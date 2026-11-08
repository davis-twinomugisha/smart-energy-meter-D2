# Put this capstone on GitHub

This package has not changed your earlier GitHub submission. Use a separate capstone repository or the existing capstone repository if you already have one.

## Restore the prepared repository

The final ZIP contains `Energy_D2_Repository.bundle`. In a terminal beside that file:

```bash
git clone Energy_D2_Repository.bundle smart-energy-d2
cd smart-energy-d2
git remote remove origin
```

Create an empty repository on your own GitHub account. Copy its HTTPS URL, then replace `YOUR_GITHUB_REPOSITORY_URL` below with that exact URL:

```bash
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

The original dataset ZIP is ignored by Git. Obtain it with `python scripts/download_data.py`, or copy the included original ZIP from the full package into `data/raw/`. The attribution and checksum are included. All processed data, trained models, results, notebook and report are tracked. No credentials are required by the software and no Wi-Fi credentials belong in the repository.

## Upload through the GitHub website instead

Create or open your capstone repository, select Add file, then Upload files. Upload the contents of the extracted `energy_d2` folder, preserving its directories. Do not upload `.venv`, `__pycache__`, runtime logs, `wifi_config.h` or the Git bundle as a substitute for source. Commit the files, verify that README and report open, then copy the repository's URL into your course submission.

The D2 brief asks for a Git repository. A ZIP alone or a Git bundle stored as an opaque file on GitHub does not provide a browsable source submission. Publish the restored source tree.
