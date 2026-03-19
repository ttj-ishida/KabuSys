KabuSys
======

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）のリポジトリ用 README。  
このドキュメントはリポジトリ内のソースコードに基づいて作成しています。プロジェクト全体の概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

概要
----
KabuSys は日本株の自動売買に必要な以下の機能群を提供するライブラリ群です。

- データ収集（J-Quants API 経由で株価・財務・カレンダー取得）
- データ保存 / スキーマ（DuckDB）管理
- ETL（差分更新・バックフィル・品質チェック）
- ニュース収集（RSS）と銘柄紐付け
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー）と評価（IC 等）
- 基本的な統計ユーティリティ（Zスコア正規化など）
- 発注・実行・監視を扱うモジュールの骨組み（strategy / execution / monitoring）

設計方針のポイント
- DuckDB を用いたローカルデータベースでデータ層（raw / processed / feature / execution）を保持
- J-Quants API 呼び出しに対するレート制御、リトライ、トークンリフレッシュ対応
- ETL は差分更新かつ冪等（ON CONFLICT）で実装
- Research モジュールは本番口座や発注 API にアクセスしない（解析専用）
- ニュース収集では SSRF や XML Bomb などセキュリティ対策を盛り込む

対応要件
- Python 3.10 以上（型ヒントに | を使用）
- 必要なパッケージ（主要なもの）:
  - duckdb
  - defusedxml
  - （標準ライブラリ以外は上記が主な依存。実行環境に応じて追加してください）

主な機能一覧
--------------
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動ロード（プロジェクトルート判定）
  - 必須環境変数の取得・検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）
  - KABUSYS_ENV（development/paper_trading/live）によるモード判定

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API から日足、財務情報、マーケットカレンダーを取得
  - レート制御、再試行、401 リフレッシュなどを内包
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）

- スキーマ定義（kabusys.data.schema）
  - raw / processed / feature / execution 層のテーブル DDL
  - インデックスと初期化関数 init_schema(db_path) を提供

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(): カレンダー取得 → 株価差分取得 → 財務取得 → 品質チェック
  - 差分更新 / バックフィル / 品質チェックをサポート

- データ品質チェック（kabusys.data.quality）
  - 欠損データ検出、スパイク検出、重複チェック、日付不整合検出
  - QualityIssue オブジェクトで結果を返す（error / warning）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードの取得、記事正規化、ID（SHA-256）生成、DuckDB への保存
  - SSRF 対策、gzip サイズ制限、XML 用保護ライブラリ利用
  - 記事から銘柄コード（4桁）を抽出し news_symbols に紐付け

- リサーチ / ファクター（kabusys.research）
  - calc_momentum / calc_volatility / calc_value 等のファクター計算（DuckDB を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索）
  - zscore_normalize（kabusys.data.stats）を再エクスポート

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など監査用テーブルの定義と初期化
  - init_audit_db(db_path) で専用 DB を初期化

セットアップ手順
--------------
以下はローカル開発 / 実行環境の最小セットアップ手順の例です。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. Python バージョン確認
   - Python >= 3.10 を推奨

4. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

5. 環境変数 (.env) を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - 監査ログを別 DB に分ける場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（主要ユースケース）
------------------------

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）
  ```
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- J-Quants から日足を取得して保存（個別実行）
  ```
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print("saved", saved)
  ```

- ニュース収集ジョブ（RSS からの一括収集）
  ```
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(res)
  ```

- リサーチ（ファクター計算 / IC 評価）
  ```
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  t = date(2024, 1, 31)
  momentum = calc_momentum(conn, t)
  fwd = calc_forward_returns(conn, t, horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC:", ic)
  # Zスコア正規化例
  normed = zscore_normalize(momentum, columns=["mom_1m", "mom_3m"])
  ```

- スキーマ初期化（監査ログを追加）
  ```
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.audit import init_audit_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

よくあるトラブルと注意点
-----------------------
- 環境変数未設定:
  - settings（kabusys.config.Settings）で必須環境変数が未設定の場合、ValueError が発生します。
  - .env を用意するか、OS 環境変数を設定してください。

- Python バージョンが古い:
  - 型注釈に | を使用しているため Python 3.10 以上が必要です。

- DuckDB ファイルの権限 / ディレクトリ:
  - init_schema は親ディレクトリがない場合に自動作成しますが、ファイルシステムの権限に注意してください。

- 自動 .env 読み込み:
  - プロジェクトルートの判定は package ファイルの __file__ を起点に .git または pyproject.toml を探します。配布後や特殊な構成では期待通りに動かない場合があるので、その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し手動で環境変数を管理してください。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は本リポジトリの主要な Python モジュール構成（src/kabusys 以下）です。実際のファイルツリーはリポジトリによりますが、コードベースから抽出した主要要素を示します。

- src/kabusys/
  - __init__.py
  - config.py                     (環境変数 / 設定管理)
  - data/
    - __init__.py
    - jquants_client.py           (J-Quants API クライアント + DuckDB 保存)
    - news_collector.py           (RSS 収集・前処理・保存・銘柄抽出)
    - schema.py                   (DuckDB スキーマ定義 & init_schema)
    - pipeline.py                 (ETL パイプライン: run_daily_etl 等)
    - quality.py                  (データ品質チェック)
    - stats.py                    (統計ユーティリティ: zscore_normalize)
    - features.py                 (zscore_normalize の再エクスポート)
    - calendar_management.py      (マーケットカレンダー管理ユーティリティ)
    - audit.py                    (監査ログテーブルの初期化)
    - etl.py                      (ETLResult の公開)
  - research/
    - __init__.py                 (研究用 API のエクスポート)
    - feature_exploration.py      (将来リターン / IC / summary)
    - factor_research.py          (momentum / volatility / value の計算)
  - strategy/
    - __init__.py                 (戦略層: 未実装の骨組み)
  - execution/
    - __init__.py                 (発注/実行層: 未実装の骨組み)
  - monitoring/
    - __init__.py                 (監視 / モニタリング: 未実装の骨組み)

拡張ポイント（今後の作業想定）
-----------------------------
- strategy / execution / monitoring の具体的実装（発注ロジック、ブローカー API 統合、ポジション管理）
- Slack 通知や運用ダッシュボード連携（環境変数で Slack トークンが定義済）
- CI / テストスイート、requirements.txt の整備
- 追加の品質チェックやメトリクス収集

最後に
------
この README はソースコードの内容に基づいて生成しています。実運用や本格的な開発ではテスト、キーやシークレットの安全な管理、運用監視、リスク管理（発注の二重チェックやサンドボックス運用）を必ず行ってください。その他、README に追加したい情報（例: サンプル .env.example、実行スクリプト例、CI 設定）や、英語版が必要であれば教えてください。