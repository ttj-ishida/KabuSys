KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
概要
KabuSys は日本株向けのデータパイプライン、ファクター計算、ニュース NLP、マーケットレジーム判定、監査ログ（取引トレーサビリティ）などを含むライブラリ群です。主に以下用途を想定しています。
- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB を用いたデータ保存・ETL パイプライン
- ニュースを用いた銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 研究用ファクター計算 / 特徴量探索（バックテスト用データ準備）
- 監査ログテーブルの初期化（シグナル→約定のトレース）

主な機能一覧
- data
  - jquants_client: J-Quants API からの取得・DuckDB への保存（差分取得／ページネーション／リトライ／レート制御）
  - pipeline: 日次 ETL パイプライン（calendar / prices / financials の差分取得 + 品質チェック）
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - news_collector: RSS 取得・前処理・記事 ID 正規化・SSRF 対策・raw_news 保存支援
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（signal_events / order_requests / executions）のスキーマ初期化・DB 作成ユーティリティ
  - stats: zscore 正規化などの統計ユーティリティ
- ai
  - news_nlp.score_news: 指定日ウィンドウのニュースをまとめて OpenAI でセンチメント評価し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に書込み
- research
  - factor_research: momentum / value / volatility 等の定量ファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー等

前提（推奨）
- Python 3.10+
- 依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （必要に応じて）urllib 等の標準ライブラリは組み込み
- J-Quants API（データ取得用）と OpenAI API（ニュース NLP 用）の利用資格・API キー

セットアップ手順
1. リポジトリをクローン / コピー
   git clone <リポジトリ>
   cd <リポジトリ>

2. 仮想環境を作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（例）
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

4. 環境変数設定
   プロジェクトルートに .env / .env.local を配置すると自動でロードされます（kabusys.config が自動ロード）。
   自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で未指定時に参照）
   - KABU_API_PASSWORD: kabu ステーション用パスワード（必要に応じて）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必要に応じて）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/…

   例 .env
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

使い方（主要な関数／ワークフロー例）
- DuckDB 接続して日次 ETL を回す（簡易サンプル）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP（OpenAI）で銘柄スコアを生成
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-…")  # api_key を省略すると環境変数 OPENAI_API_KEY を参照
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-…")

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等のテーブルが作成されます

- J-Quants からデータを直接取得して保存
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2026, 3, 1), date_to=date(2026, 3, 20))
  saved = save_daily_quotes(conn, records)
  print(f"保存数: {saved}")

注意点・運用のヒント
- Look-ahead バイアス対策
  多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で datetime.today()/date.today() を直接参照せず、target_date を明示的に渡す設計です。バックテスト等では target_date を適切に指定してください。
- OpenAI 呼び出し
  - API エラーや制限（429, ネットワーク断等）に対してはリトライとフォールバック（スコア=0 等）を行う実装ですが、コストやレート制限に注意してください。
- .env の自動ロード
  - プロジェクトルート（.git または pyproject.toml）から .env を自動ロードします。テスト時に自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB execuemany の空リスト制限
  - 一部の処理は DuckDB の executemany に空リストを渡さないようガードしています（互換性対策）。手動で DB 操作を行う場合は注意してください。

ディレクトリ構成（ソースの主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得＋保存）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult 型の再エクスポート
    - calendar_management.py        — 市場カレンダー管理・営業日ユーティリティ
    - news_collector.py             — RSS 収集・前処理・SSRF 対策
    - quality.py                    — データ品質チェック
    - stats.py                      — zscore 等統計ユーティリティ
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility 等
    - feature_exploration.py        — forward returns / IC / summary

貢献・開発メモ
- テスト: 各モジュールは外部 API 呼び出しを差し替え（モック）しやすい設計になっています（例: news_nlp._call_openai_api をユニットテストで patch する等）。
- ログレベル: settings.log_level を環境変数 LOG_LEVEL で制御できます。
- 本番運用: KABUSYS_ENV を paper_trading / live に設定して、発注・実行ロジック（別モジュール）と連携する設計想定です。

ライセンス・注意事項
- 本リポジトリのコードを利用する際は API キーの取り扱い（秘匿）、外部サービスの利用規約、取引に関する法令・リスク管理に十分注意してください。

問い合わせ
- 内部ドキュメント参照: DataPlatform.md / StrategyModel.md など（リポジトリに含まれる場合）
- 実装や使い方で不明点があれば、具体的な目的（ETL の実行 / AI スコアリング / レジーム判定 など）を示して質問してください。

以上。README の内容を実行環境やポリシーに合わせて適宜更新してください。