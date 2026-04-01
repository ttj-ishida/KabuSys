# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション 等の外部サービスからデータを取得・ETL し、AI を用いたニュースセンチメントや市場レジーム判定、ファクター計算、監査ログ管理までをサポートします。

主な設計方針:
- バックテストでのルックアヘッドバイアス回避を重視（関数は内部で date.today() 等を直接参照しない）
- DuckDB を中核データストアとして冪等書き込み（ON CONFLICT）。部分失敗を避けるための考慮あり
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフ実装
- セキュリティ配慮（RSS の SSRF 防止、XML の安全パース等）

バージョン: 0.1.0

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価（日次OHLCV）、財務データ（四半期）、上場銘柄情報、JPX カレンダー取得（差分取得・ページネーション対応）
  - ETL パイプライン（差分更新 / バックフィル / 品質チェック）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集・NLP
  - RSS フィード収集（正規化・SSRF防止・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（ai_scores）生成
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM を合成）
- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどの定量ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー、Zスコア正規化
- 実行・監視・監査
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化・専用 DB 初期化ユーティリティ
  - 監視設定（PID ファイル、CPU/Mem/Disk 閾値を設定可能）
- クライアント実装の注意点
  - J-Quants 用 RateLimiter（120 req/min）とリトライ／トークン自動リフレッシュ
  - OpenAI への呼び出しは JSON Mode を用いた堅牢なパースとリトライ

---

## 必要要件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- OS: 特に制約なし（ネットワークアクセスが必要）

（プロジェクトの package 要件ファイルがある場合はそれを参照してください）

---

## セットアップ手順

1. リポジトリを取得して仮想環境を作成
   - git clone ...（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または Windows では .venv\Scripts\activate

2. 依存パッケージをインストール（例）
   - pip install -U pip
   - pip install duckdb openai defusedxml

   開発パッケージ等が requirements.txt / pyproject.toml にある場合はそちらを使用してください。

3. パッケージを編集可能モードでインストール（任意）
   - pip install -e src

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、kabusys.config が自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID: Slack チャネル ID
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 等で使用）
   - データベースや監視設定の例（任意）:
     - DUCKDB_PATH (既定: data/kabusys.duckdb)
     - SQLITE_PATH (既定: data/monitoring.db)
     - PID_FILE_PATH (既定: data/execution.pid)
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/...)

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## .env の例

.env（プロジェクトルート）に保存しておく例:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

※ 実際のトークンは安全に管理してください。

---

## 基本的な使い方

以下は主要な操作の実行例（Python スクリプトや REPL から実行）。

- DuckDB 接続の作成（ファイルベース）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行（デフォルトは今日）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースのセンチメントスコア付与（ある日付）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026,3,20))
    print(f"scored {count} codes")

- 市場レジーム判定
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20))

- 研究用ファクター計算
  - from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, date(2026,3,20))
    volatility = calc_volatility(conn, date(2026,3,20))
    value = calc_value(conn, date(2026,3,20))

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
    conn_audit = init_audit_db("data/audit.duckdb")
    # conn_audit は監査テーブルが作成済みの DuckDB 接続

注意点:
- OpenAI・J-Quants 呼び出しは API キーやトークンが必要です。未設定時は ValueError が発生します。
- API 呼び出しはリトライ・レート制御あり。テスト時は内部の _call_openai_api などをモックできます。
- DuckDB の executemany は空リストが受け付けられないバージョンがあるため、ライブラリ側でガードしています。

---

## よく使うモジュール（概要）

- kabusys.config
  - 環境変数読み込み・Settings クラス。自動 .env 読み込み（プロジェクトルート基準）、設定値へのアクセスを統一。

- kabusys.data
  - pipeline.py: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client.py: J-Quants API 取得・保存（fetch_*, save_*）
  - news_collector.py: RSS 取得 → raw_news 保存
  - quality.py: データ品質チェック
  - calendar_management.py: 営業日判定 / calendar_update_job
  - audit.py: 監査スキーマ初期化・init_audit_db

- kabusys.ai
  - news_nlp.py: 銘柄ごとのニュースセンチメントを OpenAI で算出し ai_scores に書込
  - regime_detector.py: ETF 1321 の MA200 とマクロ記事の LLM 評価を合成して market_regime に書込

- kabusys.research
  - factor_research.py: calc_momentum / calc_volatility / calc_value
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats: zscore_normalize

---

## ディレクトリ構成

（主要ファイルを抜粋）

src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      news_collector.py
      quality.py
      calendar_management.py
      stats.py
      audit.py
      audit.py
      etl.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/
      ...その他...

ドキュメントや DataPlatform.md / StrategyModel.md 等の設計資料があれば、それに準拠した実装になっています。

---

## 運用上の注意点・ベストプラクティス

- 機密情報（API トークン）は .env に平文で置くのではなく、可能ならシークレット管理ツールを利用してください。
- 本システムは本番口座での実行（live）とペーパートレード（paper_trading）を区別できる設定があり、KABUSYS_ENV を正しく設定してください。
- ETL や OpenAI 呼び出しは外部 API に依存するため、ネットワークやトークン切れに対する監視・アラートを用意してください。
- テスト運用時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動ロードを無効化できます。また、OpenAI 呼び出しなどはモックして実行してください。

---

必要であれば README にコマンドラインツール例（CLI）や CI/CD 用の設定、docker-compose サンプル、pytest 用のテスト例、より詳細な .env.example を追加できます。どの情報がさらに必要か教えてください。