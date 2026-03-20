# KabuSys — 日本株自動売買プラットフォーム（README）

本リポジトリは日本株向けのデータプラットフォームと戦略層を含む自動売買基盤の実装（プロトタイプ）です。  
主に DuckDB をデータ層に用い、J-Quants からのデータ取得、ニュース収集、特徴量作成、シグナル生成、発注監査ログ等の主要コンポーネントを備えます。

---

## 概要

KabuSys は次の層で構成される自動売買基盤です。

- Data Layer
  - J-Quants API クライアントによる株価・財務・マーケットカレンダーの取得
  - RSS ベースのニュース収集（SSRF/XML攻撃対策、トラッキングパラメータ除去）
  - DuckDB に対する冪等な保存（ON CONFLICT 処理）
  - スキーマ定義・初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- Research / Feature
  - ファクター計算（モメンタム・ボラティリティ・バリューなど）
  - ファクター探索・IC 計算・将来リターン計算
  - Z スコア正規化などの統計ユーティリティ
- Strategy
  - 特徴量組立（feature テーブル作成）
  - シグナル生成（AI スコア統合、Bear フィルタ、BUY/SELL 判定）
- Execution / Audit（スキーマ・監査ログ）
  - signals / orders / executions / positions 等のテーブル定義
  - 監査テーブルでトレース可能な UUID ベースの連鎖

設計方針として、ルックアヘッドバイアスを避けるために target_date 時点のデータのみを使用し、発注 API への直接依存を持たないモジュール分離を行っています。

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）・リトライ・トークン自動リフレッシュ実装
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（スパイク・欠損など）
  - 日次 ETL 実行入口 run_daily_etl
- DuckDB スキーマ管理
  - init_schema で必要なテーブル・インデックスを冪等に作成
- ニュース収集
  - RSS フィード取得、URL 正規化（utm 等削除）、記事ID の SHA-256 による冪等性
  - SSRF 回避、gzip 制限、XML パースの安全化（defusedxml）
- Feature / Strategy
  - calc_momentum / calc_volatility / calc_value（research）
  - build_features（特徴量を features テーブルへ UPSERT）
  - generate_signals（features と ai_scores を統合して BUY/SELL を生成）
- Research ユーティリティ
  - 将来リターン、IC（Spearman）計算、factor_summary、rank
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings API
  - 必須環境変数チェック

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール方法の例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを編集可能モードでインストールする場合
pip install -e .
```

（プロダクションで使う場合は適宜 requirements.txt / poetry を整備してください）

---

## セットアップ手順

1. リポジトリをクローンしてソースを配置
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. .env を用意する
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャネル ID（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV（development/paper_trading/live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
     - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
4. データベース初期化（DuckDB スキーマ）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# settings.duckdb_path を使用する例
conn = init_schema(settings.duckdb_path)
# またはメモリ DB を使う場合
# conn = init_schema(":memory:")
```

---

## 使い方（簡易ガイド）

以下は主要な操作のサンプルコードです。実運用ではログ設定やエラーハンドリング、スケジューリング（cron / Airflow 等）を追加してください。

1. 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2. マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

3. ニュース収集（既知銘柄コードセットと併用）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 実運用では銘柄マスター等から準備
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

4. 特徴量構築 → シグナル生成
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features, generate_signals

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 15)

n_features = build_features(conn, target)
print("features upserted:", n_features)

n_signals = generate_signals(conn, target)
print("signals written:", n_signals)
```

5. J-Quants からのデータ取得（クライアントを直接使う）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

---

## 主要な設定 / 環境変数

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 任意。1 を設定すると .env 自動ロードを無効化

注意: settings オブジェクト（kabusys.config.settings）からこれらを取得できます。必須変数が未設定の場合は ValueError が発生します。

---

## ディレクトリ構成

主要なファイル/モジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS ニュース取得・保存
    - schema.py                     — DuckDB スキーマ定義・初期化
    - stats.py                      — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — マーケットカレンダー管理
    - features.py                   — features 公開インターフェース
    - audit.py                      — 監査ログ / 発注トレース DDL
    - quality.py?                   — （品質チェック）※存在する場合
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — features 作成
    - signal_generator.py           — シグナル生成
  - execution/                      — 発注関連（空パッケージのままの場合あり）
  - monitoring/                     — 監視用モジュール（存在する場合）

（実際のリポジトリでは上記に加えて README / pyproject.toml / .env.example 等が含まれることが想定されます）

---

## 実装上の注意・留意点

- ルックアヘッドバイアス対策: 各処理は target_date 時点で利用可能なデータのみを使う設計です。
- 冪等性: DB への挿入は ON CONFLICT を使って冪等にしています（重複更新を許容）。
- J-Quants API: rate limit（120 req/min）を守るため固定スロットリングを実装しています。401 はリフレッシュトークンで自動リフレッシュします。
- ニュース収集: SSRF 対策・受信サイズ制限・defusedxml を利用した安全な XML パースを行っています。
- DuckDB スキーマ: init_schema は存在しない親ディレクトリを自動作成し、すべての DDL をトランザクションで実行します。
- 環境変数の自動読み込み: プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

---

## 開発・拡張のヒント

- テスト: ETL / API 呼び出し部分は id_token 注入や HTTP 呼び出しのモックが行えるよう設計されています。単体テストでは jquants_client._request や news_collector._urlopen などをモックすると良いです。
- スケジューリング: 日次 ETL、ニュース収集、カレンダー更新等は cron / systemd timer / Airflow 等で定期実行してください。
- 発注層統合: strategy 層は発注 API に依存しないため、execution 層を実装して kabu/station API などと接続してください。audit/order_requests テーブルは冪等キー設計を前提としています。
- モニタリング: Slack 通知や監視ダッシュボードと連携して品質問題やエラーを可視化してください。

---

必要に応じて README に追加してほしい項目（例: API 利用例の詳細、.env.example のテンプレート、運用フロー図、CI 設定など）があれば教えてください。