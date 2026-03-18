# KabuSys

バージョン: 0.1.0

日本株向けの自動売買・データ基盤ライブラリ。J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に保存し、特徴量作成やリサーチ、ニュース収集、監査ログ（発注〜約定トレース）等を行うためのモジュール群を提供します。

主な設計方針:
- DuckDB をデータストアに採用（軽量かつ分析向け）
- API 呼び出しは冪等（ON CONFLICT / DO UPDATE）で保存
- Look‑ahead bias 対策のため取得時刻（fetched_at）を記録
- ETL / 品質チェック / カレンダー管理 / ニュース収集等を分離して実装
- 外部依存は最小限（duckdb, defusedxml 等）

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local / OS 環境変数から設定を自動ロード（プロジェクトルート検出）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD

- データ取得（J‑Quants API クライアント）
  - 株価日足: fetch_daily_quotes
  - 財務データ: fetch_financial_statements
  - JPX カレンダー: fetch_market_calendar
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - 取得結果を DuckDB に保存する save_* 関数（冪等）

- ETL / パイプライン
  - 日次 ETL (run_daily_etl): カレンダー、株価、財務データの差分取得 + 品質チェック
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl

- データスキーマ初期化
  - init_schema(db_path) で DuckDB の全テーブル（Raw / Processed / Feature / Execution）を作成

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（quality モジュール）

- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip チェック、XML パース対策）
  - raw_news 保存、記事ID の正規化（URL → SHA256）
  - 記事と銘柄コードの紐付け機能

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル生成（init_audit_schema / init_audit_db）
  - 発注から約定までのトレーサビリティを保持

- リサーチ用ユーティリティ
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン計算: calc_forward_returns
  - IC（Spearman ρ）計算: calc_ic
  - ファクター統計サマリー: factor_summary, rank
  - 正規化ユーティリティ: zscore_normalize

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部で | 型注釈を使用）
- DuckDB を利用するためネイティブパッケージが必要（pip で duckdb をインストール）

例: 仮想環境を作成して依存をインストールする

1. 仮想環境作成・有効化（任意）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 必須パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / poetry があればそれに従ってください）

3. 環境変数 / .env 設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に自動で .env/.env.local を読み込みます。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J‑Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot token（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

例 .env（簡略）
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（基本例）

以下は最小限の Python スクリプト／REPL 操作例です。

1) データベーススキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（J‑Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

# conn は init_schema で作成した接続
result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードのセット（抽出と紐付けに利用）
known_codes = {"7203", "6758", "9984"}  # 例
counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(counts)
```

4) 監査用スキーマの初期化（別 DB に分ける場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

5) リサーチ系ユーティリティの利用例
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

# 各関数は DuckDB 接続と target_date を受け取り、(date, code) キーの dict リストを返す
mom = calc_momentum(conn, target_date=date.today())
vol = calc_volatility(conn, target_date=date.today())
val = calc_value(conn, target_date=date.today())

# 将来リターンと IC
fwd = calc_forward_returns(conn, target_date=date.today(), horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

注意点:
- J‑Quants への API 呼び出しはレート制限・リトライが組み込まれていますが、トークンやネットワーク情報は正しく設定してください。
- ETL は差分更新を行います（既に取得済みの範囲は再取得しませんが、backfill_days により直近数日を再取得して後出し修正を吸収します）。

---

## ディレクトリ構成

主要ファイル / モジュールを以下に示します（抜粋）。

- src/kabusys/
  - __init__.py                     -- パッケージのエントリ（バージョン等）
  - config.py                        -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J‑Quants API クライアント（fetch/save）
    - news_collector.py              -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                      -- DuckDB スキーマ定義 / init_schema
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py         -- market_calendar 管理、営業日ロジック
    - stats.py                       -- zscore_normalize 等統計ユーティリティ
    - features.py                    -- 特徴量関連の公開インターフェース
    - etl.py                         -- ETLResult の公開
    - quality.py                     -- データ品質チェック
    - audit.py                       -- 監査ログ用スキーマ初期化
  - research/
    - __init__.py
    - feature_exploration.py         -- 将来リターン / IC / summary
    - factor_research.py             -- momentum/value/volatility ファクター計算
  - strategy/                         -- 戦略関連（骨組み）
  - execution/                        -- 発注 / 実行関連（骨組み）
  - monitoring/                       -- 監視・モニタリング（骨組み）

各モジュールの責務はファイル先頭の docstring および関数 docstring に詳述されています。

---

## 開発 / テストのヒント

- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準に実施されます。テスト時に自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の :memory: を使えばインメモリでスキーマ初期化・テストが可能です。
  - 例: init_schema(":memory:")
- ネットワーク呼び出しを伴う関数は id_token を引数で注入可能な設計になっているため、テストではモックやスタブを渡して外部依存を切り離せます。
- news_collector では defusedxml を使用しているため、XML 関連の脆弱性対策が施されています。

---

## 連絡 / 貢献

この README はコードベースの docstring を元に作成しています。追加の機能や改善提案、バグ報告は Issue／Pull Request を通じてお願いします。

--- 

以上。必要であれば README にサンプルワークフロー（cron で ETL を回す例や Slack 通知の仕組み）を追加します。どのようなユースケースを優先して記載するか教えてください。