# Running Uvicorn Server

## Correct Command

The FastAPI app is accessible through `agency.app`, not `agency.main`:

```bash
uvicorn agency.app:app --reload
```

## Alternative Commands

You can also run it directly from the API module:

```bash
uvicorn api.main:app --reload
```

Or use Python to run it:

```python
python -m uvicorn agency.app:app --reload
```

## File Structure

- `agency/app.py` - Wrapper that imports app from `api/main.py`
- `api/main.py` - Actual FastAPI application

## Common Issues

### Error: "Could not import module 'agency.main'"
**Solution**: Use `agency.app:app` instead of `agency.main:app`

### Error: "ModuleNotFoundError"
**Solution**: Make sure you're in the project root directory and the virtual environment is activated

### Error: "ImportError"
**Solution**: Check that all dependencies are installed:
```bash
pip install fastapi uvicorn
```

## Default Configuration

- **Host**: 127.0.0.1 (localhost)
- **Port**: 8000
- **Reload**: Enabled with `--reload` flag

## Accessing the API

Once running, you can access:
- API Documentation: http://127.0.0.1:8000/docs
- Alternative Docs: http://127.0.0.1:8000/redoc
- API Root: http://127.0.0.1:8000

