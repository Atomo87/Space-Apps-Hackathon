# Deployment — geo-service on Render and Laravel on Hostinger shared hosting

Hostinger and Render menu names may vary. These steps describe the usual setup.

## 1. Deploy geo-service (Python) on Render

1. Push the repository to GitHub.
2. In Render, select **New → Blueprint** and choose the repository. The `render.yaml` file creates `geosafra-geo-service` as a free Docker service with a health check at `/health`.
3. After deployment, open **Environment** and copy the value of `GEOSAFRA_TOKEN`.
4. In **Environment**, set `EARTHDATA_TOKEN` to the NASA Earthdata service token to enable SMAP, GPM, ECOSTRESS, and GRACE-FO. Keep the token out of the repository. The rest of the analysis works without this token and reports the missing data.
5. Verify that `https://YOUR-SERVICE.onrender.com/health` returns `{"status":"ok",...}`.

On the free plan, the service **sleeps after about 15 minutes of inactivity** and takes about one minute to wake up. The Laravel cron job in section 3 keeps it awake during the demo. The disk is ephemeral, so deployments clear the satellite cache. Laravel retains field climate, terrain, and satellite data in MySQL.

The Earthdata token expires after about 60 days. When it expires, generate a replacement and update the variable. Previously processed fields retain their data.

## 2. Deploy Laravel on Hostinger

On your local machine, install dependencies and build the front end. The build writes to `public/build`, which you can upload to a shared host that lacks Node.js.

```bash
composer install --no-dev --optimize-autoloader
npm ci && npm run build
```

In hPanel:

1. Set the domain to **PHP 8.2** or later.
2. Create a **MySQL database** and record the database name, username, and password.
3. Upload the project, including `vendor/`, `public/build/`, and the `geo-service/app/catalog/` directory used by the seeder, to a directory **outside** `public_html`, such as `~/geosafra`.
4. Configure the domain to serve `~/geosafra/public`. On plans with SSH access, run:

   ```bash
   mv ~/domains/YOUR-DOMAIN/public_html ~/domains/YOUR-DOMAIN/public_html_old
   ln -s ~/geosafra/public ~/domains/YOUR-DOMAIN/public_html
   ```

5. Create `.env` from `.env.example`. Replace the domain and service placeholders with your own values.

   ```dotenv
   APP_ENV=production
   APP_DEBUG=false
   APP_URL=https://YOUR-DOMAIN
   DB_CONNECTION=mysql
   DB_HOST=localhost
   DB_DATABASE=...  DB_USERNAME=...  DB_PASSWORD=...
   QUEUE_CONNECTION=sync
   GEO_SERVICE_URL=https://YOUR-SERVICE.onrender.com
   GEO_SERVICE_TOKEN=<value of GEOSAFRA_TOKEN>
   ```

6. Run the following commands over SSH and confirm that the ping reports `{"status":"ok",...}`.

   ```bash
   cd ~/geosafra
   php artisan key:generate
   php artisan migrate --seed --force
   php artisan config:cache && php artisan route:cache && php artisan view:cache
   php artisan geosafra:ping
   ```

7. After deploying a new geo-service engine version, run `php artisan cache:clear` on Hostinger. This removes old analysis text from the 10-minute cache.

> **First analysis.** Retrieving 20 years of climate data and all satellite datasets takes two to five minutes per field. The job requests up to 12 minutes of PHP execution time (`set_time_limit`). If the host stops the job early, the field shows “Try again” after 15 minutes. Retrying reuses any data already cached.

## Updates with `deploy.cmd`

After the first installation, run the script from the project root on Windows.

| Command | Effect |
|---|---|
| `deploy.cmd` | Runs tests and builds, shows the changes, and asks for confirmation. |
| `deploy.cmd -DryRun` | Lists the files that would be deployed. |
| `deploy.cmd -Yes` | Deploys without asking for confirmation. |
| `deploy.cmd -SkipTests -SkipBuild` | Skips tests and the build. |
| `deploy.cmd -Seed AssistantKnowledgeSeeder` | Also runs the specified seeder on the server. |
| `deploy.cmd -Baseline` | Records the local state as already deployed without uploading it. |

The script:

- Compares the hash of each file with the last deployed hash in `.deploy/manifest.tsv`. It uploads new or changed files in `app`, `bootstrap`, `config`, `database`, `public`, `resources`, `routes`, `vendor`, `docs`, `geo-service/app/catalog`, `artisan`, and `composer.*`. It removes corresponding remote files when they have been deleted locally.
- Excludes `.env`, `bootstrap/cache`, and `public/hot` from uploads.
- Saves a copy to `~/backups/deploy-<date>/before.tgz` before replacing any files.
- Copies files from `public/` to `public_html/geosafra` while preserving the server’s own `index.php`.
- Runs `migrate --force` when there is a new migration and `package:discover` when `vendor` changes. It rebuilds the configuration, route, and view caches on every deployment.
- Checks that the site responds and updates the manifest only after the server confirms deployment.

SSH settings, including the key, port, username, and server paths, are at the top of `scripts/deploy.ps1`.

**To roll back a deployment**, run `cd ~/domains/softrix.com.br/geosafra && tar -xzf ~/backups/deploy-<date>/before.tgz` on the server. Copy the restored files from `public/` back to `public_html/geosafra` and rebuild the caches.

## Assistant knowledge base

On an existing installation, run the migration and load the initial reference questions.

```bash
php artisan migrate --force
php artisan db:seed --class=AssistantKnowledgeSeeder --force
```

After reviewing a question and its answer, publish a JSON file containing an array of entries.

```json
[
  {
    "locale": "en-US",
    "slug": "field-imagery",
    "question": "Where can I see imagery for my field?",
    "aliases": ["Where do I find the field images?"],
    "answer": "Open the field diagnosis and look for the Field imagery section.",
    "source": "GeoSafra interface"
  }
]
```

```bash
php artisan geosafra:knowledge:publish reviewed-answers.json
```

To revise an entry, keep its identifier and locale. The optional `source_url` field accepts HTTP or HTTPS URLs. To remove an answer from search, set `published_at` to `NULL`. A match on a published question or alias returns the reference directly from the database. Other questions can use the same reference alongside the field data. Changes to retrieved references invalidate the previously cached answer.

## 3. Cron job (optional, recommended for the demo)

In hPanel, go to **Advanced → Cron Jobs** and run this command once a minute.

```
php /home/YOUR_USERNAME/geosafra/artisan schedule:run
```

The scheduled task pings geo-service every 10 minutes.

## 4. Pre-presentation checklist

- [ ] Check that Render’s `/health` endpoint responds.
- [ ] Process the Uberlândia example before the presentation. MySQL retains the result.
- [ ] Test on a phone using 4G.
- [ ] Keep a processed field ready as a backup in case the venue’s network fails.
