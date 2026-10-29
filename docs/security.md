# Security and privacy checklist

A public file converter processes untrusted files. Treat this as a core feature, not a later enhancement.

## Upload protection
- Allowlist extensions and verify file signatures/content type; never trust the filename or browser MIME type alone.
- Set maximum upload bytes, page count, image dimensions, processing time, and output size.
- Generate server-side random filenames; never use a user-supplied path.
- Reject path traversal, malformed files, encrypted files unless intentionally supported, and unsupported formats.
- Do not execute macros, scripts, embedded content, or uploaded binaries.
- Consider malware scanning (e.g. ClamAV) before processing public uploads.

## Worker isolation
- Run LibreOffice and OCR in a non-root worker container with CPU, memory, process and timeout limits.
- Use a read-only base filesystem where practical and a dedicated per-job scratch directory.
- Disable outbound network access from workers unless required.
- Do not run shell commands by concatenating user-provided strings; pass subprocess arguments as arrays.
- Use process timeouts and kill the process group on timeout.

## Privacy
- Tell users what is uploaded and how long it is retained.
- Delete source and output files automatically after a short retention window (e.g. 1 hour, configurable).
- Avoid logging document text, filenames containing personal information, or file contents.
- Use HTTPS, private storage, short-lived download links, and access checks.
- Add rate limits and quotas to prevent abuse and unexpectedly high hosting costs.
- Provide a delete-now action if feasible.

## Legal and operational
- Review licenses for all libraries, OCR language data, fonts and conversion engines.
- Publish privacy policy and acceptable-use rules before public launch.
- Do not promise perfect OCR or exact layout preservation.
