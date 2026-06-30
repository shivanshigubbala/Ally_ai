FROM golang:1.25-alpine AS build

WORKDIR /src

COPY go.mod ./
RUN go mod download

COPY . .

RUN go build -o appointment ./

FROM alpine:3.20

WORKDIR /app

COPY --from=build /src/appointment /usr/local/bin/appointment

EXPOSE 8081

CMD ["/usr/local/bin/appointment"]