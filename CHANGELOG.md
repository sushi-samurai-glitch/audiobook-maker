# Changelog

## 0.9.0 (beta), not yet released

The first public build, for Apple silicon Macs.

- A real installer: a .dmg with everything inside, FFmpeg included. Drag the app to Applications.
- Settings: Download all voices with a progress bar, what each voice takes on disk with Delete, the version, Copy
  details for bug reports, and Show log.
- The Creating screen shows how far a first-time voice download has got.
- Plain `.txt` chapters work as well as `.md`, and chapter files saved with a BOM or as Windows-1252 are read
  correctly.
- The app checks for FFmpeg before narrating, keeps the Mac awake while a book is made, and fits a 1280 × 800 screen.
- The log is kept in ~/Library/Logs/Audiobook Maker and starts afresh past 5 MB.
- No tracking: Hugging Face's usage reporting is turned off.
- Says when a new version is out (checked once a day on GitHub; can be turned off in Settings).
- Keyboard shortcuts for every step (Help, Keyboard), and Larger text in Settings.
- Settings → Licences lists everything the app includes and its licence.
