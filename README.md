# KabuSys — 日本株自動売買プラットフォーム（README）

このリポジトリは「KabuSys」と呼ばれる日本株向けのデータ基盤・リサーチ・AI支援・自動売買監査を想定したライブラリ群です。DuckDB をデータ層に用い、J-Quants や RSS、OpenAI を利用したニュース NLP／市場レジーム判定、ETL、データ品質チェック、監査ログなどの機能を備えます。

以下はコードベースから生成した README です。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（代表的な API とサンプル）
- 環境変数 / .env の扱い
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買プラットフォームの基礎ライブラリ群です。
- データ取得（J-Quants）→ ETL → 品質チェック → 解析（ファクター計算・リサーチ）→ AI（ニュースセンチメント/市場レジーム）→ 監査ログ（発注・約定追跡）までをカバーするモジュール群を提供します。
- データベースとして DuckDB を利用し、ニュース収集には RSS、NLP には OpenAI（gpt-4o-mini 等）を利用する想定です。

主な機能一覧
- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須設定チェック（Settings クラス）
- データ ETL（jquants_client + pipeline）
  - J-Quants API から株価日足 / 財務データ / 市場カレンダーを差分取得・保存
  - run_daily_etl による日次パイプライン（カレンダー → 株価 → 財務 → 品質チェック）
  - 保存は冪等（ON CONFLICT DO UPDATE）で実装
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合チェック
  - QualityIssue データクラスで詳細を返す
- ニュース収集
  - RSS からのニュース取得（SSRF 対策、URL 正規化、前処理）
  - raw_news / news_symbols への冪等保存を想定
- ニュース NLP / AI
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI により算出し ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込み
  - OpenAI 呼び出しはリトライ・エラーハンドリングを備える
- リサーチ / ファクター計算
  - calc_momentum / calc_volatility / calc_value：モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB 上で SQL / Python）
  - calc_forward_returns / calc_ic / factor_summary / rank：将来リターン・IC 計算・統計サマリー
  - zscore_normalize：クロスセクション Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events, order_requests, executions テーブル定義とインデックス
  - init_audit_db / init_audit_schema による DuckDB 初期化（UTC タイムゾーン固定）
- J-Quants クライアント（jquants_client）
  - 認証トークン（refresh → id_token）、ページネーション対応、レート制御、リトライ実装
  - fetch_* / save_* の一連 API（fetch_daily_quotes, save_daily_quotes 等）

セットアップ手順（例）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 環境の作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主要パッケージの例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env を作成すると自動で読み込まれます（.env.local は上書き）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1 など

5. DuckDB ファイルや監査 DB を初期化（任意）
   - Python REPL / スクリプトから:
     - import duckdb
     - from kabusys.config import settings
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db(settings.duckdb_path)  # または別パス

6. 実行（ETL / AI 処理等）は下記サンプル参照

使い方（代表的な API とサンプル）

- 環境設定参照（Settings）
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env などを参照

- 日次 ETL（run_daily_etl）
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメント (AI)
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY 環境変数使用

- 市場レジーム評価 (AI)
  - from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- リサーチ / ファクター計算
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect(str(settings.duckdb_path))
    momentum = calc_momentum(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

環境変数 / .env の扱い
- 自動ロード
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探索し、.env を自動で読み込みます。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - テストなどで自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な必須環境変数（Settings で必須とされるもの）
  - JQUANTS_REFRESH_TOKEN   → J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD       → kabuステーション API パスワード（必須）
  - SLACK_BOT_TOKEN         → Slack 通知用 Bot トークン（必須）
  - SLACK_CHANNEL_ID        → Slack チャンネル ID（必須）
- 任意 / デフォルト設定
  - KABUSYS_ENV             → development / paper_trading / live （デフォルト: development）
  - LOG_LEVEL               → DEBUG / INFO / ...（デフォルト: INFO）
  - DUCKDB_PATH             → デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH             → 監視用 SQLite デフォルト "data/monitoring.db"
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視しきい値）

例: .env の簡易テンプレート
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- OPENAI_API_KEY=sk-...

注意事項（設計上の重要点）
- Look-ahead バイアス対策: 多くの関数は内部で datetime.today()/date.today() を無条件に参照せず、呼び出し側が target_date を明示的に渡すことを前提にしています。バックテスト時は開始日以前のデータのみを使う等の注意が必要です。
- API 呼び出しはリトライおよびフェイルセーフを備えますが、キーがない場合は ValueError を投げます（OpenAI のキーや J-Quants トークンなど）。
- DuckDB バージョンや SQL の互換性によりパラメータバインドの扱いに注意があります（コード内に対策あり）。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                      -- 環境設定・.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース NLP（score_news）
    - regime_detector.py           -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（fetch / save）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 他）
    - etl.py                       -- ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py            -- RSS ニュース収集
    - calendar_management.py       -- 市場カレンダー管理（is_trading_day 等）
    - quality.py                   -- データ品質チェック
    - stats.py                     -- 統計ユーティリティ（zscore_normalize）
    - audit.py                     -- 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py           -- calc_momentum, calc_value, calc_volatility
    - feature_exploration.py       -- calc_forward_returns, calc_ic, rank, summary
  - ai/, data/, research/ の各モジュールは相互に参照するが、設計上ルックアヘッドやモジュール結合を避ける工夫があります。

最後に
- ここに示した README はコードからの構造抜粋に基づくドキュメントです。実際の運用では依存パッケージのバージョン管理（requirements.txt / pyproject.toml）、実行用 CLI やサービスラッパー、ユニットテスト、運用手順（監視・ロギング・スケジューラ）を追加してください。
- 追加のサンプルや CLI、CI/CD 用の設定を作成する場合は README と合わせて整備することを推奨します。

必要であれば、以下の点について追記します:
- 具体的な pip / pyproject の依存一覧
- サンプル Dockerfile / systemd ユニット例
- 各テーブル（raw_prices / raw_financials / ai_scores / market_regime など）のスキーマ定義一覧

ご希望があれば追加で作成します。