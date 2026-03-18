# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
J-Quants / kabuステーション 等の外部データ・API と連携して、データ収集（ETL）、品質チェック、ニュース収集、監査ログ・スキーマ管理などの基盤機能を提供します。

## 特徴（概要）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）およびリトライ（指数バックオフ）、トークン自動更新を実装
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止
- DuckDB ベースのスキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義を提供
  - 冪等性を保った保存（ON CONFLICT/DO UPDATE 等）
- ETL パイプライン
  - 差分更新・バックフィル・市場カレンダー先読み・品質チェックを一貫して実行
  - 品質チェック結果を収集して呼び出し元が判断可能（Fail-Fast ではない）
- ニュース収集
  - RSS フィードから記事を収集、前処理して raw_news に保存
  - URL 正規化（UTM 等除去）による冪等性、SSRF 対策、gzip/サイズ制限等による堅牢性
  - 記事と銘柄コードの紐付け機能（既知銘柄リストが利用可能な場合）
- カレンダー管理
  - market_calendar を使った営業日判定・前後営業日の取得等ユーティリティ
  - JPX カレンダーの差分更新ジョブを提供
- 監査（Audit）ログ
  - シグナル→発注→約定までのトレース可能な監査スキーマ（UUID ベースの追跡）
  - 発注の冪等化 / ステータス管理をサポート
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合（未来日付／非営業日）等を検出

## 要件
- Python 3.10 以上（PEP 604 の型構文等を利用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- （任意）ネットワークアクセス：J-Quants API / RSS フィード / kabuステーション への接続

※パッケージ管理ファイル（pyproject.toml / requirements.txt）が無い場合は上記を環境にインストールしてください。

例:
pip install duckdb defusedxml

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （任意）pip install -e . などパッケージ化している場合はそれに従う

4. 環境変数を設定（詳細は次節）
   - 開発時はプロジェクトルートに `.env` を置くと自動で読み込まれます（既定）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

## 必要な環境変数（主要）
以下はコード内 Settings クラスで参照する環境変数です。必須のものは未設定時に例外を投げます。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（ID トークン取得に使用）
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
  - kabuステーション API のベース URL
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot のトークン
- SLACK_CHANNEL_ID (必須)
  - Slack チャネル ID
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
  - DuckDB ファイルパス（":memory:" を指定してインメモリ可）
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
  - 監視用 SQLite のパス（プロジェクトに合わせて）
- KABUSYS_ENV (任意、デフォルト: development)
  - 有効値: development, paper_trading, live
  - is_live / is_paper / is_dev 判定に影響
- LOG_LEVEL (任意、デフォルト: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

.envの自動読み込み挙動:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に、
  `.env` を読み込み（既存環境変数は上書きしない）次に `.env.local` を上書き
- 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化

## 使い方（利用例）

以下は主要なユースケースの簡単なコード例です（Python REPL / スクリプト）。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルが無ければ親ディレクトリを作成
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # デフォルトで今日を対象に ETL 実行
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# sources をカスタム辞書で指定可能。known_codes は既知銘柄コード集合（例: {"7203","6758"}）
stats = run_news_collection(conn, sources=None, known_codes=None, timeout=30)
print(stats)  # {source_name: 新規保存数}
```

4) 監査ログ（Audit）スキーマの初期化（別 DB を使う場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

5) J-Quants トークンを直接取得（テスト等）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を利用
```

## よく使う関数・モジュール一覧
- kabusys.config.settings
  - 環境変数経由の設定取得
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系関数（DuckDB への保存）
  - get_id_token()
- kabusys.data.pipeline
  - run_daily_etl(), run_prices_etl(), run_financials_etl(), run_calendar_etl()
- kabusys.data.news_collector
  - fetch_rss(), save_raw_news(), run_news_collection()
- kabusys.data.calendar_management
  - is_trading_day(), next_trading_day(), prev_trading_day(), get_trading_days(), calendar_update_job()
- kabusys.data.quality
  - run_all_checks(), check_missing_data(), check_spike(), check_duplicates(), check_date_consistency()
- kabusys.data.audit
  - init_audit_schema(), init_audit_db()

## ディレクトリ構成（抜粋）
以下はコードベースの主要なファイル・モジュール構成です。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント＆保存ロジック
    - news_collector.py            -- RSS ニュース収集・保存
    - schema.py                    -- DuckDB スキーマ定義・初期化
    - pipeline.py                  -- ETL パイプライン
    - calendar_management.py       -- マーケットカレンダー管理
    - audit.py                     -- 監査ログスキーマ
    - quality.py                   -- データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は現時点で実装されている主要モジュールを示します）

## 開発ノート / 設計方針（要点）
- ETL は差分更新とバックフィルを組み合わせ、API の後出し修正（訂正）を吸収します。
- すべての永続化処理はできるだけ冪等（ON CONFLICT 等）を意識して実装されています。
- ニュース収集では SSRF / XML Bomb / Gzip Bomb / 大容量レスポンス等を考慮した堅牢な実装を目指しています。
- 監査ログは削除しない前提で設計され、発注の冪等化とトレース性に重点を置いています。
- 品質チェックは問題を収集し、呼び出し元が重大度に応じて処理を決定できるようにしています。

## ログレベル / 実行環境
- ログレベルは環境変数 LOG_LEVEL で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- 実運用では KABUSYS_ENV を `paper_trading` / `live` に切り替え、is_live/is_paper を参照した振る舞いを実装してください。

---

ご不明点や README に追記したいサンプル（例：systemd ユニット、cron での日次実行例、CI 設定等）があれば教えてください。必要に応じて実際の実行コマンド例や .env.example のテンプレートも作成します。