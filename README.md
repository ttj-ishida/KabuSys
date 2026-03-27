# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。  
J-Quants からのデータ ETL、ニュース収集と LLM を用いたセンチメント評価、ファクター計算・研究用ユーティリティ、発注監査ログなどを備え、バックテストや運用ワークフローで利用できるモジュール群を提供します。

## 主な特徴
- データ ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - ETL 実行後のデータ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS 取得、前処理、raw_news テーブルへの冪等保存、銘柄紐付け
  - SSRF / xml 脆弱性対策、受信サイズ制限、トラッキングパラメータ除去等の堅牢化
- AI（LLM）連携
  - ニュースを銘柄単位で集約し OpenAI（gpt-4o-mini など）でセンチメント評価（score_news）
  - マクロニュース＋ETF（1321）の MA 乖離を組み合わせ市場レジーム判定（score_regime）
  - 再試行・フォールバックロジックを備えた堅牢な API 呼び出し実装
- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化
  - 外部ライブラリに依存せず標準ライブラリ + DuckDB ベースで実装
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution を追跡する監査テーブル群の初期化・ユーティリティ
  - 冪等キー・ステータス管理・UTC タイムスタンプ
- J-Quants API クライアント
  - レート制御・リトライ・401 リフレッシュ・ページネーション対応
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar）

## 必要条件 / 依存ライブラリ
- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 使い方に応じて追加パッケージが必要になる場合があります（例: sqlite3 は標準、requests などは不要）。

インストール例:
pip install duckdb openai defusedxml

※プロジェクトに requirements.txt がある場合はそれを利用してください。

## 環境変数 / 設定
このパッケージは .env ファイル（プロジェクトルートに配置）または環境変数から設定を読み込みます。自動で .env をロードする処理が組み込まれています（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 BOT トークン
- SLACK_CHANNEL_ID (必須) — 通知先 Slack チャンネル ID
- DUCKDB_PATH (任意) — データ用 DuckDB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY (必須 for AI functions) — OpenAI API を利用する場合に必要

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

## セットアップ / 初期化手順（例）
1. Python 3.10+ を用意し、依存ライブラリをインストールする
   - pip install duckdb openai defusedxml
2. プロジェクトルートに .env を作成して必要な環境変数を配置
3. DuckDB データベース等の初期化（監査DB を別途初期化する場合）
   - 例: 監査ログ用 DB を初期化する
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)

（注）init_audit_db はデフォルトで TimeZone を UTC にセットします。

## 使い方（主要な API 例）

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント付与（ai.news_nlp.score_news）
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY must be set
  print(f"scored {count} codes")

- 市場レジーム判定（ai.regime_detector.score_regime）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY must be set

- 監査スキーマの初期化（既存接続に対して）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

- 研究用関数例（ファクター計算）
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

各モジュールはドキュメンテーション文字列で使用法が説明されているので、関数の引数や戻り値を参照してください。

## 自動 .env ロードについて
- パッケージは起動時に自動でプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` と `.env.local` を読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。

## エラー／フェイルセーフ方針（要点）
- AI 呼び出しで失敗した場合、多くの処理はゼロスコアやスキップでフォールバックし、パイプライン全体を継続します（例: macro_sentiment=0.0）。
- J-Quants クライアントはレート制御・リトライ・401 リフレッシュを行います。
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT DO UPDATE）で実装されています。
- ETL は各ステップで例外を捕捉して他ステップが実行されるように設計されています。結果は ETLResult に集約されます。

## 主要ディレクトリ構成（src/kabusys 下の概観）
- kabusys/
  - __init__.py (パッケージ初期化、バージョン情報)
  - config.py (環境変数・設定管理)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメント付与)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - calendar_management.py (マーケットカレンダー管理)
    - jquants_client.py (J-Quants API クライアント・保存関数)
    - pipeline.py (ETL パイプライン / run_daily_etl 等)
    - etl.py (ETLResult エクスポート)
    - news_collector.py (RSS 収集)
    - quality.py (データ品質チェック)
    - stats.py (統計ユーティリティ)
    - audit.py (監査ログテーブル初期化 / init_audit_db)
  - research/
    - __init__.py
    - factor_research.py (mom / value / volatility 等)
    - feature_exploration.py (forward returns / IC / summary / rank)
  - （その他）strategy / execution / monitoring 等のサブパッケージが想定される（__all__ に記載）

（注）リポジトリ内のファイルは上記コードベースに基づきます。プロジェクト固有の追加モジュール（strategy, execution, monitoring）が存在する場合は同ディレクトリ配下に配置されます。

## テスト / 開発時のヒント
- OpenAI 呼び出しや外部ネットワークを含む処理はユニットテスト用に差し替え（モック）できるよう設計されています（内部の _call_openai_api 等を patch）。
- DuckDB はファイルベースでも :memory: を指定してインメモリ接続でテスト可能です。
- 環境変数はテストごとに上書きしたい場合、プロセス環境を直接設定するか KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。

---

詳細は各モジュールの docstring を参照してください。質問や特定のユースケース（例: バックテスト用セットアップ手順、kabu ステーション発注連携のサンプル）について必要であれば、具体的に教えてください。README の補足やサンプルスクリプトを作成します。