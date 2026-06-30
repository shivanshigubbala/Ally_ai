FROM golang:1.25-alpine AS build

WORKDIR /src
COPY services/appointment/go.mod ./
RUN go mod download || true
COPY services/appointment/ ./
RUN go build -o /out/appointment ./

FROM alpine:3.20
COPY --from=build /out/appointment /usr/local/bin/appointment
EXPOSE 8081
CMD ["appointment"]
