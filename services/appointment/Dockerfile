FROM golang:1.25-alpine AS build

WORKDIR /src

COPY go.mod ./
COPY go.sum ./

RUN go mod download

COPY . .

RUN go build -o appointment ./cmd/server

FROM alpine:3.20

WORKDIR /app

COPY --from=build /src/appointment .

EXPOSE 8081

CMD ["./appointment"]