# build image (rustc and Cargo that can build xsnippet-api from source)
FROM rustlang/rust:nightly AS builder
WORKDIR /usr/src/xsnippet-api

# first, copy Cargo.toml and prebuild all dependencies, so that we do not have to do
# that every single time when the source code of the application is updated
COPY Cargo.toml Cargo.toml
RUN mkdir src/ && \
    echo "fn main() {println!(\"if you see this, the build broke\")}" > src/main.rs && \
    cargo build --release && \
    cargo test && \
    rm -f target/release/deps/xsnippet-api*

# now copy the source code and build the application itself
COPY . .
RUN touch src/main.rs && cargo install --path . && mv /usr/local/cargo/bin/xsnippet-api /usr/local/bin/xsnippet-api
RUN objcopy --only-keep-debug /usr/local/bin/xsnippet-api /usr/local/bin/xsnippet-api.dbg && \
    objcopy --strip-debug /usr/local/bin/xsnippet-api && \
    objcopy --add-gnu-debuglink=/usr/local/bin/xsnippet-api.dbg /usr/local/bin/xsnippet-api

# deploy image (DB schema migrations and the Python libraries required for running them)
FROM debian:buster-slim AS deploy
RUN apt-get update && apt-get install -y python3-alembic python3-psycopg2 && rm -rf /var/lib/apt/lists/*
COPY . /usr/src/xsnippet-api
WORKDIR /usr/src/xsnippet-api

# base image (xsnippet-api executable and its dynamic dependencies)
FROM debian:buster-slim AS base
RUN apt-get update && apt-get install -y libpq5 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/bin/xsnippet-api /usr/local/bin/xsnippet-api
ENV ROCKET_ADDRESS=localhost \
    ROCKET_PORT=8000 \
    RUST_BACKTRACE=1
EXPOSE $ROCKET_PORT
ENTRYPOINT ["xsnippet-api"]

# debug image (same as base, but also packs the debugging symbols)
FROM base AS debug
COPY --from=builder /usr/local/bin/xsnippet-api.dbg /usr/local/bin/xsnippet-api.dbg

# release image (just an alias for base, so that it's the target that we build by default)
FROM base AS release
