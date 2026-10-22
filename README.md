下载项目后第一步
```bash
uv sync
```


```bash
导出包列表到requirements.txt
uv pip compile --emit-index-url --universal pyproject.toml -o requirements.txt
```
