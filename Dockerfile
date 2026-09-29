FROM fash-staffingcloud20230810-registry.cn-shanghai.cr.aliyuncs.com/library/python:3.10.2

WORKDIR /usr/src/osc

COPY . ./
RUN pip3 install -r requirements.txt
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

EXPOSE 8779

# CMD ["gunicorn", "vrm:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:7666"]
CMD gunicorn -c gunicorn.conf.py;sleep infinity
