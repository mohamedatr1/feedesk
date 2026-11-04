param(
    [ValidateSet("start", "stop", "status")]
    [string]$Action = "status"
)

$PgBin = "F:\PostgreSQL\16\bin"
$Data = "F:\FeeDesk\.local\pgdata"
$Log = "F:\FeeDesk\.local\pg.log"
$Port = 55432

switch ($Action) {
    "start" {
        & "$PgBin\pg_ctl.exe" -D $Data -o "-p $Port -c listen_addresses=127.0.0.1" -l $Log start
    }
    "stop" {
        & "$PgBin\pg_ctl.exe" -D $Data stop
    }
    "status" {
        & "$PgBin\pg_isready.exe" -h 127.0.0.1 -p $Port
    }
}
