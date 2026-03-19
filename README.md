KabuSys
=======

日本株向けの自動売買／データ基盤ライブラリ集（KabuSys）のREADMEです。  
本プロジェクトは、J-Quants 等の外部データ取得、DuckDB によるデータ管理、特徴量計算・研究、ニュース収集、ETL パイプライン、監査ログなどを含むモジュール群を提供します。

主な目的
- 日本株データの取得・保管（J-Quants）
- データ品質チェックと差分ETL
- ニュース収集と記事→銘柄紐付け
- ファクター／特徴量の計算（研究用ユーティリティ）
- 発注／監査用スキーマの定義（監査ログの初期化）

動作要件
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
（実際のインストールはプロジェクトの pyproject.toml / requirements に従ってください）

機能一覧
- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、環境変数優先）
  - 必須環境変数の取得ラッパー（settings）
- データ取得 / 保存（J-Quants クライアント）
  - 日足（OHLCV）、四半期財務、マーケットカレンダー取得（ページネーション対応）
  - レート制限、リトライ、トークン自動リフレッシュ
  - DuckDB に対する冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分取得（最終取得日ベース）、バックフィル、品質チェックを含む日次 ETL
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合等を検出するチェック群
- ニュース収集
  - RSS からの取得、HTML 解凍・前処理、トラッキングパラメータ除去、SSRF 対策
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成、raw_news に冪等保存
  - 銘柄コード抽出（4桁）と news_symbols への紐付け
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - z-score 正規化ユーティリティ
- スキーマ初期化（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化関数
  - 監査ログ専用スキーマの初期化ユーティリティ

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - またはプロジェクトルートで:
     - pip install -e .
     （pyproject.toml や requirements.txt があればそれに従ってください）
4. 環境変数（必須）
   - 次の環境変数は少なくともアプリケーションの一部機能で必須です（settings 参照）。
     - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD（kabuステーション API パスワード）
     - SLACK_BOT_TOKEN（Slack 通知用トークン）
     - SLACK_CHANNEL_ID（Slack チャンネル ID）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL — デフォルト INFO
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db
   - .env 自動読み込み:
     - プロジェクトルート（.git または pyproject.toml を起点）にある .env を自動で読み込みます。
     - 読み込み優先度: OS 環境変数 > .env.local > .env
     - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     - from kabusys.data import schema
     - conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
   - 監査ログ用 DB 初期化:
     - from kabusys.data import audit
     - audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

基本的な使い方（例）
- 日次 ETL を実行する（Python スクリプト例）
  - example_etl.py:
    - from datetime import date
      import duckdb
      from kabusys.data import schema, pipeline
      conn = schema.init_schema("data/kabusys.duckdb")
      result = pipeline.run_daily_etl(conn, target_date=date.today())
      print(result.to_dict())
- ニュース収集ジョブを実行する
  - from kabusys.data import news_collector, schema
    conn = schema.get_connection("data/kabusys.duckdb")
    # 既存の有効銘柄セット known_codes を用意しておくと銘柄紐付けが行われます
    res = news_collector.run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
    print(res)
- J-Quants から日足を取得して保存する（低レベル）
  - from kabusys.data import jquants_client as jq
    recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
    saved_count = jq.save_daily_quotes(conn, recs)
- 研究用ファクター計算（例）
  - from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
    conn = schema.get_connection("data/kabusys.duckdb")
    momentum = calc_momentum(conn, target_date=date(2024,1,31))
    forward = calc_forward_returns(conn, target_date=date(2024,1,31))
    ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
    znormed = zscore_normalize(momentum, ["mom_1m", "ma200_dev"])

環境変数（.env の例）
- .env.example（プロジェクトに合わせて作成）
  - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  - KABU_API_PASSWORD=your_kabu_api_password
  - SLACK_BOT_TOKEN=xoxb-...
  - SLACK_CHANNEL_ID=C01234567
  - KABUSYS_ENV=development
  - LOG_LEVEL=INFO
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db

自動ロード動作の詳細
- config.py はプロジェクトルート（.git または pyproject.toml を見つける）を探し、
  .env と .env.local を自動読み込みします（OS 環境変数が優先）。
- .env.local は .env を上書きできます（override=True）。
- テスト等で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - news_collector.py           — RSS ニュース収集と保存
    - schema.py                   — DuckDB スキーマ定義・init_schema
    - stats.py                    — z-score 等統計ユーティリティ
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - features.py                 — 特徴量ユーティリティ公開インターフェース
    - calendar_management.py      — マーケットカレンダー管理
    - audit.py                    — 監査ログスキーマ・初期化
    - etl.py                      — ETLResult の再エクスポート
    - quality.py                  — データ品質チェック群
  - research/
    - __init__.py                 — 研究用関数の再エクスポート
    - feature_exploration.py      — 将来リターン / IC / summary
    - factor_research.py          — Momentum/Volatility/Value 等
  - strategy/                      — 戦略層（パッケージ）
  - execution/                     — 発注・実行関連（パッケージ）
  - monitoring/                    — 監視関連（パッケージ）

設計上の注意点 / 運用メモ
- DuckDB の初期化は必ず init_schema() で行ってください（DDL を作成）。
- J-Quants API はレート制限があるため、jquants_client は固定間隔スロットリングとリトライを実装済みです。
- ニュース収集は外部ネットワークを扱うため、SSRF 対策やサイズ制限を実装しています。
- 本コードベースは研究（Research）と運用（Execution）を分離する方針です。研究モジュールは DB の prices_daily / raw_financials のみを参照し、発注 API にはアクセスしません。
- KABUSYS_ENV によって実行環境（development / paper_trading / live）を区別できます。live 環境では発注などの操作に注意してください。

貢献 / 拡張
- 新しいデータソースやフィードの追加、品質チェックの拡張、特徴量の追加は対応しやすいモジュール構造です。
- DuckDB スキーマを変更する場合は schema.py に DDL を追加してください（互換性に注意）。

ライセンス
- プロジェクトの LICENSE ファイルに従ってください（ここでは明記していません）。

問い合わせ
- 実運用や導入に関する質問、API キー管理、監査要件などがあれば開発チームにお問い合わせください。

以上が本プロジェクトの概要・セットアップ・使い方の要点です。実際の導入時は pyproject.toml（または requirements.txt）やプロジェクトのドキュメント（DataPlatform.md / StrategyModel.md 等）を併せて参照してください。