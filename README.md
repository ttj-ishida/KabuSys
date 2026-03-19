# KabuSys

日本株向けの自動売買・データ基盤ライブラリ集（KabuSys）。  
データ収集（J-Quants）、DuckDB スキーマ管理、ETL パイプライン、ニュース収集、ファクター計算（研究用）などを含むモジュール群です。  
このリポジトリは戦略実装・研究・監視・発注までの各レイヤを想定したユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は以下のレイヤをサポートする Python モジュールの集合です。

- Data Layer（DuckDB ベース）: 生データ / 整形データ / 特徴量 / 発注関連テーブルを定義
- Data Ingestion: J-Quants API から株価・財務・カレンダーを安全かつ冪等的に取得・保存するクライアントと ETL パイプライン
- News Collector: RSS フィードから記事を収集・正規化し DuckDB に保存、記事と銘柄の紐付け
- Research: ファクター（モメンタム、ボラティリティ、バリュー等）計算・特徴量探索（IC計算等）
- Execution / Strategy / Monitoring: 発注やストラテジ層、監視用の雛形パッケージ（実装箇所あり）

設計上のポイント：
- DuckDB を中心としたオンディスク DB（またはメモリ DB）でデータを管理
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動更新を備える
- XML（RSS）パースで defusedxml を利用し安全性を重視
- ETL/保存処理は冪等（ON CONFLICT）を考慮

---

## 主な機能一覧

- 環境設定読み込み（`.env`, `.env.local`、自動ロード、無効化用フラグ）
- DuckDB スキーマ定義・初期化（data.schema.init_schema / init_audit_db）
- J-Quants API クライアント（レート制御、リトライ、トークンリフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で冪等保存
- ETL パイプライン（日次差分 ETL: run_daily_etl）
- ニュース収集（RSS 取得、前処理、DB 保存、銘柄抽出）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ファクター計算
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- 統計ユーティリティ（zscore_normalize）
- 監査（audit）スキーマの初期化ユーティリティ

---

## 動作条件（推奨）

- Python 3.10 以上（型記法に | を使用）
- 必要パッケージ（例）:
  - duckdb
  - defusedxml
- その他: ネットワークアクセス（J-Quants API / RSS）、J-Quants のリフレッシュトークン

（プロジェクトルートに requirements.txt / pyproject.toml があればそれに従ってください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数 / 設定

KabuSys は環境変数から設定を読み込みます（`kabusys.config.settings` 経由でアクセス）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabu ステーション API のパスワード（必要な場合）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必要な場合）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必要な場合）

任意 / デフォルト可能:
- KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
- LOG_LEVEL   : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を自動読み込みします。OS 環境変数が優先されます。
- 自動ロードを無効化するには: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

簡易の .env.example:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストール
   （プロジェクトが pyproject.toml / requirements.txt を持っている場合はそちらを使用）
   ```
   pip install duckdb defusedxml
   ```

3. 環境変数を設定（`.env` をプロジェクトルートに作成するのが簡単）
   - 必須のトークン等を `.env` に記載

4. DuckDB スキーマ初期化
   Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   これにより必要なテーブルとインデックスが作成されます。

5. （任意）監査ログ専用 DB 初期化
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要な例）

- 設定値にアクセス
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- 日次 ETL を実行
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758"}  # 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2024, 1, 31))
  # records: [{"date":..., "code":..., "mom_1m":..., ...}, ...]
  ```

- IC（Information Coefficient）計算
  ```python
  from kabusys.research import calc_forward_returns, calc_ic

  fwd = calc_forward_returns(conn, target_date=date(2024,1,31))
  factors = [...]  # 事前に計算した factor_records（各要素に "code" とファクター列を持つ）
  ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- Z スコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=["mom_1m", "mom_3m"])
  ```

---

## 主な API / モジュール参照

- kabusys.config
  - settings (Settings オブジェクト)
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を想定）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - etl.py
    - features.py
    - stats.py
    - quality.py
    - calendar_management.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
    (戦略実装用モジュール群)
  - execution/
    - __init__.py
    (発注実装用モジュール群)
  - monitoring/
    - __init__.py
    (監視 / メトリクス用モジュール)

---

## 開発・運用上の留意点

- Python バージョンは 3.10 以上を推奨（`X | Y` 型記法を使用）
- J-Quants API のレート制限（120 req/min）を考慮しクライアントは内部でスロットリングを行います
- RSS 取得は SSRF や XML 攻撃対策（ホスト検証、defusedxml、サイズ制限）を備えています
- ETL 保存は冪等（ON CONFLICT）で設計されていますが、外部からの不整合入力などには quality チェックを実行して検出してください
- 自動 .env ロードはプロジェクトルート判定（.git または pyproject.toml）に基づきます。テスト時などに自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください
- DuckDB のタイムゾーンや Python 側の datetime の扱いに注意してください（監査テーブルは UTC を強制しています）

---

## トラブルシューティング

- DuckDB が見つからない / import error:
  - `pip install duckdb` を実行してください。
- J-Quants の認証エラー（401）:
  - `JQUANTS_REFRESH_TOKEN` が正しいか確認。jquants_client は 401 受信時にトークンを自動リフレッシュしますが、リフレッシュトークン自体が無効だと失敗します。
- RSS 取得でプライベートアドレス接続がブロックされる:
  - セキュリティ上の仕様です。社内サービスに接続したい場合は適切な構成のプロキシ経由などを検討してください。

---

## ライセンス / 貢献

本リポジトリのライセンスや貢献方法はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（ここでは 仮定の README を示しています）。

---

必要であれば、README に含める具体的なコマンド例（cron ジョブの登録例、docker-compose 例、CI ワークフロー）や .env.example の完全版、ユニットテストの実行方法なども追記できます。どの情報を追加しますか？