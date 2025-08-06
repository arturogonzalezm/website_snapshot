# WordPress Snapshot Time-Travel Docker Images

With zero SSH or root on the live host, you can still build full "snapshot → time-travel" Docker images by having WordPress push its own backups to a place you control, and then running your snapshot/restore tooling entirely on a separate Docker host. Here's a turnkey pattern:

## 1. Push site backups from WordPress (no host access needed)

Use a WP plugin that can package and upload **both** your database dump and your `wp-content` folder to remote storage:

| Plugin | What it does | Storage targets |
|--------|--------------|----------------|
| **UpdraftPlus** | Exports DB + files on schedule | S3, Google Drive, FTP/SFTP, etc. |
| **Duplicator Pro** | Builds a full ZIP installer with DB + files | S3, Dropbox, FTP/SFTP, e-mail |

1. **Install & configure** your chosen plugin in the WP dashboard.
2. **Point it at** an S3 bucket (or other storage) you control.
3. **Schedule** hourly/daily backups:
   * SQL dump of the database
   * Tar/ZIP of `wp-content` (themes, plugins, uploads)

Your live site never needs to open SSH or expose more than the WP admin panel—and your backups land safely off-site.

## 2. Separate Docker host: fetch + snapshot

On any machine (CI runner, your laptop, small VPS), run a cron job or CI pipeline that:

1. **Downloads the latest backup artifacts** you pushed in step 1:

```bash
aws s3 cp s3://your-bucket/latest.sql ./dump.sql
aws s3 cp s3://your-bucket/latest_wp_content.tar.gz ./site.tar.gz
```

2. **Builds a Docker image** tagged with the timestamp:

```dockerfile
# in a temp dir alongside dump.sql & site.tar.gz
FROM mysql:8.0 AS db-stage
COPY dump.sql /docker-entrypoint-initdb.d/

FROM wordpress:latest
COPY site.tar.gz /tmp/
RUN tar xzf /tmp/site.tar.gz -C /var/www/html
```

```bash
docker build -t registry.example.com/site-snapshots:$(date +%Y%m%d%H%M%S) .
docker push registry.example.com/site-snapshots:$(date +%Y%m%d%H%M%S)
```

3. **(Optional)** Prunes old tags on your registry to enforce retention policy.

All of this runs **completely outside** the live WordPress host.

## 3. Restore/time-travel

When you need to roll back or spin up a historical copy:

1. `docker pull registry.example.com/site-snapshots:<TAG>`
2. Run a "restore" container (or sidecar) to populate fresh volumes:

```bash
docker run --rm \
  -v wp_data:/var/www/html \
  -v db_data:/var/lib/mysql \
  registry.example.com/site-snapshots:<TAG> \
  bash -c "echo Volumes populated—now start your normal stack"
```

3. Point your normal `docker-compose.yml` (or Kubernetes, etc.) at those volumes and bring the site up.

## Why this works without host access

* **WordPress handles the dump/export** via HTTP (the plugin) and pushes directly to storage you control.
* **Your Docker host** never connects to the production machine—it only pulls from S3 (or FTP).
* **No server-level credentials** are required on the live host.

If you'd like, I can help you turnkey the cron script, sample Dockerfile and CI configuration—just say the word!

# Running this setup

```python
python3 archivebox_cli.py --binary .venv/bin/archivebox --data-dir srv/archivebox init

# Default: skips extractors
python3 archivebox_cli.py --data-dir srv/archivebox bulk

# If you install dependencies later, enable full archiving:
python3 archivebox_cli.py --data-dir srv/archivebox bulk --no-index-only
```
