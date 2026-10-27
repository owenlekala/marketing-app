# TAG Marketing

A separate Frappe app for ERPNext WhatsApp marketing and automation. The application is under development; business features and production release gates are not yet qualified.

The [implementation handbook](docs/whatsapp_marketing/README.md) owns the design, tasks and acceptance criteria. Read [progress](docs/whatsapp_marketing/PROGRESS.md) for verified work and the [development setup](docs/whatsapp_marketing/FRAMEWORK_AND_SETUP.md) for the pinned disposable runtime.

## Development

Keep this repository beside the compatible `frappe` and `erpnext` source repositories. Run from this repository root:

```sh
python3 development/whatsapp_marketing/runtime.py up
python3 development/whatsapp_marketing/runtime.py verify
```

Runtime credentials are generated locally and ignored by Git. This developer environment is not a production deployment. Python and app version bounds are declared in [pyproject.toml](pyproject.toml); the exact tested revisions and image digests are owned by [the runtime lock](development/whatsapp_marketing/runtime.lock.json).

## License

[MIT](license.txt).
