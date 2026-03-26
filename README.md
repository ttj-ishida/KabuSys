KabuSys — 日本株データプラットング & 自動売買補助ライブラリ
===============================================================================

概要
----
KabuSys は日本株向けのデータ ETL、ニュース NLP、ファクター研究、マーケットレジーム判定、監査ログ等のユーティリティ群をまとめた Python パッケージです。  
DuckDB をデータ格納に利用し、J-Quants API・RSS ニュース・OpenAI（gpt-4o-mini）等と連携して、日次 ETL、ニュースセンチメント評価、ファクタ計算、監査ログ初期化などの処理を提供します。

主な特徴（機能一覧）
------------------
- データ ETL
  - J-Quants API から株価（日足）・財務データ・JPX カレンダーを差分取得して DuckDB に保存
  - 差分取得・バックフィル・ページネーション対応・リトライ/レート制御を実装
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合などの品質チェックを実行
- ニュース収集 / NLP
  - RSS フィードの安全な取得（SSRF対策、最大受信サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価（ai_scores へ保存）
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュース LLM センチメントを合成して日次で 'bull' / 'neutral' / 'bear' を判定
- リサーチ用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（audit）
  - signal → order_request → execution のトレーサビリティ用テーブル定義と初期化（DuckDB）
- 設定管理
  - .env（.env.local）や環境変数からの自動ロード、Settings オブジェクトを介した安全な取得

前提（推奨）
------------
- Python 3.10+（typing の union 型注釈等を利用）
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - その他標準ライブラリ内で完結するユーティリティが多いですが、プロジェクトの pyproject.toml / requirements.txt を参照してください。

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <リポジトリ URL>
   - cd <repo>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 例（requirements.txt がある場合）:
     - pip install -r requirements.txt
   - 最低限（代表例）:
     - pip install duckdb openai defusedxml

   - 開発インストール（パッケージを編集しながら使う場合）:
     - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git か pyproject.toml のあるディレクトリ）に .env / .env.local を配置すると自動でロードされます（起動時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 主要な必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack ボットトークン（通知用）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（score_news / regime 判定で使用）
   - データベースパス（任意・デフォルトあり）:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
   - 環境モード:
     - KABUSYS_ENV: development / paper_trading / live
   - ログレベル:
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

使い方（基本例）
----------------

- 設定値参照（Python）
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token

- DuckDB 接続
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（run_daily_etl）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアリング（AI）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → env OPENAI_API_KEY を使用

- 市場レジーム判定
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB 初期化（監査専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
    # conn_audit を使って監査テーブルにレコードを入れていく

- ニュース RSS 取得（内部ユーティリティ）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

- ファクター計算（例）
  - from datetime import date
    from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect(str(settings.duckdb_path))
    momentum = calc_momentum(conn, target_date=date(2026,3,20))

注意点 / 動作仕様
-----------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml が存在する場所）を基準に行われます。テストなどで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは gpt-4o-mini を想定しており、API レスポンスは JSON モードで厳密にパースされます。API 失敗時はフェイルセーフ（0.0 などの中立値）で継続する設計です。
- DuckDB に対する書き込みは冪等化（ON CONFLICT）されるよう設計されています。ETL やスコア書き込みはトランザクションで保護されていますが、一部関数は transactional オプションを持ちます。
- ニュース収集は SSRF 対策、Gzip 解凍サイズチェック、トラッキングパラメータ削除などの安全処理を行います。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のみ有効です。LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のみ許容します。

ディレクトリ構成（抜粋）
----------------------
パッケージの主要ファイルと役割（src/kabusys 配下）:

- __init__.py
  - パッケージ初期化。__version__ 等。

- config.py
  - .env / 環境変数の読み込み、Settings クラス（設定取得）

- ai/
  - __init__.py
  - news_nlp.py — ニュースを銘柄別に集約して OpenAI に投げ、ai_scores へ書き込み
  - regime_detector.py — ETF 1321 の MA200 乖離とマクロニュースを合成して市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得/保存ロジック、レート制御、リトライ）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py — RSS 取得・前処理・raw_news 保存ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — zscore_normalize など汎用統計ユーティリティ
  - audit.py — 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）

- research/
  - __init__.py
  - factor_research.py — momentum/value/volatility 等のファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank

補足（開発・運用）
----------------
- 単体テストや CI のために、外部 API 呼び出し箇所はモックしやすい実装になっています（例: _call_openai_api の差し替え、news_collector._urlopen のモック等）。
- DuckDB のバージョンや SQL 構文の互換性に注意してください（コード内に DuckDB バージョン依存の注記あり）。
- 実運用での「発注」機能は本パッケージの範疇に含まれますが、実際のブローカー API と接続する際は安全側での確認（環境変数・リスク制御・監査ログ）を徹底してください。

ライセンス / 貢献
----------------
- 本リポジトリのライセンスや Contributing ガイドがあればプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

お問い合わせ
------------
- 実装の詳細や利用方法に不明点がある場合は、リポジトリの issue を作成してください。

以上。README の内容はコードベースの公開 API と設計ノートを元にまとめています。必要なら、サンプル .env.example、requirements.txt、または CLI/サービス化手順（systemd / cron ジョブ例）を追記できます。どの情報を追加しますか？