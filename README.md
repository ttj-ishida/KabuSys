# KabuSys

日本株自動売買システムのコアライブラリ（README）

概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム向けに設計されたライブラリ群です。本コードベースは主に以下を提供します。

- J-Quants API からの市場データ（株価日足・財務データ・JPXマーケットカレンダー）取得と DuckDB への保存（冪等的）
- RSS ベースのニュース収集（トラッキング除去、SSRF 防御、DuckDB 保存）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定・次/前営業日取得）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 簡易な設定管理（.env / 環境変数読み込み、環境切替）

設計上の特徴：
- API レート制限（J-Quants: 120 req/min）を遵守する RateLimiter
- HTTP のリトライ（指数バックオフ、401 時のトークン自動リフレッシュ）
- SSRF/DoS 対策（news_collector）
- DuckDB を用いたローカル分析・永続化（DDL・インデックス定義あり）
- 冪等性を考慮した保存ロジック（ON CONFLICT ... DO UPDATE / DO NOTHING）

---

## 主な機能一覧

- 環境・設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数の取得ラッパー（例: JQUANTS_REFRESH_TOKEN）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足 / 財務データ / マーケットカレンダーの取得（ページネーション対応）
  - DuckDB への冪等保存（save_* 関数）
  - レートリミット・リトライ・トークン自動更新
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・XML パース（defusedxml）
  - URL 正規化・トラッキング排除・記事ID生成（SHA-256）
  - SSRF 対策・レスポンスサイズ制限
  - raw_news / news_symbols への保存（チャンク挿入、トランザクション）
- スキーマ管理（kabusys.data.schema）
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema() による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分、バックフィル）
  - 日次 ETL 実行（run_daily_etl）
  - 品質チェック呼び出し
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定・次/前営業日・期間の営業日列挙
  - 夜間バッチでのカレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の定義と初期化
  - 監査用インデックス、UTC タイムゾーン固定
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue オブジェクトで問題を集約

---

## 必要条件

- Python 3.10 以上（PEP 604 の union 型表記などを使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある想定で、そちらを使ってインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成・有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -U pip
   pip install duckdb defusedxml
   # 実環境では pyproject.toml / requirements.txt を使ってインストールしてください

4. 環境変数 (.env) を作成
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

   必須環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

   任意 / デフォルト:
   - KABUSYS_ENV: development | paper_trading | live（default: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（default: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（default: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（monitoring）パス（default: data/monitoring.db）

   サンプル .env（例）:
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化

   Python REPL またはスクリプトから:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査ログ専用 DB を初期化する場合:

   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡単な例）

- J-Quants API で ID トークンを取得する

  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って POST で取得

- 日次 ETL を実行する（市場データの差分取得・保存・品質チェック）

  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- RSS ニュースを収集して保存する

  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema(":memory:")  # またはファイル DB
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(res)

- カレンダー関連ユーティリティ

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  is_open = is_trading_day(conn, date(2026,3,18))
  next_day = next_trading_day(conn, date(2026,3,18))

- 品質チェックを個別に実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for issue in issues:
      print(issue)

注意点:
- J-Quants API 呼び出しは内部でレート制限・リトライ・401 リフレッシュを管理します。
- news_collector は SSRF 対策・受信サイズ制限・gzip 解凍後のサイズチェックを実装しています。
- DuckDB の接続はスレッド共有時の扱いなど注意が必要です（アプリ側で適切に接続管理してください）。

---

## 設定（環境変数詳細）

主な設定項目（kabusys.config.Settings に基づく）:

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API のパスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（monitoring）ファイル（デフォルト data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（必須ではないが有効値であること）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- `.env.local` は上書き（override=True）されますが、OS 環境変数は保護されます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要なファイル / モジュール:

src/
  kabusys/
    __init__.py                # パッケージルート、__version__
    config.py                  # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py        # J-Quants API クライアント（fetch/save）
      news_collector.py        # RSS 収集・正規化・保存
      schema.py                # DuckDB スキーマ定義・初期化
      pipeline.py              # ETL パイプライン（run_daily_etl 等）
      calendar_management.py   # マーケットカレンダー管理
      audit.py                 # 監査ログ用スキーマ（signal/order/execution）
      quality.py               # データ品質チェック
      pipeline.py              # ETL orchestration（上記に含まれる）
    strategy/
      __init__.py              # 戦略関連（未実装のエントリ）
    execution/
      __init__.py              # 発注・ブローカー連携（未実装のエントリ）
    monitoring/
      __init__.py              # 監視関連（未実装のエントリ）

説明:
- data/ 以下がデータ取得・保存・品質管理・監査に関するコア実装です。
- strategy/、execution/、monitoring/ はパッケージ構成だけ用意してあり、戦略ロジックや実際の発注連携、監視機能はここに実装を追加していく想定です。

---

## 運用上の注意点

- 本ライブラリは実際の発注を行う仕組みの一部を含みます。live 環境で運用する場合は必ず十分なテスト・監査・リスク管理を行ってください。
- J-Quants / kabu ストレージの API キーやパスワードは安全に管理してください（リポジトリに含めない）。
- DuckDB のファイルはローカルに保存されるため、バックアップやパーミッション管理を検討してください。
- news_collector は外部 HTTP を行うため、プロキシやネットワーク制約、SSRF を考慮した運用が必要です。

---

## 開発・テスト

- 単体テストは含まれていませんが、モジュール設計は関数単位での差し替え（例: news_collector._urlopen をモック）を想定しています。
- ETL や API 呼び出しは id_token の注入（引数）や KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってテスト容易性を提供しています。

---

もし README に追加したいコマンドや具体的な実装（戦略・実ブローカー連携）のサンプルがあれば教えてください。README をそれに合わせて拡張します。