# Deploy: geo-service no Render + Laravel na Hostinger (compartilhada)

> Os nomes dos menus da Hostinger e do Render podem variar. Os passos abaixo são o caminho usual.

## 1. geo-service no Render (Python)
1. Suba o repositório no GitHub.
2. Render → **New → Blueprint** → escolha o repositório. O `render.yaml` cria o serviço `geosafra-geo-service` (Docker, plano free, health check em `/health`).
3. Depois do deploy, abra **Environment** e copie o valor de `GEOSAFRA_TOKEN`.
4. Ainda em **Environment**, preencha `EARTHDATA_TOKEN` com o token de serviço da NASA Earthdata (liga SMAP, GPM, ECOSTRESS e GRACE-FO). Nunca coloque esse token no repositório. Sem ele, o resto funciona e a análise declara a lacuna.
5. Teste: `https://SEU-SERVICO.onrender.com/health` deve responder `{"status":"ok",...}`.

Observações:
- No plano free, o serviço **dorme após ~15 min sem uso** e leva cerca de 1 min para acordar. O ping agendado do Laravel (item 3) evita isso durante a demonstração.
- O disco é efêmero: o cache dos satélites se perde a cada novo deploy. Não é um problema, porque o Laravel guarda clima, relevo e dados de satélite de cada talhão no MySQL.
- O token Earthdata expira (cerca de 60 dias). Quando vencer, gere outro e troque a variável; os talhões já processados não são afetados.

## 2. Laravel na Hostinger
Na sua máquina:
```bash
composer install --no-dev --optimize-autoloader
npm ci && npm run build          # gera public/build (a hospedagem compartilhada costuma não ter Node)
```
No hPanel:
1. **PHP 8.2** (ou superior) para o domínio.
2. Crie um **banco MySQL** e anote o nome, o usuário e a senha.
3. Envie o projeto inteiro (com `vendor/`, `public/build/` e a pasta `geo-service/app/catalog/`, que o seeder usa) para uma pasta **fora** de `public_html`, por exemplo `~/geosafra`.
4. Faça o domínio servir `~/geosafra/public`. Pelo SSH (planos com acesso SSH):
   ```bash
   mv ~/domains/SEUDOMINIO/public_html ~/domains/SEUDOMINIO/public_html_old
   ln -s ~/geosafra/public ~/domains/SEUDOMINIO/public_html
   ```
5. Crie o `.env` a partir do `.env.example`:
   ```dotenv
   APP_ENV=production
   APP_DEBUG=false
   APP_URL=https://SEUDOMINIO
   DB_CONNECTION=mysql
   DB_HOST=localhost
   DB_DATABASE=...  DB_USERNAME=...  DB_PASSWORD=...
   QUEUE_CONNECTION=sync
   GEO_SERVICE_URL=https://SEU-SERVICO.onrender.com
   GEO_SERVICE_TOKEN=<valor de GEOSAFRA_TOKEN>
   ```
6. Pelo SSH:
   ```bash
   cd ~/geosafra
   php artisan key:generate
   php artisan migrate --seed --force
   php artisan config:cache && php artisan route:cache && php artisan view:cache
   php artisan geosafra:ping          # deve mostrar {"status":"ok"...}
   ```
7. A cada novo deploy do geo-service (motor atualizado), rode `php artisan cache:clear` na Hostinger: as análises ficam 10 min em cache e mostrariam o texto antigo.

> **Tempo da primeira análise:** buscar 20 anos de clima e todos os satélites leva de 2 a 5 min por talhão. O processamento pede até 12 min ao PHP (`set_time_limit`); se a hospedagem cortar antes, o talhão volta a oferecer "Tentar de novo" após 15 min, e a nova tentativa aproveita o cache do que já foi baixado.

## Atualizações: `deploy.cmd` (só o que mudou)

Depois da primeira instalação, use o script da raiz do projeto, no Windows:

```bat
deploy.cmd            :: roda os testes e o build, mostra o que mudou e pede confirmação
deploy.cmd -DryRun    :: só lista o que seria enviado
deploy.cmd -Yes       :: envia sem perguntar
deploy.cmd -SkipTests -SkipBuild
deploy.cmd -Seed AssistantKnowledgeSeeder   :: roda também um seeder no servidor
deploy.cmd -Baseline  :: marca o estado local como já publicado (não envia nada)
```

O que ele faz:
- Compara o hash de cada arquivo com o do último deploy, guardado em `.deploy/manifest.tsv`. Envia só os arquivos novos ou alterados de `app`, `bootstrap`, `config`, `database`, `public`, `resources`, `routes`, `vendor`, `docs`, `geo-service/app/catalog`, `artisan` e `composer.*`. Também apaga no servidor o que foi apagado localmente.
- Nunca envia o `.env`, `bootstrap/cache` nem `public/hot`.
- Antes de trocar qualquer arquivo, guarda uma cópia em `~/backups/deploy-<data>/before.tgz`.
- Copia o que é de `public/` para `public_html/geosafra`, sem tocar no `index.php` próprio do servidor.
- Roda `migrate --force` quando há migration nova e `package:discover` quando o `vendor` muda. Sempre refaz os caches (`config`, `route` e `view`).
- Confere se o site responde. O manifesto só é atualizado depois que o servidor confirma o deploy.

A configuração (chave SSH, porta, usuário e caminhos no servidor) fica no topo de `scripts/deploy.ps1`.

**Para desfazer** um deploy, no servidor: `cd ~/domains/softrix.com.br/geosafra && tar -xzf ~/backups/deploy-<data>/before.tgz`. Depois, copie de novo para `public_html/geosafra` o que for de `public/` e refaça os caches.

## Base de conhecimento do assistente

Em uma instalação existente, rode a migração e carregue as perguntas de referência iniciais:

```bash
php artisan migrate --force
php artisan db:seed --class=AssistantKnowledgeSeeder --force
```

Depois de revisar uma pergunta e sua resposta, publique um arquivo JSON com uma lista de entradas:

```json
[
  {
    "locale": "pt-BR",
    "slug": "leitura-do-mapa",
    "question": "Onde vejo as imagens do talhão?",
    "aliases": ["Onde ficam as imagens do talhão?"],
    "answer": "Abra o diagnóstico do talhão e procure a seção Imagens do talhão.",
    "source": "Interface do GeoSafra"
  }
]
```

```bash
php artisan geosafra:knowledge:publish respostas-revisadas.json
```

Use o mesmo identificador e idioma para revisar uma entrada. O campo opcional `source_url` aceita URL HTTP ou HTTPS. Para retirar uma resposta da busca, ponha `published_at` como `NULL`. Uma correspondência com a pergunta ou uma variante publicada retorna a referência direto do banco. Outras perguntas podem usar a mesma referência como contexto, junto com os dados do talhão. Mudanças nas referências recuperadas invalidam a resposta anterior em cache.

## 3. Cron (opcional, recomendado na demo)
hPanel → **Avançado → Cron Jobs** → a cada minuto:
```
php /home/SEU_USUARIO/geosafra/artisan schedule:run
```
Ele pinga o geo-service a cada 10 min.

## 4. Checklist antes de apresentar
- [ ] `/health` do Render responde.
- [ ] O exemplo de Uberlândia foi processado **antes** da apresentação (o resultado fica no MySQL).
- [ ] Teste no celular, em 4G.
- [ ] Mantenha um talhão já pronto como plano B, caso a rede do evento falhe.
