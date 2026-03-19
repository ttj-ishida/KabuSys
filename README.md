KabuSys
=======

日本株向けの自動売買プラットフォーム用ライブラリ群（モジュール群）。  
データ取得（J-Quants）、DuckDB スキーマ定義・ETL、ニュース収集、ファクター計算、研究用ユーティリティ、監査ログなどを含むコンポーネントを提供します。

要点
- Python パッケージとして内部モジュール群を提供（src/kabusys 配下）。
- DuckDB を中心にデータを永続化（raw / processed / feature / execution / audit 層）。
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新対応）。
- RSS ニュース収集、正規化、銘柄抽出、DuckDB への冪等保存。
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と IC/統計サマリ。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。

主な機能
- データ取得 / 保存
  - J-Quants から日次株価・財務・市場カレンダーを取得（data/jquants_client.py）。
  - DuckDB へ冪等に保存（ON CONFLICT DO UPDATE を使用）。
- ETL パイプライン
  - 差分更新、バックフィル、品質チェックを含む日次 ETL（data/pipeline.py）。
- スキーマ管理
  - DuckDB のスキーマ定義と初期化（data/schema.py）。
  - 監査ログ（signal_events / order_requests / executions）初期化（data/audit.py）。
- ニュース収集
  - RSS フィード取得、XML の安全パース、URL 正規化、記事ID生成、銘柄抽出、DB 保存（data/news_collector.py）。
- 研究支援
  - ファクター算出（momentum, volatility, value）（research/factor_research.py）。
  - 将来リターン計算、IC 計算、統計サマリ（research/feature_exploration.py）。
  - 統計ユーティリティ（zscore_normalize）（data/stats.py）。
- データ品質
  - 欠損、スパイク、重複、日付不整合のチェック（data/quality.py）。

動作要件
- Python 3.10 以上
- 依存ライブラリ（最低限）:
  - duckdb
  - defusedxml
（コードは標準ライブラリの urllib を利用しており、requests は必須ではありません）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン / 配置
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) または .venv\Scripts\activate (Windows)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （将来的に requirements.txt を追加する想定）
4. 環境変数を設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（kabusys.config が .env/.env.local を読み込み）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

推奨する .env（例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

使い方（主要な操作例）
- DuckDB スキーマを初期化する
  - Python スニペット例:
    from kabusys.data.schema import init_schema
    init_schema("data/kabusys.duckdb")
  - これにより必要なテーブルとインデックスが作成されます。

- 日次 ETL を実行する（J-Quants からデータ取得して保存 → 品質チェック）
  - 例:
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)
    print(result.to_dict())
  - run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順で処理します。設定や ID トークンは環境変数から読み込みます。

- ニュース収集ジョブを実行する
  - 例:
    from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection
    conn = init_schema("data/kabusys.duckdb")
    known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)
  - RSS のソースはデフォルトで Yahoo Finance のビジネス RSS 等を使用します。sources 引数で差し替え可能。

- 研究用ファクターを計算する
  - 例:
    from kabusys.data.schema import get_connection
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
    conn = get_connection("data/kabusys.duckdb")
    d = date(2024, 1, 31)
    mom = calc_momentum(conn, d)
    vol = calc_volatility(conn, d)
    val = calc_value(conn, d)
    fwd = calc_forward_returns(conn, d)
    ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
    print(ic)

- 統計正規化（Z スコア）
  - from kabusys.data.stats import zscore_normalize
  - normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])

設定に関する注意
- 環境変数は .env / .env.local / OS 環境変数から読み込まれます（優先度: OS 環境 > .env.local > .env）。
- 自動読み込みを防ぐには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト時に便利）。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかで、モード判定に使われます（is_live 等のプロパティあり）。
- LOG_LEVEL は "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL" のいずれか。

主要モジュールと説明（抜粋）
- kabusys.config
  - 環境変数読み込み・管理。Settings クラスで必要なキーをプロパティとして提供。
- kabusys.data.jquants_client
  - J-Quants API クライアント（取得・保存機能、レート制御、リトライ、token refresh）。
- kabusys.data.schema
  - DuckDB の DDL と初期化。init_schema() で接続を返す。
- kabusys.data.pipeline / etl
  - 差分 ETL と日次 ETL のエントリポイント（run_daily_etl）。
- kabusys.data.news_collector
  - RSS 収集、記事正規化、DuckDB への保存、銘柄抽出。
- kabusys.data.quality
  - 品質チェック（欠損・スパイク・重複・日付不整合）。
- kabusys.research.*
  - ファクター計算（momentum / volatility / value）、将来リターン、IC、統計サマリ。
- kabusys.data.audit
  - 発注・約定フローの監査ログスキーマと初期化機能。

ディレクトリ構成（抜粋）
- src/kabusys/
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
    - etl.py
    - quality.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

運用上の注意
- J-Quants のレート上限（120 req/min）と API の性質を尊重すること（jquants_client にレート制御済み）。
- ETL は外部 API 依存のため、運用時は credential（refresh token）を安全に管理してください。
- DuckDB に書き込むデータは冪等化処理（ON CONFLICT）を行っていますが、バックアップ運用を検討してください。
- RSS パースでは defusedxml を使用して XML 攻撃を緩和しています。さらにネットワークの SSRF 対策（ホスト検証）を実装済みです。

貢献 / 開発者向け
- コードを拡張する際は既存の設計方針（冪等性、Look-ahead bias 回避、テスト容易性）に注意してください。
- テストを追加する場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env の影響を排除できます。
- DuckDB をインメモリで起動して単体テストを行うことが可能（":memory:" を DB パスに使用）。

ライセンス / その他
- このドキュメントはコードベースに基づいた簡易 README です。実運用に投入する前にセキュリティ・例外処理・監査要件を確認してください。

---  
不明点や README に追記したい具体的な手順（例: CI/CD での ETL 実行、Slack 通知の設定、kabuステーション連携方法など）があれば教えてください。必要に応じて実例コードや運用手順を追加します。