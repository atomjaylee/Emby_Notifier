FROM arm64v8/python:3.11-alpine3.19

LABEL maintainer="Xu@nCh3n"

ENV TZ=Asia/Shanghai LANG=zh_CN.UTF-8 PYTHONUNBUFFERED=1

WORKDIR /usr/src/myapp
EXPOSE 8000

COPY pyproject.toml ./
COPY src ./src
COPY main.py ./

RUN python3 -m pip install --no-cache-dir .

ENTRYPOINT ["python3"]
CMD ["/usr/src/myapp/main.py"]
