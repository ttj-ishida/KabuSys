KabuSys
======

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買リサーチ基盤のモジュール群です。  
J-Quants からのデータ取得・ETL、ニュース収集と LLM を使ったニュースセンチメント評価、ファクター計算・特徴量探索、監査ログ（トレーサビリティ）などを含む設計になっています。  
バックテストや本番運用向けに Look-ahead バイアス対策、冪等性、API リトライ・レート制御、セキュリティ対策（SSRF防止等）などの実装方針を採用しています。

主な機能
--------
- 環境設定管理
  - .env / .env.local から自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得と検証（settings オブジェクト）
- データ取得 / ETL
  - J-Quants API から株価（日足）、財務データ、JPX カレンダーを差分取得（ページネーション対応）
  - 差分保存（DuckDB への冪等保存、ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集 / NLP
  - RSS 取得と前処理（URL正規化、SSRF対策、サイズ制限）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントスコア算出（ai.news_nlp.score_news）
  - マクロニュース × ETF MA200 乖離の合成による市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI 呼び出しは JSON Mode を使い、レスポンスバリデーションとリトライ制御を実装
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（research.feature_exploration）
  - z-score 正規化ユーティリティ（data.stats）
- 監査・実行ログ
  - signal → order_request → execution までの監査スキーマ定義と初期化ユーティリティ（data.audit）
  - 監査DB初期化（init_audit_db）
- ユーティリティ
  - 市場カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - J-Quants クライアント（認可・レート制御・リトライ）

動作要件（推奨）
----------------
- Python 3.10 以上
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants API / RSS フィード / OpenAI）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを利用）

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を作成（.env.example を参照）
   - 例: 必須変数
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（実行モジュール使用時）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: （通知機能を使う場合）
   - 注意: 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

5. データベース初期化（監査ログ等）
   - 監査DB（DuckDB）を初期化する例:
     - python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"

基本的な使い方
--------------
- 設定値へアクセス
  - from kabusys.config import settings
  - settings.duckdb_path などで Path を取得できます（デフォルト data/kabusys.duckdb）

- 日次 ETL を実行
  - 例:
    - from datetime import date
      from kabusys.data.pipeline import run_daily_etl
      import duckdb
      from kabusys.config import settings
      conn = duckdb.connect(str(settings.duckdb_path))
      result = run_daily_etl(conn, target_date=date(2026,3,20))
      print(result.to_dict())

- ニュースセンチメントスコア（AI）
  - score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込み
    - from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date=date(2026,3,20))
  - score_regime: 市場レジーム（bull/neutral/bear）を market_regime テーブルへ書き込み
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date=date(2026,3,20))

- 監査スキーマ初期化
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn)  # conn は DuckDB 接続

- J-Quants 認可トークン取得（必要な場合）
  - from kabusys.data.jquants_client import get_id_token
    token = get_id_token()  # settings.jquants_refresh_token を使用

設計上の注意点（抜粋）
--------------------
- Look-ahead バイアス防止:
  - 日付参照に datetime.today() / date.today() を安易に使わない設計（target_date を明示）
  - prices_daily や raw_news のクエリは target_date より前のデータのみを使う等の配慮
- 冪等性:
  - DB へは基本的に ON CONFLICT DO UPDATE / INSERT … ON CONFLICT 等で冪等保存
- API レート制御・リトライ:
  - J-Quants は固定間隔スロットリングで制御、リトライ・トークンリフレッシュを実装
  - OpenAI 呼び出しは JSON Mode を利用し、429/タイムアウト/5xx 等に対して指数バックオフでリトライ
- セキュリティ:
  - RSS 取得は SSRF 対策（ホスト検査・リダイレクト検査）および受信サイズ制限、defusedxml による XML パース保護
- テスト容易性:
  - OpenAI 呼び出し等は内部関数をパッチ可能な構造（ユニットテストでの差し替えを想定）

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py             -- ニュースセンチメント（OpenAI）
    - regime_detector.py      -- ETF MA200 + マクロセンチメントで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント（取得 / 保存）
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - etl.py                  -- ETLResult の公開
    - news_collector.py       -- RSS 収集と前処理
    - calendar_management.py  -- 市場カレンダー管理・ユーティリティ
    - quality.py              -- データ品質チェック
    - stats.py                -- 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                -- 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py      -- Momentum / Volatility / Value の計算
    - feature_exploration.py  -- 将来リターン / IC / 統計サマリー
  - research/...              -- その他リサーチ用ユーティリティ
  - ai/...                    -- AI 関連モジュール
  - data/...                  -- データ層モジュール群

よくあるコマンド例
-----------------
- 開発インストール（パッケージとして使う場合）
  - pip install -e .

- DuckDB に接続して関数を実行する（REPL 例）
  - python - <<'PY'
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    print(run_daily_etl(conn).to_dict())
    PY

付録：主要環境変数（抜粋）
------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news/score_regime 用、必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

開発・運用上の補足
-----------------
- DuckDB のバージョンや OpenAI / J-Quants SDK の変更により例外や戻り値の形が変わる可能性があります。SDK 仕様変更時は呼び出し箇所の互換性を確認してください。
- ETL や AI 呼び出しは外部 API を使用するため、実行時のレートやコストに注意してください。
- 本リポジトリは設計方針（Look-ahead 回避、冪等性、ログ保存）を重視しており、本番での発注ロジックや金銭的運用は別途十分な検証・リスク管理が必要です。

お問い合わせ / 貢献
-------------------
- プロジェクトの改善提案やバグ報告、Pull Request を歓迎します。README や CONTRIBUTING がある場合はそちらに従ってください。

以上。README の補足や具体的な利用シナリオ（例: バッチスケジュール、Slack 通知連携、kabuステーションとの接続例）が必要であれば教えてください。