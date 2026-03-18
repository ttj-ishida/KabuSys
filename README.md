# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）用コードベースの README。  
本ドキュメントではプロジェクト概要、主要機能、セットアップ・利用方法、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL・特徴量生成・リサーチ・発注管理・監査を想定したコンポーネント群を提供するライブラリです。  
主に以下を目的としています。

- J-Quants API からの株価・財務・市場カレンダーの取得と DuckDB への冪等保存
- RSS ベースのニュース収集と記事→銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター（モメンタム・ボラティリティ・バリュー等）計算および IC/サマリー算出
- ETL の日次パイプライン、監査ログ（発注トレース）のスキーマ
- 発注ロジック周りのスケルトン（execution / strategy / monitoring ディレクトリ下）

設計上のポイント：
- DuckDB を永続 DB として利用（:memory: でも可）
- 外部依存は最小化（標準ライブラリ中心）、ただし DuckDB / defusedxml は利用
- API レート制御・リトライ・トークン自動更新等を備えた J-Quants クライアント
- ニュース収集は SSRF / XML Bomb / 大量レスポンス対策を実装

---

## 機能一覧

主な機能（モジュール別抜粋）

- kabusys.config
  - .env 自動ロード（プロジェクトルートの .env / .env.local）
  - 必須環境変数チェック（settings オブジェクト経由）
  - KABUSYS_ENV / LOG_LEVEL 等の検証

- kabusys.data.jquants_client
  - J-Quants API へのリクエスト（レートリミット、リトライ、401 トークンリフレッシュ対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）

- kabusys.data.news_collector
  - RSS フィード取得（SSRF・リダイレクト検査、gzip 対応、サイズ上限）
  - 記事正規化（URL 除去、空白正規化）、記事 ID は正規化 URL の SHA-256（先頭32文字）
  - raw_news 保存（チャンク・トランザクション・ON CONFLICT DO NOTHING）
  - 銘柄コード抽出と news_symbols への紐付け

- kabusys.data.schema / audit
  - DuckDB スキーマの初期化（raw / processed / feature / execution / audit）
  - 監査用テーブル（signal_events / order_requests / executions 等）初期化

- kabusys.data.pipeline / etl
  - 差分更新を考慮した日次 ETL（run_daily_etl）
  - prices / financials / calendar の個別 ETL 関数
  - 品質チェック（quality.run_all_checks）との連携

- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合チェック
  - QualityIssue の集約・ログ出力

- kabusys.research
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats から）

その他:
- 発注/モニタリング/戦略層の雛形（execution/, strategy/, monitoring/）

---

## セットアップ手順

前提:
- Python 3.9+（型注釈等を利用）
- Git が使用可能

基本手順（開発環境向け）:

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール  
   このコードベースで明示的に使用している主要パッケージ:
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに pyproject.toml / requirements.txt があれば `pip install -e .` や `pip install -r requirements.txt` を利用してください）

4. 環境変数（.env）を用意  
   プロジェクトルート（.git / pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   最低限設定が必要な環境変数（settings から）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）

   任意 / デフォルトあり:
   - KABU_API_BASE_URL : デフォルト "http://localhost:18080/kabusapi"
   - DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
   - SQLITE_PATH : デフォルト "data/monitoring.db"
   - KABUSYS_ENV : "development" | "paper_trading" | "live"（デフォルト development）
   - LOG_LEVEL : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト INFO）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. DB スキーマ初期化（DuckDB）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   監査ログ専用 DB を初期化する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的なサンプル）

以下は主要な操作の簡単なサンプル。

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すと本文から4桁銘柄コードを抽出して紐付ける
  saved = run_news_collection(conn, known_codes={"7203","6758"})
  print(saved)
  ```

- J-Quants から株価を直接取得して保存する（テストや手動実行向け）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f"fetched={len(records)} saved={saved}")
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target)
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack Bot トークン（通知等に使用）
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: runtime 環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, …）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動ロードを無効化

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- execution/            (発注関連の実装・インターフェース)
- strategy/             (戦略ロジックの配置先)
- monitoring/           (監視・メトリクス)
- data/
  - __init__.py
  - jquants_client.py   (J-Quants API クライアント)
  - news_collector.py   (RSS ニュース収集)
  - schema.py           (DuckDB スキーマ定義 & init_schema)
  - pipeline.py         (ETL パイプライン: run_daily_etl 等)
  - etl.py              (ETL 公開 API)
  - quality.py          (データ品質チェック)
  - features.py         (特徴量ユーティリティの公開)
  - stats.py            (zscore_normalize 等)
  - calendar_management.py (マーケットカレンダー管理)
  - audit.py            (監査ログスキーマ & 初期化)
- research/
  - __init__.py
  - feature_exploration.py  (forward returns, IC, summary)
  - factor_research.py      (momentum/volatility/value 等)
- その他: strategy/, execution/, monitoring/ は実装や拡張ポイント

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリは取引ロジックを含むため、実稼働（live）環境では十分なテストと安全策（サンドボックス、paper_trading）を行ってください。
- J-Quants の API レート制限や取得失敗に備え、ETL は idempotent（ON CONFLICT）かつリトライ実装を活用していますが、運用ルールを設けてください。
- .env ファイルは秘密情報を含むため、リポジトリにコミットしないでください。
- DuckDB のバックアップ・スナップショット運用を推奨します（特に audit / execution データ）。

---

もし README に追加したい内容（例えばサンプル構成ファイル .env.example、CI/CD、テスト実行方法、パッケージ化手順など）があれば教えてください。必要に応じて追記します。