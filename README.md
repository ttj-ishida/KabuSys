# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants や RSS、kabuステーション 等からデータを取得・整備し、DuckDB に保存、特徴量作成→シグナル生成→監査までの主要コンポーネントを提供します。

主な用途:
- 市場データ（OHLCV / 財務 / カレンダー）の差分取得 (J-Quants)
- ニュース収集（RSS）と記事の銘柄紐付け
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量の正規化（Z スコア）および features テーブルへの格納
- 戦略スコアの統合と BUY / SELL シグナル生成
- DuckDB ベースのスキーマ定義・初期化、ETL パイプライン、監査テーブル

バージョン: 0.1.0

---

## 主な機能（抜粋）

- data/jquants_client:
  - J-Quants API から株価・財務・カレンダーを取得（ページネーション・リトライ・レート制御付き）
  - DuckDB への冪等保存関数（ON CONFLICT を利用）
- data/schema:
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- data/pipeline:
  - 日次差分 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
- data/news_collector:
  - RSS 取得・前処理・raw_news 保存・銘柄抽出と news_symbols への紐付け
- data/calendar_management:
  - market_calendar の管理と営業日ユーティリティ（is_trading_day, next_trading_day 等）
- data/stats:
  - zscore_normalize（クロスセクション Z スコア正規化）
- research:
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を利用）
  - 将来リターン calc_forward_returns、IC（Spearman）計算等
- strategy:
  - build_features（特徴量構築→features テーブルへ upsert）
  - generate_signals（features + ai_scores を用いて final_score を算出し signals テーブルへ upsert）
- audit / execution / monitoring 周辺で監査ログ・発注→約定→ポジション管理のスキーマを提供

---

## 依存関係

本リポジトリ内のコードから推測される主なランタイム依存:
- Python 3.10+
  - 型アノテーションで `X | Y` を使用しているため 3.10 以上を想定
- duckdb
- defusedxml
- （標準ライブラリの urllib, datetime, logging 等を多用）

インストール例:
pip install duckdb defusedxml

プロジェクト配布方法に合わせて `pyproject.toml` / `setup.cfg` があればそちらを利用してください。

---

## 環境変数（必須・任意）

自動ロードはプロジェクトルートの `.env` / `.env.local` を参照します（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。必須のキー:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID

任意・デフォルトあり:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLitePath（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## セットアップ手順

1. Python 3.10+ をインストールする。

2. 仮想環境を作成・有効化（例）:
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

3. 必要パッケージをインストール:
pip install duckdb defusedxml

（プロジェクトに pyproject.toml / requirements.txt があればそれを利用）

4. プロジェクトルートに .env を作成し、必要な環境変数を設定。

5. DuckDB スキーマを初期化:
Python REPL や簡単なスクリプトで以下を実行:

from kabusys.data.schema import init_schema
from kabusys.config import settings
init_schema(settings.duckdb_path)

これにより指定されたパスに DuckDB ファイルが作成され、すべてのテーブルが作成されます。

---

## 使い方（代表的なワークフロー例）

- DuckDB の初期化（1回）
from kabusys.data.schema import init_schema
from kabusys.config import settings
conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）:
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn)
print(res.to_dict())

- 特徴量構築（指定日）:
from datetime import date
from kabusys.strategy import build_features
count = build_features(conn, date(2024, 1, 4))
print(f"built features for {count} codes")

- シグナル生成（指定日）:
from kabusys.strategy import generate_signals
num_signals = generate_signals(conn, date(2024, 1, 4))
print(f"signals written: {num_signals}")

- ニュース収集ジョブを実行して DB に保存:
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758', ...})
print(result)

- J-Quants トークンを明示取得して ETL に渡す（テストなど）:
from kabusys.data import jquants_client as jq
token = jq.get_id_token()  # settings を参照して取得
# token を run_daily_etl に渡すことも可能

注意点:
- すべての主要処理関数は DuckDB の接続オブジェクトを受け取るため、接続管理は呼び出し側で行ってください。
- 日付はすべて datetime.date を使うこと（timezone の混入を避ける設計）。

---

## 主要 API（主な公開関数）

- kabusys.config.settings — 環境変数ラッパー
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...) — 日次 ETL
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=..., weights=...)

詳細は各モジュールの docstring を参照してください（コード内に詳細設計と挙動が記載されています）。

---

## ディレクトリ構成

（src 配置を前提にした主要ファイル一覧）

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント / 保存ロジック
      - news_collector.py          — RSS 取得・前処理・保存
      - schema.py                  — DuckDB スキーマ定義・初期化
      - stats.py                   — zscore_normalize 等の統計ユーティリティ
      - pipeline.py                — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py     — market_calendar 管理・営業日ユーティリティ
      - features.py                — features インターフェース（再エクスポート）
      - audit.py                   — 監査ログテーブル定義
      - (その他 data 関連モジュール)
    - research/
      - __init__.py
      - factor_research.py         — モメンタム / ボラティリティ / バリュー計算
      - feature_exploration.py     — 将来リターン / IC / summary 等
    - strategy/
      - __init__.py
      - feature_engineering.py     — build_features 実装
      - signal_generator.py        — generate_signals 実装
    - execution/                   — 発注/約定/ポジション管理関連（パッケージ雛形）
    - monitoring/                  — 監視・メトリクス系（存在想定）

---

## 運用・注意点

- 環境（KABUSYS_ENV）によって振る舞いを変える設計があります（development / paper_trading / live）。
  本番（live）では発注・監査・ログの扱いに注意してください。
- J-Quants API のレート制限（120 req/min）を respect する実装（固定間隔スロットリング）がありますが、運用側でも呼び出し間隔に注意してください。
- ニュース RSS の取得は外部ネットワークに依存します。SSRF 対策や受信サイズ制限などの安全対策を実装済みです。
- DuckDB スキーマは冪等性を考慮して作られていますが、バックアップ・バージョン管理は運用で確保してください。
- 本ライブラリは発注処理の最終送信（証券会社との接続）や本番口座への送金などを自動で行うものではありません。発注フローを本番で使う場合は十分な監査・テストを行ってください。

---

## 参考・開発ヒント

- 開発中に自動で .env を読み込ませたくない場合:
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB をメモリで試す:
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
- ロギングは標準 logging を使用。ローカルで詳細デバッグしたい場合は LOG_LEVEL=DEBUG を設定。

---

質問や追加したいサンプル（例: Docker 化、CI/CD、より詳細な起動スクリプト）などがあれば教えてください。README をそれに合わせて拡張します。