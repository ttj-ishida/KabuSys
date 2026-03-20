# KabuSys

日本株向けの自動売買（アルゴリズム取引）基盤ライブラリです。  
データ取得（J‑Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査ログなどを含む3層（Raw / Processed / Feature）設計のデータプラットフォームと戦略層ユーティリティを提供します。

---

## 特徴（概要）

- J‑Quants API 経由で株価・財務・カレンダーを取得し DuckDB に永続化（冪等保存）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 特徴量（Momentum / Volatility / Value / Liquidity 等）の計算と Z スコア正規化
- 特徴量と AI スコアを統合したシグナル生成（BUY / SELL）
- RSS ベースのニュース収集と銘柄紐付け（SSRF対策・トラッキングパラメータ除去・重複排除）
- マーケットカレンダー管理（JPX）と営業日ユーティリティ
- DuckDB スキーマ定義 / 初期化ユーティリティ
- 発注・監査ログ用スキーマ（実装済のDDL）を備える設計

---

## 主な機能一覧

- データ取得 / 保存
  - J‑Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT 対応）
- ETL
  - run_daily_etl（market calendar → prices → financials → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl
- データスキーマ
  - init_schema / get_connection（DuckDB）
- 特徴量 / 戦略
  - calc_momentum / calc_volatility / calc_value（research モジュール）
  - build_features（strategy.feature_engineering）
  - generate_signals（strategy.signal_generator）
- ニュース収集
  - fetch_rss / run_news_collection / save_raw_news / save_news_symbols
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 統計ユーティリティ
  - zscore_normalize（data.stats）
- 監査ログ用スキーマ（audit モジュールのDDL）

---

## 前提条件

- Python 3.10 以上（ソース内での型ヒントに `X | None` を使用）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - defusedxml

推奨: 仮想環境（venv / pyenv）を使用してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ配布用に setup.cfg/pyproject がある場合）pip install -e .
4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を配置可能
   - 自動ロード順: OS 環境 > .env.local > .env
   - 自動ロードを抑制する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから init_schema を呼び出す（下記 使用例参照）

---

## 環境変数（主なもの）

設定は environment または .env ファイルで行います。config.Settings を通じてアクセスされます。

- 必須
  - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
  - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- 任意 / デフォルトあり
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（値をセットすると無効化）
  - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（簡単な例）

以下は代表的な操作のサンプルです。プロジェクトの Python モジュールとして import して利用します。

1) DuckDB スキーマ初期化（ファイル DB）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J‑Quants から差分取得 → 保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量の構築（target_date の features を作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 10))
print(f"features upserted: {n}")
```

4) シグナル生成（features + ai_scores → signals）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 10))
print(f"signals written: {count}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# sources は {source_name: url} の辞書。省略時は DEFAULT_RSS_SOURCES。
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)
```

6) カレンダー更新ジョブ（夜間バッチ想定）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

補足:
- DuckDB をインメモリで使う場合は db_path に ":memory:" を渡せます（init_schema(":memory:")）。
- J‑Quants の API 呼び出しは rate limit やリトライを内包しているため通常は追加の制御不要です。

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要モジュールを抜粋したツリー例:

```
src/
  kabusys/
    __init__.py
    config.py

    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      features.py
      calendar_management.py
      audit.py
      stats.py

    research/
      __init__.py
      factor_research.py
      feature_exploration.py

    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py

    execution/            # 発注／約定関連（実装の拡張場所）
      __init__.py

    monitoring/           # 監視・アラート関連（拡張用）
      __init__.py
```

各モジュールの責務:
- kabusys/config.py: 環境変数読み込み・設定アクセス
- data/*.py: データ取得、保存、ETL、ニュース収集、カレンダー、スキーマ、統計ユーティリティ
- research/*.py: ファクター計算・研究用ユーティリティ（本番ロジックから切り離している）
- strategy/*.py: 特徴量の合成・正規化、シグナル生成ロジック
- execution/: 発注層への接続や注文管理の実装を想定

---

## 注意事項 / 実運用上のポイント

- 環境変数の自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行われます。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J‑Quants API の利用にはリフレッシュトークンが必要です。get_id_token が自動でトークンをリフレッシュしますが、環境変数は必ず正しく設定してください。
- DuckDB のファイルは適切にバックアップを取ることを推奨します。:memory: はテスト用です（永続化されません）。
- ニュース収集は外部URL を扱うため SSRF 対策や受信サイズ制限、XML パーサの防御（defusedxml）を実装済みですが、本番では追加の監視やサンドボックスを検討してください。
- KABUSYS_ENV は development / paper_trading / live のいずれかを指定し、運用条件に応じた安全措置（paper/trading では発注抑制など）を実装してください（本リポジトリではフラグ提供のみ）。

---

README はここまでです。必要であれば以下を追加できます:
- 具体的な SQL スキーマ（既に schema.py に記述済み）
- CI / テストの実行方法
- サンプルワークフロー（夜間 ETL → 特徴量構築 → シグナル生成 → 発注） のシェルスクリプト例
- さらに詳しい API ドキュメント（各関数のパラメータ・戻り値一覧）