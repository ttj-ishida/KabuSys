# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants や RSS など外部データを収集・整形し、DuckDB に格納して戦略や発注基盤へ渡すための ETL、データ品質チェック、監査ログ機能を備えています。

---

## 概要

KabuSys は以下のような用途を想定したモジュール群を提供します。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- RSS フィードからのニュース収集・前処理・銘柄紐付け（SSRF対策・XML安全化・トラッキング除去）
- DuckDB スキーマ定義と初期化、ETL パイプライン（差分更新・バックフィル対応）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査用テーブル（シグナル→発注→約定フローをトレース可能）
- マーケットカレンダー管理（営業日判定、next/prev/trading days）

設計上のポイント:
- API レート制限・リトライ・Idempotency（ON CONFLICT）を重視
- Look-ahead bias 対策として fetched_at / UTC の利用
- セキュリティ対策（SSRF、XML Bomb、受信サイズ制限 等）
- DuckDB を中心に軽量でローカル運用しやすい構成

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ冪等保存する save_* 関数
  - レート制御・指数バックオフ・401 自動リフレッシュ
- data.news_collector
  - RSS フィード取得、記事正規化、raw_news への保存、銘柄抽出・紐付け
  - SSRF / Gzip bomb / Defused XML 対応
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で全テーブルとインデックスを作成
- data.pipeline
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一連処理
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間差分更新
- data.quality
  - 欠損・重複・スパイク・日付不整合のチェック群
  - run_all_checks による一括実行
- data.audit
  - 監査用テーブル（signal_events / order_requests / executions）と初期化ヘルパ
- config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数をラップする Settings（必須項目は _require で検証）

---

## 動作要件

- Python 3.10 以上（PEP 604 の Union 型（|）等を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

必要に応じて他ライブラリ（例: requests ではなく標準 urllib を利用しているため最小限です）。

例（pip）:
pip install duckdb defusedxml

プロジェクト配布パッケージがある場合は:
pip install -e .

---

## 設定（環境変数）

プロジェクトルートの `.env` および `.env.local` が自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。  
自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- 動作モード / ログ
  - KABUSYS_ENV (任意、'development' | 'paper_trading' | 'live', デフォルト: development)
  - LOG_LEVEL (任意、DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

例 (.env):
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=change_me
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

設定不足（必須変数未設定）時は Settings が ValueError を投げます。

---

## セットアップ手順

1. Python と依存ライブラリをインストール
   - Python >= 3.10
   - pip install duckdb defusedxml

2. リポジトリをクローン / パッケージをインストール
   - git clone ...
   - pip install -e .  （開発インストール）

3. 環境変数を準備
   - プロジェクトルートに `.env` を作成（上記の必須キーを設定）

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで以下を実行して DB を初期化します。

例:
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)  # ファイル作成 + テーブル作成

監査ログ用に別 DB を分ける場合:
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/audit.duckdb")

注: init_schema は親ディレクトリを自動作成します。

---

## 使い方（簡単なコード例）

以下は代表的な利用例です。実行前に .env を用意してください。

- 日次 ETL を実行して DuckDB を更新する

from kabusys.config import settings
from kabusys.data import schema, pipeline

# DB 初期化（未作成時）
conn = schema.init_schema(settings.duckdb_path)

# ETL 実行（今日が対象日）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())

- RSS ニュース収集ジョブを実行する

from kabusys.config import settings
from kabusys.data import schema, news_collector

conn = schema.init_schema(settings.duckdb_path)

# known_codes を与えると記事と銘柄の紐付けを行います（例: 上場銘柄の set）
known_codes = {"7203", "6758"}  # 必要に応じて実際のコードセットで置き換えてください
stats = news_collector.run_news_collection(conn, known_codes=known_codes)
print(stats)

- カレンダー夜間更新ジョブ

from kabusys.config import settings
from kabusys.data import schema, calendar_management

conn = schema.init_schema(settings.duckdb_path)
saved = calendar_management.calendar_update_job(conn)
print("calendar saved:", saved)

- 監査スキーマを既存接続に追加する

from kabusys.data import audit
# conn は schema.init_schema で得た接続
audit.init_audit_schema(conn, transactional=True)

---

## ログ設定例

標準の logging でアプリ側からログレベルを設定してください。環境変数 LOG_LEVEL が設定されている場合、Settings.log_level が検証を行います。

簡単な例:
import logging
from kabusys.config import settings

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("kabusys")
logger.info("KabuSys starting...")

---

## ディレクトリ構成

リポジトリ配下の主なファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、.env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ロジック
    - news_collector.py      — RSS 取得・前処理・DB 保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義 & init_schema
    - calendar_management.py — カレンダー管理・営業日判定・更新ジョブ
    - audit.py               — 監査ログテーブル & 初期化ユーティリティ
    - quality.py             — データ品質チェック（欠損/スパイク/重複/日付不整合）
    - pipeline.py            — （ETL ロジック）
  - strategy/                 — 戦略関連（雛形）
  - execution/                — 発注実行関連（雛形）
  - monitoring/               — 監視・メトリクス（雛形）

各モジュールは役割ごとに分離されており、テストや拡張がしやすい設計になっています（例: news_collector._urlopen をテストでモック可能）。

---

## 注意事項 / トラブルシューティング

- 必須環境変数が未設定の場合、Settings のプロパティアクセスで ValueError が発生します。README の「設定」セクションを参照してください。
- J-Quants API のレート制限（120 req/min）を超えないよう内部で固定間隔レートリミッタを実装しています。大量取得を同時並行で行う場合は注意してください。
- news_collector は外部 URL の取得時に SSRF チェック、Content-Length チェック、Gzip 解凍サイズチェックを行います。想定外のレスポンスや巨大レスポンスはスキップされ、ログに警告が出ます。
- DuckDB はファイルロックや同時接続の取り扱いに注意が必要です。複数プロセスで同一ファイルに同時書き込みを行う場合は運用設計を行ってください。

---

## 貢献 / テスト

- 各モジュールはユニットテストしやすいよう副作用を最小化して設計されています（例: id_token を注入できる、_urlopen を差し替え可能）。  
- PR やイシュー歓迎します。変更を加える際は既存の設計原則（冪等性、セキュリティ、UTC タイムスタンプ等）を尊重してください。

---

以上が本リポジトリの概要と基本的な使い方です。必要に応じて個別のモジュール（jquants_client, news_collector, pipeline, audit, quality など）のドキュメントやサンプルスクリプトを追加していくと運用しやすくなります。