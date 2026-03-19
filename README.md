# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）  
このリポジトリは、データ取得・ETL、データ品質チェック、ファクター計算、ニュース収集、監査ログ等を含む日本株自動売買用の基盤機能群を提供します。KabuSys は内部的に DuckDB をデータレイヤーに利用し、J-Quants API から市場データ・財務データ・マーケットカレンダーを取得します。

---

## 主要機能（概要）

- 環境設定管理
  - `.env` / 環境変数から設定を自動ロード（プロジェクトルート検出）
  - 必須環境変数の明示的取得とバリデーション

- データ取得・保存（Data layer）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - 株価（日足）・財務データ・マーケットカレンダーの取得・DuckDB への冪等保存
  - RSS ベースのニュース収集（前処理・SSRF対策・トラッキング除去・銘柄抽出・DuckDB 保存）

- ETL パイプライン
  - 差分更新、バックフィル、カレンダー先読み、品質チェックを含む日次 ETL 実行
  - ETL 結果の構造化（ETLResult）

- データ品質チェック
  - 欠損データ・重複・スパイク（急騰・急落）・日付不整合の検出
  - 問題を QualityIssue として収集し呼び出し元が判定を行える設計

- スキーマ管理（DuckDB）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - 監査ログ（signal / order_request / execution 等）のための別途初期化 API

- 研究・特徴量計算（Research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman ランク相関）計算、統計サマリー
  - 特徴量の Z スコア正規化ユーティリティ

- その他
  - ニュースと銘柄コードの紐付け（テキストから4桁銘柄コードを抽出）
  - カレンダー管理（営業日判定、次/前営業日の取得）
  - 監査ログ初期化（UTC に固定）

---

## 必要条件

- Python 3.9+（型アノテーションで | を使用するため）
- 主な依存ライブラリ（例）
  - duckdb
  - defusedxml

（パッケージ化時に requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化する
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb defusedxml
   # 開発用には lint / test 等のツールを追加
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（パッケージが import された際に自動ロード）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

   例 `.env`（実際のトークンは秘匿してください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマの初期化
   以下のようにして初期スキーマを作成します（`DUCKDB_PATH` を使うかパスを直接指定）。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主要な例）

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # 初期化済みの DB に接続（既に init_schema を実行済みであれば get_connection で可）
  conn = init_schema("data/kabusys.duckdb")

  # 今日の ETL を実行
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足を取得して保存（低レベル呼び出し）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- ニュース収集ジョブの実行（RSS から収集して保存・銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄リスト（例: {'7203','6758', ...}）
  results = run_news_collection(conn, known_codes={'7203','6758'})
  print(results)
  ```

- 研究用ファクター計算（例: モメンタム／IC）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  target = date(2025, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # 例: mom に対する翌日リターンの IC
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  ```

- Z-score 正規化（features / research で共通利用）
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records=mom, columns=["mom_1m", "mom_3m", "ma200_dev"])
  ```

---

## 環境変数（主要なキー）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション用 API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot Token（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

設定は .env/.env.local から自動的にロードされます。OS 環境変数 > .env.local > .env の優先度です。

---

## ディレクトリ構成

（プロジェクトルート内の src/kabusys を基準とする主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント（取得 & 保存）
    - news_collector.py           -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                   -- DuckDB スキーマ定義・初期化
    - stats.py                    -- 統計ユーティリティ（zscore 正規化等）
    - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
    - features.py                 -- 特徴量ユーティリティ（再エクスポート）
    - calendar_management.py      -- マーケットカレンダー管理（営業日判定等）
    - audit.py                    -- 監査ログスキーマ（signal/events/order/execution）
    - etl.py                      -- ETL 辞書型公開（ETLResult の再エクスポート）
    - quality.py                  -- データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py      -- 将来リターン計算 / IC / summary 等
    - factor_research.py          -- momentum/volatility/value ファクター計算
  - strategy/
    - __init__.py                 -- 戦略関連エントリポイント（将来拡張）
  - execution/
    - __init__.py                 -- 発注 / broker 抽象（将来拡張）
  - monitoring/
    - __init__.py                 -- 監視・メトリクス（将来拡張）

---

## 開発時の注意点 / 追加情報

- DuckDB とのトランザクション管理:
  - スキーマ初期化やバルク挿入はトランザクションを利用しますが、関数によっては明示的な BEGIN/COMMIT を行っています。既存トランザクション中でスキーマ初期化を呼ぶと注意が必要です（ドキュメント内に注釈あり）。

- セキュリティ / ネットワーク:
  - news_collector は SSRF 対策（リダイレクト先のスキームと内部アドレスチェック）、XML パースの安全化（defusedxml）、受信サイズ制限などを実装しています。

- J-Quants API:
  - レート制限（120 req/min）を守るための RateLimiter、401 応答時の自動トークンリフレッシュ、指数バックオフのリトライロジックを実装しています。

- テスト:
  - ネットワーク I/O を伴うモジュール（_jquants_client、news_collector、calendar_update_job 等）は単体テスト時に外部呼び出しをモックしてください。news_collector の _urlopen 等は差し替え可能な設計です。

---

この README はコードベースから抽出した主要機能・API と使い方の簡易ガイドです。詳細な仕様（DataPlatform.md / StrategyModel.md 等）はリポジトリの設計ドキュメントに従ってください。必要であれば README にさらに具体的な CLI 使用例や CI/CD の設定例、テスト手順を追加できます。