# KabuSys

日本株向けの自動売買基盤ライブラリ（パッケージ名: kabusys）。  
J-Quants / kabuステーション 等の外部 API からデータを取得して DuckDB に蓄積し、ETL、データ品質チェック、ニュース収集、監査ログなどを提供します。戦略・発注・監視の各層と連携して、自動売買システムのバックエンド基盤として利用できます。

バージョン: 0.1.0

## 主要機能
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限・リトライ・トークン自動リフレッシュ・ページネーション対応
  - 取得時刻（fetched_at）を記録して Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- ニュース収集
  - RSS フィード取得、URL 正規化（UTM 等削除）、SHA-256 ベースの記事 ID 発行
  - SSRF 対策、受信サイズ制限、XML の安全パース（defusedxml）
  - raw_news / news_symbols への冪等保存・銘柄抽出
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブルDDL定義
  - スキーマ初期化・接続ユーティリティ
- ETL パイプライン
  - 差分更新（最終取得日計算＋バックフィル）、カレンダー先読み
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 日次 ETL 実行エントリポイント（run_daily_etl）
- 監査ログ（Audit）
  - signal → order_request → execution に至る UUID 連鎖で完全トレーサビリティを保持
  - 発注要求の冪等キーやステータス遷移管理
- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定を Settings クラス経由で取得

## 必須・推奨依存パッケージ
- Python 3.10+
- duckdb
- defusedxml
- （標準ライブラリ: urllib, logging, datetime 等）

（実際のパッケージ化時は pyproject.toml / requirements.txt を作成し依存を明示してください）

## セットアップ手順（開発環境向け）

1. リポジトリをクローン／配置し、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows の場合は .venv\Scripts\activate)

2. 依存パッケージをインストールします（例）:
   - pip install duckdb defusedxml

3. パッケージをインストール（ローカル開発モード）:
   - pip install -e .

4. 環境変数を設定します。プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主に必要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 BOT トークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（任意、デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルのパス（任意、デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（任意、デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（任意、デフォルト development）
- LOG_LEVEL: DEBUG / INFO / ...（任意、デフォルト INFO）

.env 例（実務では機密情報は管理に注意）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## 使い方（主要な API と利用例）

以下は Python REPL やスクリプト内での利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリは自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

2) J-Quants からデータ取得・保存（個別利用）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

# id_token は自動で settings.jquants_refresh_token から取得されます
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

3) 日次 ETL 実行（カレンダー, 株価, 財務, 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date 省略で本日
print(result.to_dict())
```

4) RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 銘柄抽出に使う有効な4桁コードの集合（必要なら取ってくる処理を実装）
known_codes = {"7203", "6758", ...}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

5) データ品質チェック単体実行
```python
from kabusys.data import quality

issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注記:
- ネットワーク呼び出し（J-Quants / RSS）は外部に依存するため、テスト時は該当関数をモックしてください。news_collector は _urlopen を差し替え可能です。
- jquants_client は API レート制限やリトライを組み込んでいます。ID トークンはモジュール内でキャッシュ・自動更新されます。

## よく使うモジュールと主要関数（抜粋）
- kabusys.config
  - settings: 設定プロパティ（jquants_refresh_token, kabu_api_password, slack_bot_token, ...）
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, ...)
- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

## ディレクトリ構成（主要ファイル）
プロジェクトは src/kabusys 配下に実装されています。主要ファイルの一覧（一部抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       - 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py             - J-Quants API クライアント
      - news_collector.py             - RSS ニュース収集
      - schema.py                     - DuckDB スキーマ定義・初期化
      - pipeline.py                   - ETL パイプライン（差分更新・日次ETL）
      - audit.py                      - 監査ログ（signal/order/execution）
      - quality.py                    - データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py                    - 戦略層（拡張ポイント）
    - execution/
      - __init__.py                    - 発注・ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py                    - モニタリング（拡張ポイント）

各モジュールは用途別に分かれており、戦略・発注部分は拡張ポイントとして空のパッケージが用意されています。

## 運用上の注意
- 環境変数に機密情報（API トークン等）を直接置く場合は管理に注意してください。CI/シークレットマネージャ等の利用を推奨します。
- DuckDB ファイルはバックアップや永続化方針を検討してください（ファイル破損や同時書き込みの扱い）。
- J-Quants 等 API の利用規約・レート制限を遵守してください。本実装は 120 req/min を想定したスロットリングを実装しています。
- 本パッケージは基盤ライブラリです。実際の自動売買運用時は戦略の検証、発注の安全性（ポジション管理、リスク制御、二重発注防止等）を十分に実装してください。

---

不明点や README に追加したい操作（例: CLI や systemd / cron による定期実行サンプル、バックテスト手順等）があれば教えてください。必要に応じて追記・サンプルスクリプトを作成します。