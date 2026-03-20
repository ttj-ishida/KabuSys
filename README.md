# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS 等から市場データを収集し、DuckDB 上で加工・特徴量生成、戦略シグナル生成までを行うためのモジュール群を提供します。

主な設計方針は以下の通りです。
- 取得データはすべて時刻情報を保持してトレース（look-ahead bias 対策）。
- DuckDB を中心に冪等（idempotent）操作を行う（ON CONFLICT / INSERT ... RETURNING 等）。
- 外部 API 呼び出しにはレート制御・リトライ・トークン自動更新などの安全対策を実装。
- Research 層は本番発注ロジックに依存しない（安全な解析が可能）。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）: data/jquants_client.py
  - RSS ニュース収集器（正規化・SSRF対策・トラッキング削除）: data/news_collector.py
  - ETL パイプライン（差分取得・バックフィル・品質チェック）: data/pipeline.py
  - マーケットカレンダー管理ジョブ: data/calendar_management.py

- データ層・スキーマ
  - DuckDB 用スキーマ定義と初期化ユーティリティ: data/schema.py
  - raw / processed / feature / execution の多層スキーマ設計
  - 監査ログ（signal / order / execution トレース）: data/audit.py

- 研究（Research）機能
  - ファクター計算（Momentum / Value / Volatility / Liquidity）: research/factor_research.py
  - 特徴量探索・IC / forward returns / 統計サマリー: research/feature_exploration.py
  - z-score 正規化ユーティリティ: data/stats.py

- 戦略（Strategy）機能
  - 特徴量構築（features テーブルへの UPSERT、ユニバースフィルタ、標準化）: strategy/feature_engineering.py
  - シグナル生成（features + ai_scores を統合して final_score を計算し signals に保存）: strategy/signal_generator.py

- その他
  - 設定管理（.env 自動ロード、環境判定、必須項目チェック）: config.py
  - ニュース → 銘柄紐付け（記事ID生成、news_symbols 管理）
  - RateLimiter / リトライロジック / SSRF 対策などの堅牢性設計

---

## 必要条件

- Python 3.9+
- DuckDB（Python パッケージ: duckdb）
- （任意）defusedxml（news RSS パースの安全対策で使用）
- 標準ライブラリ以外の依存はモジュールによって必要となります。requirements.txt があればそちらを参照してください（本リポジトリには明示的な requirements ファイルは含まれていません）。

推奨:
- 仮想環境（venv / pipenv / poetry）を利用すること。

---

## セットアップ手順

1. リポジトリをクローン / ソースを取得

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージのインストール（例）
   - pip install duckdb defusedxml

   （プロジェクトに requirements を追加している場合はそれを使用してください）

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（config.py による自動ロード）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須となる主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使用する場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意 / デフォルト:
   - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/... （デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）

   例 `.env`（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化
   Python REPL かスクリプトから schema.init_schema を呼び出して DB を初期化します。

   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # 親ディレクトリを自動作成
   conn.close()
   ```

---

## 使い方（主要ユースケース）

以下はライブラリをインポートして利用する最小例です。実運用では logging の設定や例外処理を追加してください。

- 日次 ETL（市場カレンダー・株価・財務の差分取得＋品質チェック）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（まだなら）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

- 特徴量構築（features テーブルへの書き込み）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへ）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print(f"signals generated: {count}")
```

- ニュース収集・保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄の紐付けも実行される
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
print(res)
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- J-Quants 生データ取得（クライアントを直接使用する場合）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.data.schema import get_connection
from datetime import date

token = get_id_token()  # settings.jquants_refresh_token を使って自動取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
# 保存: save_daily_quotes を使う
```

注意:
- generate_signals や build_features は DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, positions など）を前提とします。事前に ETL とスキーマ初期化を行ってください。
- 発注や execution 層（kabu API）を使う場合は追加の設定（KABU_API_PASSWORD 等）や実際の broker 接続ロジックが必要です。本リポジトリの execution パッケージは発注ロジックの橋渡し実装用です（ファイルは含まれていますが、外部依存のため設定が必要）。

---

## 設定・挙動の補足

- 自動 .env ロード
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）から `.env` → `.env.local` の順で自動読み込みします（既存の OS 環境変数は上書きされませんが `.env.local` は override=True で上書き可能）。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 環境モード
  - KABUSYS_ENV は `development`, `paper_trading`, `live` のいずれかで、settings.is_live / is_paper / is_dev が使用できます。

- ロギング
  - LOG_LEVEL でログレベルを指定します（例: DEBUG, INFO）。コード内では logger を多用しており、外部からの logging.basicConfig 等で制御してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なファイル・モジュール構成は以下のとおりです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/  (監視関連のモジュール格納想定)
  - その他: README.md / pyproject.toml 等（プロジェクトルート）

（上記は本 README に含まれるコードベースに基づく主要ファイル一覧です。）

---

## 開発者向けノート / ベストプラクティス

- DuckDB はローカルファイル（既定: data/kabusys.duckdb）を使います。CI やユニットテストでは ":memory:" を渡してインメモリ DB を使うと便利です。
- ETL を定期実行する場合は以下を推奨します:
  - まず calendar_update_job を走らせて市場カレンダーを取得し、営業日調整を可能にする
  - その後 run_daily_etl を走らせる
  - ETL の後に build_features → generate_signals の順で処理
- 外部 API トークンは必ず安全に管理してください（Vault 等の使用を推奨）。
- production（live）では `KABUSYS_ENV=live` を設定して安全上のフラグ／振る舞いを切り替えてください。

---

## ライセンス・免責

- 本 README はコードベースの説明を目的としています。実際の運用に際しては適切なテスト・監査を行ってください。
- 金融商品取引にはリスクがあります。本ライブラリを用いた売買で発生した損失については責任を負いません。

---

必要であれば、この README に以下の追記が可能です:
- 具体的な requirements.txt の候補
- サンプル cron / systemd ユニットファイル（ETL の定期実行例）
- より詳細な DB スキーマドキュメント（各テーブル説明）
- ユニットテストの実行方法

どれを追加しますか？