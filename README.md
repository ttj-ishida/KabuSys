KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリの内部モジュール群です。本リポジトリは以下のレイヤーを持つデータ取得・前処理・特徴量・監査・ETL 機能を提供します。  
（この README はソースコードを元に手作業で作成しています）

概要
----

KabuSys は日本株のデータ収集・品質管理・特徴量生成・監査ログ・ETL を行うためのモジュール群です。主に以下を目的としています。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS からニュースを収集して正規化・DB保存、銘柄コード抽出
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 戦略向けファクター（モメンタム、ボラティリティ、バリュー等）計算と正規化ユーティリティ
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマと初期化
- 設定管理（.env 自動ロード、環境別フラグ、必須 env チェック）

主な機能一覧
------------

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェックと便利プロパティ（env, log_level, is_live 等）

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API の認証（refresh token → id token）
  - デイリープライス、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン（kabusys.data.pipeline）
  - 市場カレンダー / 株価 / 財務データの差分取得（バックフィル含む）
  - run_daily_etl による一括 ETL と品質チェック実行

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue オブジェクトで報告

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策、gzip 制限、XML 脆弱性対策）
  - 記事正規化、ID 生成（normalized URL の SHA-256 前半）、DuckDB 保存
  - 記事と銘柄コードの紐付け（extract_stock_codes）

- スキーマ管理（kabusys.data.schema / audit）
  - DuckDB の Raw / Processed / Feature / Execution / Audit 用テーブル定義と初期化
  - init_schema / init_audit_schema / init_audit_db

- 研究用ファクター計算（kabusys.research）
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（kabusys.data.stats 経由）

セットアップ手順
----------------

前提
- Python 3.9+（ソースは型注釈に沿って記載）
- DuckDB（Python パッケージ duckdb）
- defusedxml（RSS パースの安全化）
- ネットワークアクセス（J-Quants API / RSS）

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要パッケージ例:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを使用）

3. このパッケージを開発モードで使う（任意）
   - pip install -e .

環境変数（.env）準備
- プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 主要な環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN：J-Quants の refresh token（必須）
  - KABU_API_PASSWORD：kabu ステーション API パスワード（必須）
  - SLACK_BOT_TOKEN：Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID：Slack チャンネル ID（必須）
- その他（任意/デフォルト有り）:
  - KABUSYS_ENV：development / paper_trading / live（デフォルト development）
  - LOG_LEVEL：DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - KABUS_API_BASE_URL（kabu ステーション API のベース URL、デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視用 DB、デフォルト data/monitoring.db）

例 .env（サンプル）
- .env.example を参考にしてください（リポジトリにある場合）。簡単な例:
  JQUANTS_REFRESH_TOKEN=xxxx
  KABU_API_PASSWORD=yyyy
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development

初期化（DuckDB スキーマ）
- DuckDB ファイルを初期化してスキーマを作成する例:

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 監査ログ専用 DB を作る場合:

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（代表的な操作例）
-----------------------

- 日次 ETL を実行してデータを収集（簡易例）

  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集ジョブの実行

  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄コードの集合（文字列の4桁コード）
  res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(res)

- ファクター計算（研究用途）

  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2025, 1, 31)
  mom = calc_momentum(conn, d)
  vol = calc_volatility(conn, d)
  val = calc_value(conn, d)
  # 正規化例
  mom_norm = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

- J-Quants 生データ取得・保存（低レベル）

  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect("data/kabusys.duckdb")
  records = fetch_daily_quotes()  # settings.jquants_refresh_token を使って自動認証
  saved = save_daily_quotes(conn, records)

- カレンダー管理・ユーティリティ

  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  is_trade = is_trading_day(conn, date(2025,1,1))
  nxt = next_trading_day(conn, date(2025,1,1))

注意点 / 実運用に関するメモ
--------------------------

- J-Quants API のレート制限（120 req/min）をモジュールが内部で尊重します。大量のページング取得時は時間がかかる場合があります。
- jquants_client は 401 受信時に自動でトークンリフレッシュを行い 1 回だけリトライします。
- DuckDB への保存は冪等性を考慮しており、ON CONFLICT で更新する設計です。
- news_collector は SSRF 対策や XML 爆弾対策（defusedxml）を組み込んでいます。また取得サイズ制限が入っています。
- 環境は KABUSYS_ENV により挙動（例えば発注機能の有効/無効など）を分ける想定です（development / paper_trading / live）。

ディレクトリ構成
----------------

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py          -- J-Quants API クライアント（取得・保存）
  - news_collector.py         -- RSS ニュース収集・保存
  - schema.py                 -- DuckDB スキーマ定義・初期化
  - stats.py                  -- 統計ユーティリティ（zscore_normalize 等）
  - pipeline.py               -- ETL パイプライン（run_daily_etl など）
  - features.py               -- 特徴量公開インターフェース（再エクスポート）
  - calendar_management.py    -- カレンダー管理ユーティリティ
  - audit.py                  -- 監査ログスキーマ・初期化
  - etl.py                    -- ETL 公開 API（ETLResult 再エクスポート）
  - quality.py                -- データ品質チェック
- research/
  - __init__.py               -- 研究用 API を再エクスポート
  - feature_exploration.py    -- 将来リターン計算・IC・統計サマリ
  - factor_research.py        -- momentum/volatility/value 計算
- strategy/
  - __init__.py               -- 戦略層（未実装のエントリポイント）
- execution/
  - __init__.py               -- 発注/実行層（未実装のエントリポイント）
- monitoring/
  - __init__.py               -- 監視関連（未実装のエントリポイント）

開発・貢献
----------

- コードは各モジュールごとに単体テストを用意して検証することを推奨します（テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env 自動読み込みを無効化できます）。
- ETL や DB 初期化は破壊的ではない設計（冪等）ですが、運用データに対してはバックアップを取ってから操作してください。

その他
-----

- 本 README はソースの docstring / コメントを元にまとめた概要ドキュメントです。より詳しい仕様（DataPlatform.md / StrategyModel.md 等）は別途参照してください（リポジトリに同梱されている想定の設計文書）。
- 実際の「発注」や「本番接続（kabu ステーション）」を行う場合は、KABUSYS_ENV を適切に設定し、十分な検証を行ってください（paper_trading での検証を推奨）。

質問や追記してほしい項目があれば教えてください。README を用途（導入ガイド／API リファレンス／運用手順）に合わせて拡張できます。