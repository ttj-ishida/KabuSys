# KabuSys — 日本株自動売買基盤 (README)

このリポジトリは日本株向けの自動売買プラットフォームのコアライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、シグナル計算、ニュース収集、マーケットカレンダー管理、監査ログなど、投資戦略のバックエンド処理を目的としたモジュール群を含みます。

主な対象：研究・ペーパートレード・実運用のサポート（コードは戦略層とデータ層を分離して設計されています）。

---

## 主な機能

- J-Quants API クライアント（取得・リトライ・レート制御・トークンリフレッシュ）
- DuckDB を使ったデータスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（コンポーネントスコアの統合、BUY/SELL判定、エグジットロジック）
- ニュース収集（RSS → 正規化 → DB 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day等）
- 監査ログ（シグナル→発注→約定のトレース用テーブル）

---

## 前提条件

- Python 3.9+
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml

実際にはプロジェクトの pyproject.toml / requirements.txt を参照してインストールしてください。最小限の例は以下のとおりです。

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# （プロジェクト配布用に pyproject.toml がある場合）
pip install -e .
```

---

## 環境変数（必須 / 任意）

このパッケージは .env / .env.local / OS 環境変数を読み込みます（優先度: OS > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

主な環境変数（必須のものは実行機能に応じて必要）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（J-Quants API 利用時必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能を使う場合）
- KABU_API_BASE_URL — kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知機能を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

サンプル .env（.env.example を用意しておくことを推奨）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易手順）

1. リポジトリをクローンし作業環境を作成

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# もし pyproject.toml があるなら
pip install -e .
```

2. 環境変数設定

プロジェクトルートに `.env` / `.env.local` を置く。必要なキーを設定します（上記参照）。

3. DuckDB スキーマ初期化

Python からスキーマを初期化します（デフォルトで DUCKDB_PATH の親ディレクトリが自動作成されます）。

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

---

## 使い方（主要なユースケース）

以下はライブラリを直接利用する簡単な例です。スクリプト化してスケジューラ（cron / Airflow / Prefect 等）から呼び出す想定です。

- 日次ETL（市場カレンダー・株価・財務を差分取得して保存／品質チェック）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）構築

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"upserted features: {count}")
```

- シグナル生成（features と ai_scores を基に signals テーブルへ保存）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total_signals}")
```

- ニュース収集ジョブ（RSS 取得 → raw_news / news_symbols へ保存）

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# known_codes は銘柄抽出のための有効コード集合（optional）
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)
```

- マーケットカレンダー更新（夜間バッチ）

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意: J-Quants を呼び出す機能を使う場合は JQUANTS_REFRESH_TOKEN が必要です。kabu（発注）関連の機能は KABU_API_PASSWORD 等が必要です。

---

## 主要モジュールと使いどころ

- kabusys.config
  - 環境変数管理、自動 .env ロード、settings オブジェクト提供
- kabusys.data.schema
  - DuckDB スキーマの定義・初期化（init_schema）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し / データ保存ユーティリティ
- kabusys.data.pipeline
  - ETL 主処理（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- kabusys.data.news_collector
  - RSS 取得・正規化・DB 保存・銘柄抽出
- kabusys.research.*
  - 研究用のファクター計算・解析ユーティリティ（calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic など）
- kabusys.strategy.feature_engineering
  - features テーブル生成（build_features）
- kabusys.strategy.signal_generator
  - signals テーブル生成（generate_signals）
- kabusys.data.audit
  - 発注/約定等をトレースする監査ログ用 DDL / 初期化等

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境設定読み込み（.env 自動ロード）
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント・保存ロジック
      - news_collector.py            — RSS ニュース収集・保存
      - schema.py                    — DuckDB スキーマ定義・初期化
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - stats.py                     — 統計ユーティリティ（zscore_normalize）
      - features.py                  — features 再エクスポート
      - calendar_management.py       — market_calendar 管理（is_trading_day 等）
      - audit.py                     — 監査ログ用 DDL と初期化支援
      - ...（その他データ層ユーティリティ）
    - research/
      - __init__.py
      - factor_research.py           — ファクター計算（momentum/volatility/value）
      - feature_exploration.py       — 研究用解析（forward returns, IC, summary）
    - strategy/
      - __init__.py
      - feature_engineering.py       — features 作成ロジック
      - signal_generator.py          — シグナル生成ロジック
    - execution/                      — 発注/実行層（未実装のインターフェース等）
    - monitoring/                     — 監視/モニタリング用コード（DB, Slack 通知など）

---

## 運用上の注意点 / 補足

- 環境（KABUSYS_ENV）が `live` の場合は実運用リスクがあります。実際の発注や資金管理を行う前に十分なテストを行ってください。
- J-Quants API のレート制限（120 req/min）やリトライロジックは jquants_client に組み込まれていますが、実運用ではさらに上位でバッチ制御やスケジューリングを行うことを推奨します。
- ニュース収集では外部 RSS の扱いに注意（SSRF 対策、最大レスポンスサイズ制限、XML パースの保護などを実装済み）。
- DB スキーマは冪等に作成／更新される設計ですが、マイグレーション戦略は別途考慮してください（スキーマ変更時のデータ移行など）。

---

## 貢献 / 開発フロー（簡略）

- 新機能・修正はブランチを切り、Pull Request を作成してください。
- 重大変更（スキーマ変更など）はドキュメント（DataSchema.md など）と移行手順を含めてください。
- 自動テスト・型チェック（mypy 等）を導入することを推奨します。

---

ライセンス、詳細設計（StrategyModel.md / DataPlatform.md / DataSchema.md）などは別途ドキュメントを参照してください。

ご不明点や追加したいサンプル（CLI ラッパー、タスクスケジューラ設定例、docker-compose 等）があれば教えてください。README に追記します。