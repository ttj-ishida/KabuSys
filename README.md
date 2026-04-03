# KabuSys — 日本株自動売買基盤（README）

概要
----
KabuSys は日本株のデータ取得・ETL、特徴量/ファクター計算、ニュースに基づくAIスコアリング、監査ログ、マーケットカレンダー管理などを備えた研究・自動売買プラットフォーム向けのライブラリ群です。DuckDB をデータ格納に使い、J-Quants や RSS、OpenAI（LLM）など外部サービスと連携して、バックテスト/リサーチ/実運用の基盤処理を提供します。

主な特徴
--------
- ETL（J-Quants からの株価・財務・カレンダー差分取得）と品質チェック（欠損・スパイク・重複・日付整合性）。
- ニュース収集（RSS）と前処理、安全対策（SSRF 対策、XML の安全パース）。
- OpenAI を使ったニュースセンチメント（銘柄単位）とマクロセンチメントの評価（JSON Mode を想定）。
- マーケットカレンダー管理（JPX カレンダーを差分取得・営業日判定ユーティリティ）。
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と研究用統計ユーティリティ（Zスコア、IC 計算など）。
- 監査ログ用スキーマ（signal → order_request → execution のトレーサビリティ）を DuckDB へ初期化する機能。
- 環境変数 / .env 自動ロード、環境別設定（development / paper_trading / live）。

必須外部サービス / ライブラリ（主要）
- J-Quants API（株価・財務・カレンダー取得）
- OpenAI（gpt-4o-mini を想定）
- DuckDB
- defusedxml（RSS パースの安全化）
- 標準ライブラリ（urllib 等）

セットアップ手順
----------------
1. リポジトリを取得
   - Git からクローンする想定:
     git clone <repo-url>
     cd <repo>

2. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要なパッケージをインストールします。プロジェクトに requirements.txt があればそれを使ってください。
   - 例（最低限）:
     pip install duckdb openai defusedxml

   - 開発インストール:
     pip install -e .

4. 環境変数の設定
   - プロジェクトルート（リポジトリのルート）に .env または .env.local を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化）。
   - 最低限必要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime などで使用）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注や接続で使用する場合）
   - その他（任意やデフォルトがあるもの）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知連携に使用

   - .env のパースは shell 風の書式（export も可）をサポートし、コメントやクォートも考慮します。

5. データベース初期化（監査スキーマなど）
   - 監査ログ用 DB を初期化する例:
     python -c "from kabusys.data.audit import init_audit_db; conn = init_audit_db('data/audit.duckdb')"

使い方（主要なユースケースとコード例）
------------------------------------

基本的な前提
- 多くの関数は duckdb.DuckDBPyConnection を受け取ります。まず接続を作成してください。

例: DuckDB 接続を作る
- import duckdb
- from kabusys.config import settings
- conn = duckdb.connect(str(settings.duckdb_path))

1) 日次ETL（run_daily_etl）
- ETL（カレンダー取得 → 株価差分 → 財務差分 → 品質チェック）を実行する例:
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

2) ニュースセンチメント（銘柄単位）
- OpenAI を使って前日〜当日のニュースを集約し ai_scores へ保存（score_news）:
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n}")

  - api_key 引数で明示的に OpenAI キーを渡すこともできます。
  - OpenAI API キーが未設定の場合は ValueError を送出します。

3) マクロ + ETFベースの市場レジーム判定
- ETF（1321）200日 MA 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ書き込み:
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))

4) 監査スキーマ初期化
- 監査テーブル（signal_events, order_requests, executions）を作成:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # この conn を使って注文トレーサビリティを記録できます

5) 研究用途のファクター計算 / 統計
- モメンタムやボラティリティ、バリューを計算:
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  data = calc_momentum(conn, target_date=date(2026,3,20))

- Zスコア正規化:
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "ma200_dev"])

6) カレンダー関連
- 営業日判定 / 次営業日取得:
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_trading = is_trading_day(conn, date(2026,3,20))
  next_day = next_trading_day(conn, date(2026,3,20))

注意点 / 設計上の留意点
- Look-ahead bias を避ける設計（多くの関数が date を明示的に受け取り、内部で date.today() を参照しない）。
- API 呼び出しはリトライとバックオフ、フェイルセーフ（多くの場面で失敗時は 0 や空リストでフォールバック）を実装。
- DuckDB の executemany の制約に配慮した実装（空 params の扱いに注意）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探して実行されます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants 用（必須）
- OPENAI_API_KEY — OpenAI 用（score_news / score_regime）
- KABU_API_PASSWORD — kabuステーション接続用
- KABUSYS_ENV — environment ("development" / "paper_trading" / "live")
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py  — パッケージエクスポート
- config.py    — 環境変数 / .env 自動ロードと Settings
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM スコアリング（銘柄単位）
  - regime_detector.py — マクロ + ETF による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（取得 & DuckDB への保存）
  - pipeline.py        — ETL 実装（run_daily_etl 等）
  - etl.py             — ETL の公開型 (ETLResult)
  - quality.py         — データ品質チェック
  - stats.py           — 共通統計ユーティリティ（zscore_normalize）
  - news_collector.py  — RSS ニュース収集と前処理（SSRF/サイズ制限対策）
  - calendar_management.py — マーケットカレンダー管理（営業日判定等）
  - audit.py           — 監査ログスキーマの初期化
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ等
- (strategy/, execution/, monitoring/ 等はパッケージ公開対象として想定されていますが、実装はこのコードベースの他の部分に依存します)

ドキュメント / 設計メモ
---------------------
- 各モジュールの冒頭には設計方針・処理フロー・フェイルセーフの振る舞いが詳細に記載されています。実装を変更する際はこれらの方針に従ってください。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を前提にしており、応答のバリデーションを厳密に行います。
- J-Quants クライアントはレート制限（120 req/min）や 401 のトークン自動リフレッシュ、ページネーション対策を実装済みです。

貢献 / テスト
--------------
- テストでは .env の自動ロードを抑止するために環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- OpenAI や HTTP 周りはモックしやすいように内部呼び出し関数が分離されています（ユニットテストで差し替え可能）。

ライセンス / その他
-------------------
- この README ではライセンス情報は含めていません。実際の配布リポジトリでは LICENSE ファイルを確認してください。

以上が KabuSys の概要・セットアップ・基本的な使い方です。必要であれば、各モジュール別の詳細な使用例（API 引数の詳細、返り値のサンプル）やユースケース別のワークフロー（ETL スケジュール例、監視・再起動フロー、発注フローのサンプル）を追加で作成しますのでお知らせください。