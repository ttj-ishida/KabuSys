KabuSys — 日本株自動売買システム（README）

プロジェクト概要
- KabuSys は日本株向けのデータパイプライン、NLP/LLM ベースのニュース評価、ファクター算出、監査ログ管理、ETL や市場カレンダー管理を含む「自動売買／リサーチ基盤」を意図した Python パッケージです。
- データ取得は J-Quants API、ニュース収集は RSS（news_collector）、センチメント評価は OpenAI（gpt-4o-mini）を利用する設計になっています。
- DuckDB を主な永続化層として利用し、監査ログ用 DB や SQLite（モニタリング）もサポートします。

主な機能一覧
- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動ロード（無効化可）
  - 必須設定の取得・検証（settings オブジェクト）
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants からの差分取得（株価・財務・カレンダー）、ページネーション、リトライ、レートリミット対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL 実行 run_daily_etl（品質チェック含む）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue 型で集約）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日検索、JPX カレンダー ETL（calendar_update_job）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・SSRF 対策・トラッキングパラメータ除去・raw_news 保存
- AI ニュース解析（kabusys.ai.news_nlp）
  - ニュースを銘柄ごとに集約し OpenAI にバッチ送信して ai_scores を更新
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを融合して日次レジーム判定
- リサーチ / ファクター計算（kabusys.research）
  - Momentum / Volatility / Value ファクター、将来リターン計算、IC（Spearman）や統計サマリ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルを定義・初期化（トレーサビリティ確保）

セットアップ手順（開発向け）
1. リポジトリをクローン
   git clone <repo_url>
   cd <repo_root>

2. Python 環境
   - 推奨: Python 3.10+
   - 仮想環境を作成してアクティブにする（venv, pyenv 等）

3. 必要パッケージのインストール（例）
   pip install -e ".[all]"
   ※ 実際の pyproject.toml / requirements があればそちらを使用してください。
   主要依存例:
   - duckdb
   - openai
   - defusedxml

4. 環境変数 / .env ファイル
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます（起動時、env が設定されていなければ .env を読み込み、.env.local は上書き）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   最低限必要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_station_password
   - SLACK_BOT_TOKEN=your_slack_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=your_openai_api_key  (score_news / regime で利用)

   オプション:
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト development)
   - LOG_LEVEL=INFO|DEBUG|...  (デフォルト INFO)
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動 .env ロードを無効化

   （.env.example を作成してプロジェクトに含めると便利です）

5. DuckDB 初期化（監査 DB 等）
   - 監査ログ用 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - 既存接続にスキーマを適用する場合:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

使い方（主要なサンプル）
- 日次 ETL 実行（DuckDB 接続を作成して run_daily_etl を呼ぶ例）:
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI API キー必須）:
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print("scored:", n_written)

- 市場レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査 DB 初期化（別 DB にする場合）:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- 研究用ファクター計算例:
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  # momentum は各銘柄ごとの dict のリスト

注意点 / 運用メモ
- Look-ahead バイアス防止: 多くの関数は内部で date.today() を直接参照せず、target_date を明示的に受け取る設計です。バッチやバックテストで使用するときは target_date を制御してください。
- OpenAI 呼び出し: ネットワークエラーやレート制限に対してリトライ設計が入っていますが、API キーは適切に設定してください。テスト時は該当内部関数をモックできます（コード中に patch を想定したコメントあり）。
- .env の自動読み込み: プロジェクトルートを __file__ の親から探索する実装のため、パッケージ配布後も動作します。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB 互換性: コードはいくつかの箇所で DuckDB の executemany の仕様やバージョン差分を考慮しています。運用する DuckDB バージョンで動作確認を行ってください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py (環境変数 / Settings)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存ロジック)
    - pipeline.py (ETL パイプライン、run_daily_etl 等)
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py (RSS 収集・保存)
    - calendar_management.py (市場カレンダー管理)
    - quality.py (データ品質チェック)
    - stats.py (統計ユーティリティ)
    - audit.py (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py (momentum/value/volatility 等)
    - feature_exploration.py (forward returns, IC, summaries)
  - ai, data, research 以下に多数の内部ユーティリティ関数と設計注釈あり

テスト／開発補助
- 各種外部 API 呼び出し（OpenAI / J-Quants / RSS）を行う箇所には、モックや patch で差し替え可能な内部ラッパー関数が用意されています。ユニットテストではこれらを差し替えて API 呼び出しを回避してください。
- DuckDB はインメモリ ":memory:" での接続もサポートしているため、テスト時はファイルを書き出さずに動作確認できます。

ライセンス・貢献
- 本 README に含めたいライセンス情報やコントリビューションガイドがあればプロジェクトに追加してください（ここには記載がありません）。

補足（よくある問い合わせ）
- 「どの環境変数が必須か？」: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID は Settings から必須として取得されます。AI 周り（score_news 等）を使う場合は OPENAI_API_KEY が必要です。
- 「.env の読み込み場所は？」: プロジェクトルート（.git または pyproject.toml を基準）から .env を読み込みます。CWD に依存しないため、パッケージ内からの参照も安定しています。

以上。必要であれば README に含めるサンプル .env.example、運用フロー図、コマンドラインの実行例（cron / Airflow など）や詳細な API 使用例を追加作成します。どの情報を優先して追加したいか教えてください。