FROM node:25-slim AS base
    RUN apt update

    RUN npm i -g turbo

    WORKDIR /src/repo/

FROM base AS extractor
    COPY . /src/repo/
    RUN turbo prune web --docker

FROM base AS builder
    WORKDIR /app
    COPY --from=extractor /src/repo/out/json/ .
    RUN npm i

    COPY --from=extractor /src/repo/out/full/ .
    RUN npm run build

FROM node:25-slim AS runner

    WORKDIR /app
    COPY --from=builder /app/apps/web/.output/ .

    ENTRYPOINT [ "node", "server/index.mjs" ]

    # ENTRYPOINT ["tail", "-f", "/dev/null"]