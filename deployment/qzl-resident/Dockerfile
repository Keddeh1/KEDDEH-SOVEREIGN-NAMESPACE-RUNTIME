FROM node@sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20 AS node
FROM python@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /lib/x86_64-linux-gnu/libstdc++.so.6 /lib/x86_64-linux-gnu/libstdc++.so.6
COPY --from=node /lib/x86_64-linux-gnu/libgcc_s.so.1 /lib/x86_64-linux-gnu/libgcc_s.so.1
COPY docker /usr/local/bin/docker
COPY wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels /wheels/keddeh_sovereign_namespace_runtime-0.3.2+qzl.1-py3-none-any.whl yowasp-yosys==0.69.0.0.post1233 z3-solver==5.1.0.0 && python -m pip check
RUN groupadd --gid 1000 keddeh && useradd --uid 1000 --gid 1000 --home-dir /tmp/keddeh-owner keddeh
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 HOME=/tmp/qzl-owner
USER 1000:1000
ENTRYPOINT ["python", "-m", "keddeh_namespace.web4_runtime", "serve", "--root"]
