# KARMA — Ubuntu 24.04 + Nginx + PostgreSQL deployment

Target URL: `https://5.61.27.185/karma/`

This build supports deployment under `/karma` using `APP_PREFIX=/karma` and Django `FORCE_SCRIPT_NAME`.

## Safe deployment

1. Upload/extract the project on the server.
2. Run:

```bash
cd karma_project
sudo ./deploy-ubuntu-24.04.sh
```

3. The script deliberately does **not** edit your existing Nginx virtual hosts because this server already hosts other sites.
4. Add this line inside the existing HTTPS `server { ... }` block handling the IP:

```nginx
include /etc/nginx/snippets/karma-location.conf;
```

5. Validate and reload:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Useful commands

```bash
sudo systemctl status karma
sudo journalctl -u karma -f
sudo nginx -t
```

## Optional demo seed

By default production deployment does not create demo credentials. To seed demo data:

```bash
sudo KARMA_SEED_DEMO=1 ./deploy-ubuntu-24.04.sh
```
