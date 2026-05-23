# syntax=docker/dockerfile:1
FROM rust:1.85-slim-bookworm AS chef
RUN cargo install cargo-chef --locked
WORKDIR /app

FROM chef AS planner
COPY rust/scene-syncd .
RUN cargo chef prepare --recipe-path recipe.json

FROM chef AS builder
COPY --from=planner /app/recipe.json recipe.json
RUN cargo chef cook --release --recipe-path recipe.json
COPY rust/scene-syncd .
RUN cargo build --release

FROM gcr.io/distroless/cc-debian12:nonroot
COPY --from=builder /app/target/release/scene-syncd /usr/local/bin/scene-syncd
EXPOSE 8080
ENTRYPOINT ["scene-syncd"]
