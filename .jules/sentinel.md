## 2024-05-23 - Path Traversal in Gradio File Loading
**Vulnerability:** The application constructs file paths using user-provided input without proper validation, allowing access to the entire filesystem via path traversal (e.g., `] ..`).
**Learning:** `os.path.join` does not resolve `..` or prevent directory traversal. When dealing with user-controlled paths, always resolve to absolute paths (`os.path.abspath`) and check if the resulting path starts with the expected base directory.
**Prevention:** Always validate user-provided paths against a whitelist of allowed directories. Use `os.path.abspath` and `startswith` to enforce directory containment.
