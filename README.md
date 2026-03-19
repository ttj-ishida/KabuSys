# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。データ取得（J-Quants）、DuckDB を用いたデータスキーマ／ETL、ニュース収集、ファクター計算（リサーチ）、
および監査・実行レイヤの骨組みを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のためのモジュール群を集めたコードベースです。主に以下の責務があります。

- J-Quants API からの市場データ・財務データ・マーケットカレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を利用したデータスキーマ定義・初期化・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、保存、品質チェック）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策・XML セキュリティ・ペイロード制限）
- 研究（research）モジュール：ファクター計算、将来リターン・IC 計算、Zスコア正規化など
- 監査ログのためのスキーマ（order/signal/execution のトレーサビリティ）

設計上の特徴:
- DuckDB を中心に冪等性（ON CONFLICT ...）やトランザクション処理を想定
- 外部依存は最小限（duckdb, defusedxml 等を利用）
- 本番システムにおける安全性（トークン自動更新、SSRF対策、XML攻撃対策など）を考慮

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（fetch / save / pagination / retry / rate-limit）
  - schema: DuckDB のスキーマ定義と初期化（raw/processed/feature/execution 層）
  - pipeline / etl: 差分 ETL（prices / financials / calendar）と日次 ETL 実行 run_daily_etl
  - news_collector: RSS 取得・記事正規化・記事保存・銘柄抽出・bulk 保存
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ（signal/order_request/execution）スキーマ & 初期化
  - stats / features: Z スコア正規化や特徴量ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value などのファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- config: 環境変数ベースの設定読み込み（.env 自動ローディング、必須チェック、環境種別判定）
- monitoring, execution, strategy: パッケージインターフェースを分離（ひな型）

---

## 前提・依存

- Python 3.10 以上（注: 型注釈で `|` を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml

例:
pip install duckdb defusedxml

（プロジェクトに pyproject.toml / requirements.txt があればそちら経由でインストールしてください）

---

## 環境変数 / 設定 (.env)

config.Settings で参照される主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

自動で .env / .env.local をプロジェクトルートから読み込む仕組みがあります。
自動ローディングを無効化する場合:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=yyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. Python を準備（3.10+）
2. 依存のインストール:
   pip install duckdb defusedxml
   （プロジェクトにパッケージ管理がある場合は `pip install -e .` や `pip install -r requirements.txt` を利用）
3. 環境変数 (.env) を作成して必要な値を設定
4. DuckDB スキーマの初期化
   - Python REPL やスクリプトで実行:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - ":memory:" を指定するとインメモリ DB で動作（テスト用）:
     conn = init_schema(":memory:")

5. 監査ログ専用スキーマ（必要な場合）:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（コード例）

- 日次 ETL 実行（市場カレンダー・株価・財務データの差分取得と品質チェック）

from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- 特定日・銘柄のファクター計算（リサーチ）

from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2024, 1, 4)
mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)
fwd = calc_forward_returns(conn, t)

# 例: mom の mom_1m と fwd_1d の IC を計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

# Z スコア正規化
normed = zscore_normalize(mom, ["mom_1m", "ma200_dev"])

- J-Quants 生データ取得（低レベル）

from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,4))
saved = save_daily_quotes(conn, records)
print("saved:", saved)

- ニュース収集ジョブの実行

from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 有効銘柄セット（例）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)

---

## よく使うユーティリティ / 注意点

- config:
  - settings = kabusys.config.settings からアプリ設定を参照可能
  - 必須環境変数が未設定の場合は ValueError が発生します（例: JQUANTS_REFRESH_TOKEN）
- DuckDB:
  - init_schema() は冪等（既存テーブルを作成済みであればスキップ）
  - get_connection() は既存ファイル接続を返すのみ（スキーマ初期化は行わない）
- ETL:
  - run_daily_etl() は品質チェックを実行し、QualityIssue のリストを ETLResult に格納
  - backfill_days により直近日数を再取得して API の後出し修正に対応
- RSS / news_collector:
  - SSRF 対策・最大受信バイト数制限・gzip 対応あり
  - 記事 ID は正規化 URL の SHA256 の先頭 32 文字
- ロギング:
  - LOG_LEVEL でプロジェクト全体のログレベルを制御
- テスト:
  - 環境変数の自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
  - DuckDB に ":memory:" を使うと一時 DB でテスト可能

---

## ディレクトリ構成

（抜粋。重要なファイルを列挙）

src/
  kabusys/
    __init__.py
    config.py                        # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py              # J-Quants API クライアント（fetch/save）
      news_collector.py              # RSS ニュース収集・保存・銘柄抽出
      schema.py                      # DuckDB スキーマ定義・init_schema
      pipeline.py                    # ETL パイプライン（run_daily_etl 等）
      etl.py                         # ETL インターフェース (ETLResult)
      quality.py                      # データ品質チェック
      calendar_management.py         # マーケットカレンダー管理
      audit.py                       # 監査ログスキーマ初期化
      stats.py                       # 統計ユーティリティ（zscore）
      features.py                     # 特徴量公開インターフェース
    research/
      __init__.py
      factor_research.py             # Momentum/Value/Volatility ファクター計算
      feature_exploration.py         # 将来リターン / IC / サマリー
    strategy/
      __init__.py                     # 戦略レイヤのエントリ（未実装の雛形）
    execution/
      __init__.py                     # 発注/実行レイヤのエントリ（未実装の雛形）
    monitoring/
      __init__.py                     # 監視用エントリ（未実装の雛形）

---

## 開発・拡張のヒント

- DuckDB の SQL と Python の組み合わせで高速に集計処理を実行する設計です。大量データを扱う場合はクエリ計画・インデックスを確認してください。
- jquants_client の _RateLimiter やリトライロジックは API レート制限を念頭に置いた実装です。必要に応じて調整してください。
- news_collector はセキュリティに配慮した実装（defusedxml、SSRF・gzipサイズ制限）になっています。RSS ソースの追加は DEFAULT_RSS_SOURCES を拡張してください。
- audit スキーマは監査が重要な用途向けに設計されています。テーブルの削除や外部キーの取り扱いはコメントに注意してください（DuckDB の制限に合わせた設計）。

---

## ライセンス / 貢献

（この README はコードベースに基づく概要を示します。ライセンスはリポジトリルートの LICENSE を参照してください。）
貢献やバグ報告はプルリクエスト / Issue を通じてお願いします。

---

必要であれば、この README をベースに「運用手順書」「デプロイ手順」「監視・アラート設計」などのドキュメントを作成します。どの部分を詳細化したいか教えてください。