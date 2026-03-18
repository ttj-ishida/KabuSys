# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
J-Quants からの市場データ取得、DuckDB を使ったデータスキーマ・ETL、ニュース収集、ファクター計算（リサーチ向け）や発注監査用スキーマなど、運用に必要な主要機能をモジュール化して提供します。

---

## 概要

KabuSys は以下の責務を持つ Python パッケージ群です。

- J-Quants API からの株価・財務・カレンダー取得（ページネーション・レート制御・トークン自動リフレッシュ対応）
- DuckDB を用いたデータスキーマ定義と冪等（idempotent）な保存処理
- ETL（差分更新、バックフィル、品質チェック）の自動化
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策・サイズ制限・トラッキング除去）
- リサーチ用ファクター（モメンタム・ボラティリティ・バリュー等）の計算と評価ユーティリティ（IC / Z-score）
- 監査用テーブル群（シグナル→発注→約定のトレーサビリティ）

設計上、本パッケージの多くのモジュールは「DuckDB 接続」を受け取り、外部の発注 API（kabuステーション等）や本番口座へは自動的にはアクセスしません。

---

## 主な機能一覧

- data/
  - schema.init_schema / get_connection: DuckDB スキーマ作成と接続
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - pipeline.run_daily_etl: 日次 ETL（カレンダー・株価・財務・品質チェック）
  - news_collector.run_news_collection: RSS フィードからの記事取得・前処理・DB 保存・銘柄紐付け
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 発注・約定の監査スキーマ初期化ユーティリティ
  - stats / features: Zスコア正規化等の統計ユーティリティ
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value 等
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config: .env 自動読み込み、環境設定ラッパ（必須環境変数の取得）
- execution / strategy / monitoring: パッケージ領域（発注や戦略・監視ロジックの拡張向け）

---

## 要求・前提

- Python 3.10+
  - ソース内で `|` を使った型注釈（Union）を用いているため。
- 必要な外部パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード取得等）

依存はプロジェクトの配布方法により異なります。簡易的に試す場合は最低限 `duckdb` と `defusedxml` をインストールしてください。

例:
pip install duckdb defusedxml

---

## 環境設定 (.env)

プロジェクトは .env/.env.local または OS 環境変数から設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（Settings から参照されるもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API のパスワード（発注系を使用する場合）
- SLACK_BOT_TOKEN        : Slack 通知を行う場合の Bot トークン
- SLACK_CHANNEL_ID       : Slack のチャンネル ID

その他の設定（任意、デフォルトあり）
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化
- DUCKDB_PATH / SQLITE_PATH — データベースのパス（デフォルト: data/kabusys.duckdb, data/monitoring.db）

.env の読み込みルールは POSIX 系の `.env` 形式に準拠し、コメントやクォート、export 形式に対応します。

---

## セットアップ手順（ローカル検証向け）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - その他、プロジェクトが要求するパッケージがあれば適宜追加
4. .env を作成（必須環境変数を設定）
   - 例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_password
5. DuckDB スキーマを初期化
   - Python REPL / スクリプトから実行（下の「使い方」参照）

---

## 使い方（簡単なコード例）

- DuckDB スキーマ初期化

  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

  - ":memory:" を渡すとインメモリ DB になります。

- 日次 ETL を実行（J-Quants から市場データを差分取得し保存）

  from kabusys.data import pipeline
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

  - 引数で target_date / id_token / run_quality_checks / backfill_days 等を指定できます。
  - 実行結果は ETLResult オブジェクト（取得件数や品質チェック結果を含む）です。

- ニュース収集ジョブ（RSS → raw_news）

  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 銘柄候補セット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数, ...}

- リサーチ用ファクター計算

  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize

  target = date(2024, 1, 31)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

  # 例: ファクターと将来リターンの IC を計算
  # factor_records のカラム名に合わせて指定してください（例: "mom_1m" / "fwd_1d"）
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

- 設定値の参照

  from kabusys.config import settings
  token = settings.jquants_refresh_token

  - 必須 env が欠けていると settings プロパティで ValueError を送出します。

- 監査ログ用スキーマ初期化（audit 専用 DB）

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## よくある操作と注意点

- 自動 .env ロードの挙動
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。
  - テスト等で自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- J-Quants API のレート制御
  - jquants_client は 120 req/min を目安に固定間隔のスロットリングを実装しています。
  - 429/408/5xx 系はリトライ（指数バックオフ）対象、401 はトークン刷新を試みます。

- DuckDB スキーマの冪等性
  - save_* 系関数は ON CONFLICT を用いて冪等に保存します。ETL を繰り返し実行しても重複は起きにくい設計です。

- NewsCollector のセキュリティ対策
  - RSS フィードはスキーム検査 (http/https)・プライベートアドレス（SSRF）検査・最大受信サイズ制限・gzip 解凍後のサイズチェック等を行います。

- デバッグ／ログ
  - settings.log_level を設定することでログレベルを調整できます。
  - エラーはモジュール内部でログ出力され、ETL 等は例外捕捉して partial な失敗を報告するスタイルです。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- execution/__init__.py
- strategy/__init__.py
- monitoring/__init__.py
- research/
  - __init__.py
  - feature_exploration.py
  - factor_research.py
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
  - etl.py
  - quality.py

（上記はリポジトリの主要モジュール一覧です。実際のプロジェクトにはテスト・CI 設定・ドキュメント等が含まれる場合があります。）

---

## 今後の拡張点（参考）

- Strategy / Execution 層の具象実装（ポートフォリオ最適化、リスク管理ルール、注文送信ロジック）
- Slack 等への通知機能の実装（settings の Slack トークンを利用）
- モデル管理・AI スコアリングパイプラインの追加
- モニタリングダッシュボード（監査ログ／パフォーマンス可視化）

---

質問や追加したいサンプル（例えば CLI スクリプト、Docker 化、CI ワークフローなど）があれば教えてください。README の目的や対象を指定いただければ、より運用向けの手順・例を追加します。