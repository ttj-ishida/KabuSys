KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株のデータ収集（ETL）・品質チェック・ファクター計算・ニュース NLP（LLM）による銘柄スコアリング・市場レジーム判定・監査ログ管理などを備えた自動売買／リサーチ基盤ライブラリです。  
モジュールは DuckDB をデータ層に使い、J-Quants API / RSS / OpenAI（gpt-4o-mini 等）を利用してデータ取得や NLP を行います。設計上、ルックアヘッドバイアスを避ける工夫や、冪等性・リトライ・フェイルセーフを重視しています。

主な機能
---------
- ETL（jquants_client 経由）
  - 日次株価（OHLCV）の差分取得と DuckDB への冪等保存
  - 財務データの差分取得と保存
  - JPX マーケットカレンダー取得・保存（営業日判定に利用）
- データ品質チェック（quality）
  - 欠損値、主キー重複、スパイク、日付不整合の検出
- ニュース収集（news_collector）
  - RSS から記事取得、前処理、raw_news と news_symbols への保存（SSRF/Gzip/サイズ対策あり）
- ニュース NLP（news_nlp）
  - OpenAI を用いた銘柄ごとのセンチメントスコア算出（JSON Mode / バッチ・リトライ実装）
- 市場レジーム判定（regime_detector）
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを重み合成して日次レジーム判定
- リサーチ（research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算、将来リターン、IC 計算、統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル定義および初期化ユーティリティ（冪等、UTC 保存）
- 設定管理（config）
  - .env / 環境変数から設定を自動読み込み（プロジェクトルート検出）、必須値チェック

前提条件（目安）
----------------
- Python 3.10+
- DuckDB
- OpenAI Python SDK（OpenAI クライアント）
- defusedxml（RSS パース保護）
- （標準ライブラリの urllib 等を使用。requests は不要）

セットアップ手順
---------------
1. リポジトリのチェックアウト（適宜）
   - ソースはパッケージルートに src/kabusys 配下で想定されています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトがパッケージ化されている場合）pip install -e .

   例:
   - pip install -e .[dev] など（extras がある場合）

4. 環境変数 / .env 設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（デフォルト）。テスト等で自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector で使用）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : SQLite（監視系）ファイルパス（デフォルト data/monitoring.db）
     - KABUSYS_ENV           : 実行環境 ("development" | "paper_trading" | "live")（デフォルト development）
     - LOG_LEVEL             : ログレベル ("DEBUG","INFO",...)（デフォルト INFO）
   - .env のサンプル例（.env.example をプロジェクトルートに作ることを推奨）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=secret
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

使い方（主要 API と簡単なコード例）
----------------------------------

- DuckDB 接続の例
  - import duckdb
    from kabusys.config import settings
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（データ収集 + 品質チェック）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュース NLP（AI スコアリング）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    # OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
    written = score_news(conn, target_date=date(2026,3,20))
    print(f"書き込んだ銘柄数: {written}")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20))

- 監査ログ初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # 初期化された接続を利用して order_requests 等を記録・検索可能

- ファクター計算・リサーチ
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
    conn = duckdb.connect(str(settings.duckdb_path))
    momentum = calc_momentum(conn, date(2026,3,20))
    vol = calc_volatility(conn, date(2026,3,20))
    # 正規化
    momentum_z = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

注意点・設計上の特徴
-------------------
- ルックアヘッドバイアス防止:
  - 多くの関数は内部で datetime.today()/date.today() を直接参照せず、target_date を引数として受け取ります。ETL / スコアリングは必ず指定日時以前のデータのみを参照する設計です。
- 冪等性:
  - J-Quants の保存処理（save_*）やニュース保存などは ON CONFLICT DO UPDATE / DO NOTHING を使用し冪等性を保証します。
- フェイルセーフ:
  - API 呼び出し失敗時は可能な限り処理継続（LLM 失敗時はスコアを 0 にフォールバックなど）する設計。
- テストしやすさ:
  - OpenAI 呼び出しはモジュール内のラッパー関数（_call_openai_api）を patch して差し替え可能です。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                       # 環境変数・設定管理
    ai/
      __init__.py
      news_nlp.py                    # ニュース NLP（OpenAI 経由）
      regime_detector.py             # 市場レジーム判定
    data/
      __init__.py
      jquants_client.py              # J-Quants API クライアント（取得＋DuckDB 保存）
      pipeline.py                    # ETL パイプラインと run_daily_etl
      etl.py                         # ETL の公開インターフェース
      news_collector.py              # RSS ニュース収集
      calendar_management.py         # マーケットカレンダー管理・営業日判定
      quality.py                     # データ品質チェック
      stats.py                       # 統計ユーティリティ（zscore）
      audit.py                       # 監査ログテーブル定義 / 初期化
    research/
      __init__.py
      factor_research.py             # Momentum / Value / Volatility 等
      feature_exploration.py         # 将来リターン / IC / summary
    ai/                              # AI 関連（上記）
    research/                        # 研究用モジュール
    monitoring/                      # 監視用 DB / ロジック（存在する場合）
    execution/                       # 注文実行関連（存在する場合）
    strategy/                        # 戦略ロジック（存在する場合）

ログ・デバッグ
---------------
- 設定は環境変数 LOG_LEVEL で制御します（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- ETL / 品質チェック / AI モジュールは logger を使用して情報を出力します。

テスト・モック
--------------
- OpenAI へ実際にアクセスせずにテストしたい場合、kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替えてレスポンスを返すことが想定されています。

その他
-----
- 自動で .env を読み込む実装は config モジュールにあり、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env/.env.local を適用します。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 呼び出しは内部で固定間隔のレート制御とリトライを実装しています。API トークンは get_id_token を通してリフレッシュされます。

ライセンスや貢献方法、詳細な設計ドキュメント（DataPlatform.md / StrategyModel.md 等）はプロジェクト別ドキュメントを参照してください。

必要があれば README にサンプル .env.example を追加、あるいは CI / デプロイ用の運用手順（cron ジョブ例、Dockerfile 例）も作成します。追加で記載したい内容があれば教えてください。