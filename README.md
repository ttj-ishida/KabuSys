KabuSys — 日本株自動売買プラットフォーム（README）
================================

概要
--
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買の基盤モジュール群です。  
主な目的は以下です：

- J-Quants API からの株価・財務・カレンダーの差分ETL（DuckDB 保存、冪等）
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄単位）と市場レジーム判定
- 研究用ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査（audit）スキーマによるシグナル〜約定のトレーサビリティ
- kabuステーション 等の実行/監視モジュール群（パッケージ公開インターフェースを想定）

特徴（機能一覧）
--
- ETL パイプライン（kabusys.data.pipeline.run_daily_etl）
  - 市場カレンダー / 株価日足 / 財務データの差分取得・保存
  - 品質チェック（kabusys.data.quality）
- J-Quants クライアント（kabusys.data.jquants_client）
  - rate limiter、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、SSRF 対策、前処理、raw_news 保存
- AI スコアリング（kabusys.ai）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF 200日MA乖離とマクロニュースのLLMセンチメントを組合せて市場レジーム判定（market_regime）
  - OpenAI 呼び出しはリトライ・バックオフ等を実装
- 研究（kabusys.research）
  - calc_momentum / calc_volatility / calc_value 等のファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank 等の解析ユーティリティ
  - zscore_normalize（kabusys.data.stats）を用いた標準化
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日の取得、カレンダーの夜間更新ジョブ
- 監査スキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出（QualityIssue オブジェクトで返却）

動作要件（推奨）
--
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai (v1 SDK 互換)
  - defusedxml
- (オプション) requests 等（本コードは標準ライブラリ urllib を使用しているため必須ではありません）

例: 必要パッケージのインストール（例）
- 最小:
  pip install duckdb openai defusedxml
- 開発環境（仮想環境を推奨）:
  python -m venv .venv
  source .venv/bin/activate
  pip install -U pip
  pip install duckdb openai defusedxml

環境変数（主な設定）
--
自動でプロジェクトルートの .env / .env.local を読み込む仕組みがあります（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主な環境変数（必須は README 内で示す）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行時に使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

セットアップ手順
--
1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt があればそれを使ってください）

4. 環境変数設定
   - プロジェクトルートに .env を作成（.env.example を参照してください）
   - 重要: API トークンやパスワードは絶対に公開リポジトリにコミットしないでください

5. DuckDB / 監査DB の初期化（例）
   以下のスクリプトを実行して監査用 DB を初期化できます:

   python - <<'PY'
   from kabusys.data.audit import init_audit_db
   from kabusys.config import settings
   init_audit_db(settings.duckdb_path)
   print("audit DB initialized:", settings.duckdb_path)
   PY

   または、既存の duckdb 接続（duckdb.connect(...)）を取得して init_audit_schema を呼ぶことも可能です。

使い方（代表的な例）
--
- DuckDB 接続を作る
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL の実行（run_daily_etl）
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可能
  print(result.to_dict())

- ニュースセンチメントスコア生成
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY は環境変数で指定
  print("scored:", n)

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings
  import duckdb
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  volatility = calc_volatility(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])

注意点・運用メモ
--
- 環境変数やトークンは厳重に管理してください。.env は gitignore に追加してください。
- 自動 .env ロードはパッケージ起動時に有効です。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し時はレスポンスのパース失敗や API 障害に対しフェイルセーフで 0.0 を返すよう設計されています（ログを要確認）。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE 等）を意識して実装されていますが、運用前に必ずテストを行ってください。
- DuckDB のバージョン差異により executemany の挙動が異なるケースがあるため、実行環境の duckdb バージョンを合わせることを推奨します。

ディレクトリ構成
--
（主要ファイルのみ抜粋）

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
      audit.py
      calendar_management.py
      etl.py
      jquants_client.py
      news_collector.py
      pipeline.py
      quality.py
      stats.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/
      (factor / feature utilities)
    (その他: strategy / execution / monitoring はパッケージ公開インターフェースに含まれる想定)

各モジュールの役割
- kabusys.config: 環境変数・設定管理（.env 自動ロード、設定プロパティ）
- kabusys.data: ETL・J-Quants クライアント・ニュース収集・品質・カレンダー・監査
- kabusys.ai: LLM を使ったニューススコアリング・レジーム判定
- kabusys.research: ファクター計算・解析ユーティリティ

貢献・開発
--
- コードは型アノテーションとドキュメンテーションストリングを重視して記述されています。新機能追加やバグ修正は PR の形でお願いします。
- API キーや重要な資格情報を含むファイルは絶対にコミットしないでください。

ライセンス
--
- このリポジトリにライセンスファイルが同梱されている場合はそちらに従ってください（本 README には明記されていません）。

問い合わせ
--
- 実行時の問題や不明点はログ（設定した LOG_LEVEL）を確認の上、必要であれば issue を作成してください。

以上。必要に応じて README にコード例の追加や手順の詳細化（監視ジョブの設定、kabuステーションとの連携、Slack 通知設定方法など）を追記できます。どの部分を詳しく書きたいか教えてください。