# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / データプラットフォームのプロトタイプライブラリです。J-Quants など外部データソースからのデータ取得、DuckDB を用いたデータベーススキーマ、ETL パイプライン、特徴量エンジニアリング、シグナル生成、ニュース収集、マーケットカレンダー管理などを通して、戦略の研究〜運用までのワークフローをサポートします。

主な設計方針:
- ルックアヘッドバイアスを防ぐ設計（target_date 時点のデータのみを使用）
- DuckDB によるローカルデータ管理（冪等性を考慮した保存）
- 外部 API 呼び出しはレート制御・リトライを実装
- research 層と execution 層を明確に分離

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（price / financials / market calendar）
  - API レート制御、リトライ、トークン自動リフレッシュ
  - raw データの DuckDB への冪等保存（ON CONFLICT を活用）
- ETL パイプライン
  - 日次差分 ETL（run_daily_etl）
  - 市場カレンダー ETL（calendar_update_job）
  - バックフィル・品質チェック連携
- データスキーマ
  - raw / processed / feature / execution 層の DuckDB スキーマ定義（init_schema）
- ニュース収集
  - RSS フィード取得、前処理、raw_news / news_symbols への保存
  - SSRF 対策、レスポンスサイズ制限、トラッキングパラメータ除去
- 研究（research）ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量・戦略
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）
  - BUY / SELL のルール（閾値、Bear レジーム抑制、ストップロス 等）
- 監査・実行ログ（スキーマ側でサポート）
  - signal_events / order_requests / executions などの監査テーブル定義

---

## 要求環境 / 依存パッケージ

推奨:
- Python 3.10 以上（ソース内で `X | None` 等の構文を使用）
必須パッケージ（最小）:
- duckdb
- defusedxml

例: requirements.txt（プロジェクトに合わせて拡張してください）
```
duckdb
defusedxml
```

インストール例:
```bash
python -m pip install -r requirements.txt
# または開発インストール
python -m pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン／プロジェクトを配置
2. Python 仮想環境を作成して依存をインストール
3. 環境変数を設定（.env を推奨）

自動環境変数読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml がある場所）から `.env` および `.env.local` を自動で読み込みます。
- テスト等で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

任意 / システム設定
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: デフォルト `data/monitoring.db`
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

例 (.env):
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本ワークフロー例）

以下は最小限の Python スクリプト例です。DuckDB スキーマ初期化 → 日次 ETL → 特徴量構築 → シグナル生成 の流れです。

```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

# DB 初期化（ファイルパス or ":memory:"）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると today）
etl_result = run_daily_etl(conn)

# ETL 結果を確認
print(etl_result.to_dict())

# 特徴量構築（ETL で prices_daily / raw_financials を準備した上で）
today = date.today()
n_features = build_features(conn, today)
print(f"features built: {n_features}")

# シグナル生成（デフォルト threshold=0.60）
n_signals = generate_signals(conn, today)
print(f"signals generated: {n_signals}")
```

ニュース収集を実行する例:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は既知の銘柄コード集合（抽出精度向上のため）
known_codes = {"7203","6758", "9984", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

注意:
- API トークンや環境変数が正しく設定されている必要があります。
- ETL 実行中にネットワークや API のエラーがあっても、各ステップは独立にエラーハンドリングされ、可能な限り他ステップを継続します（ETLResult.errors に記録）。

---

## 主な API（モジュール）

- kabusys.config.settings
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live 等
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features, generate_signals

---

## ディレクトリ構成

プロジェクトの主要ファイル／ディレクトリは以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                          -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                 -- J-Quants API クライアント
    - news_collector.py                 -- RSS ニュース収集
    - pipeline.py                       -- ETL パイプライン
    - schema.py                         -- DuckDB スキーマ定義 / init_schema
    - calendar_management.py            -- カレンダー管理ユーティリティ
    - features.py                       -- 再エクスポート（zscore_normalize）
    - stats.py                          -- 統計ユーティリティ（z-score 等）
    - audit.py                          -- 監査ログスキーマ
    - (その他: quality.py 等が想定される)
  - research/
    - __init__.py
    - factor_research.py                -- モメンタム / バリュー / ボラティリティ算出
    - feature_exploration.py            -- IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py            -- features テーブル構築
    - signal_generator.py               -- signals テーブル生成
  - execution/                          -- 発注・実行関連（パッケージ化の準備）
  - monitoring/                         -- 監視 / メトリクス（実装場所）

その他:
- .env / .env.local                     -- 環境変数（プロジェクトルートに置く）
- data/                                 -- デフォルトの DuckDB ファイルなどを置くディレクトリ

---

## 注意点 / 実運用に向けた留意事項

- 本リポジトリは実運用システムの設計を模した構成ですが、本番環境にデプロイする前に以下を確認してください:
  - エラーハンドリング・監視・アラートの整備
  - 発注（execution）層の堅牢化と証券会社 API の安全確認
  - シークレット（トークン）の安全な管理（Vault 等の導入）
  - テストカバレッジとモックによる外部依存の切替
- データベースファイル（例: data/kabusys.duckdb）はバックアップ / 権限制御を行ってください。
- J-Quants API のレート制限や利用規約に従ってください。

---

問題や改善提案があれば、コード内のログや docstring を参考に拡張してください。README の内容をプロジェクトドキュメントとして必要に応じて追記・修正してください。