KabuSys — 日本株向けデータ基盤＋自動売買リサーチライブラリ
=================================================

概要
----
KabuSys は日本株のデータ収集（J‑Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング、そして市場レジーム判定や監査ログ管理までをカバーする Python ライブラリです。  
設計上のポイントは次のとおりです。

- DuckDB をデータレイクとして利用し、ETL と品質チェックを行う
- J‑Quants API による差分取得（レートリミット・リトライ・トークン自動更新対応）
- ニュースの LLM スコアリング（OpenAI）を用いた銘柄別センチメント / マクロセンチメント評価
- 監査ログ（signal → order_request → executions）のスキーマ定義と初期化ユーティリティ
- ルックアヘッドバイアス回避（内部処理は date 引数ベース、datetime.now を直接参照しない等）
- 冪等性を意識した保存（ON CONFLICT / idempotent 保存）

主な機能
--------
- データ取得・ETL
  - J‑Quants から株価日足・財務・上場情報・市場カレンダーの差分取得（fetch_*）
  - DuckDB への冪等保存（save_*）
  - 日次 ETL パイプライン run_daily_etl
- データ品質チェック
  - 欠損・重複・日付不整合・スパイク検出（quality.run_all_checks 等）
- ニュース収集 / 前処理
  - RSS 取得・正規化・記事ID生成・raw_news への保存を想定したユーティリティ（news_collector）
- NLP（OpenAI）
  - 銘柄別ニュースセンチメントを ai_scores に書き込む score_news
  - ETF（1321）MA 乖離とマクロニュースを組み合わせた市場レジーム判定 score_regime
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算（research.calc_*）
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化（research.feature_exploration, data.stats）
- 監査（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化（data.audit.init_audit_db）
- 設定管理
  - .env / 環境変数読み込み（config.Settings）と自動ロード（プロジェクトルート検出）

セットアップ
-----------
前提
- Python 3.10 以上（型注釈・Union | を使用）
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パース安全化）
- その他：標準ライブラリ + urllib 等

推奨手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係のインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. パッケージを開発モードでインストール（任意）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに .env を置くと自動的に読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを特定）。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主な環境変数
- 必須（機能使用に応じて）
  - JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン
  - OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime で参照）
  - SLACK_BOT_TOKEN        : Slack 通知用（使用する場合）
  - SLACK_CHANNEL_ID       : Slack チャンネル ID（使用する場合）
  - KABU_API_PASSWORD      : kabu API パスワード（kabu 関連機能）
- 任意（デフォルト値あり）
  - KABU_API_BASE_URL      : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH            : SQLite（監視用）パス（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV (development / paper_trading / live)
  - LOG_LEVEL (DEBUG/INFO/...)

使用例（簡単なコード断片）
------------------------

- DuckDB 接続を作って日次 ETL を実行する
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアリング（OpenAI）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect(str(settings.duckdb_path))
    count = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → env OPENAI_API_KEY を使用

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))

- ファクター計算（研究用）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    mom = calc_momentum(conn, date(2026,3,20))

- 監査 DB の初期化
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")

注意点 / 設計上の考慮
-------------------
- ルックアヘッドバイアス回避:
  - score_news / score_regime / ETL 等は内部で date を明示的に受け取り、datetime.now()/today() に依存しない実装方針です。
- 冪等性:
  - J‑Quants からの保存は ON CONFLICT（UPDATE）で上書きするため再実行可能。
- リトライ・レート制御:
  - jquants_client は API レート制限（120 req/min）を守るための RateLimiter、リトライ、401→トークンリフレッシュ対応を持ちます。
- フェイルセーフ:
  - LLM 呼び出し失敗時はスコアをゼロにフォールバックする等、全面的にフェイルセーフ設計になっています（例: マクロセンチメントが失敗しても処理は継続）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は本リポジトリの主要なファイル/モジュール構成の抜粋です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュース NLP（score_news）
    - regime_detector.py           -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            -- J‑Quants API クライアント（fetch_* / save_*）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl など）
    - etl.py                       -- ETL 便利インターフェース（ETLResult 再エクスポート）
    - news_collector.py            -- RSS 収集・前処理ユーティリティ
    - calendar_management.py       -- 市場カレンダー管理（is_trading_day 等）
    - quality.py                   -- データ品質チェック
    - stats.py                     -- zscore_normalize 等
    - audit.py                     -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           -- momentum/value/volatility
    - feature_exploration.py       -- forward returns / IC / rank / summary
  - ai/ (上記)
  - その他モジュール群...

追加情報 / トラブルシューティング
---------------------------------
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動で読み込みます。
  - テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI JSON Mode:
  - score_news / score_regime は OpenAI の JSON Mode（response_format={"type":"json_object"}）を前提にレスポンスを厳密な JSON としてパースします。レスポンスが期待形式でない場合は警告をログに出してフォールバックします。
- デバッグ:
  - settings.log_level を DEBUG に設定すると内部ログが詳細に出力されます（環境変数 LOG_LEVEL）。

貢献
----
バグ報告や改善提案は issue を立ててください。Pull Request を歓迎します。

ライセンス
----------
（必要に応じてプロジェクトのライセンス情報をここに追記してください）

以上。README に追記してほしい実行例（コマンド・CI 設定・依存固定ファイルなど）があれば教えてください。