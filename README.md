KabuSys — 日本株自動売買 / データプラットフォーム
=================================================

概要
----
KabuSys は日本株向けのデータプラットフォームと研究・自動売買の基盤ライブラリです。  
主な目的は、J-Quants API や RSS ニュースからのデータ収集（ETL）、データ品質チェック、特徴量（ファクター）計算、LLM を使ったニュースセンチメント評価および市場レジーム判定、そして監査ログ（注文／約定のトレーサビリティ）を提供することです。

機能一覧
--------
- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存
  - 差分更新／バックフィル、ページネーション対応、トークン自動リフレッシュ、レート制御・リトライ
- データ品質チェック
  - 欠損・重複・スパイク・日付不整合の検出（QualityIssue）
- ニュース収集・NLP
  - RSS 収集（SSRF 防止、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄単位のニュースセンチメント評価（ai_scores への書き込み）
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM スコアを合成して日次で market_regime を算出
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン、IC（Information Coefficient）、ファクター統計サマリ
  - Z スコア正規化ユーティリティ
- 監査ログ (Audit)
  - signal_events / order_requests / executions 等の監査テーブル生成・初期化（DuckDB）
  - 発注フローのトレーサビリティ（UUID ベース）
- 設定管理
  - .env（.env.local）/ 環境変数からの設定読み込み（自動ロード機能）

要件（主な依存）
----------------
- Python 3.10+
- duckdb
- openai
- defusedxml
- （その他）標準ライブラリ

インストール
------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （ローカル開発）プロジェクトルートで: pip install -e .

環境変数と .env
----------------
パッケージは起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、.env → .env.local の順に自動読み込みします。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

主に使用する環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに使用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment (development/paper_trading/live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例: .env の最小例
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb

セットアップ手順（簡易）
-----------------------
1. 必要な Python パッケージをインストール（上記参照）。
2. .env をプロジェクトルートに作成して必要な値を設定。
3. DuckDB のスキーマ初期化（必要に応じてアプリ側で実行）：
   - 監査DBを作る例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

使い方（主要な API と実行例）
----------------------------

- 設定参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live などを参照できます。

- 日次 ETL の実行（データ取得 → 品質チェック）
  - 例:
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

  - run_daily_etl は ETLResult を返します。個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）も利用可能です。

- ニュースセンチメントのスコアリング
  - ai.news_nlp の score_news を使用して raw_news / news_symbols データから ai_scores を作成します。
  - 例:
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=settings.openai_api_key if hasattr(settings,'openai_api_key') else None)
    print(f"wrote {n_written} scores")

  - api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を利用します。API 呼び出しの失敗はフェイルセーフでスキップします。

- 市場レジーム判定
  - ai.regime_detector.score_regime を使い、ETF（1321）MA200 とマクロニュースを組み合わせて market_regime テーブルに書き込みます。
  - 例:
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数からキーを読む

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - 例:
    records = calc_momentum(conn, target_date=date(2026, 3, 20))

- 監査ログ（監査テーブル初期化）
  - from kabusys.data.audit import init_audit_db, init_audit_schema
  - 例（ファイル DB を初期化）:
    conn = init_audit_db("data/audit.duckdb")
    # あるいは既存接続に対して:
    init_audit_schema(conn, transactional=True)

注意事項 / 設計上のポイント
-------------------------
- Look-ahead バイアス防止: 多くの関数は datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計です。バックテストでの利用時は target_date を適切に指定してください。
- フェイルセーフ設計: LLM/API の一時的失敗時はゼロフォールバックやスキップで継続するようになっています（例: macro_sentiment=0.0）。
- DuckDB とのやり取りは SQL と executemany を多用し、冪等性（ON CONFLICT DO UPDATE）を重視しています。
- .env の自動読み込みはプロジェクトルート検出に基づきます。テストで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py             — パッケージ定義（version 等）
- config.py               — 環境変数 / 設定管理（.env 自動ロード含む）
- ai/
  - __init__.py
  - news_nlp.py           — ニュース NLP（score_news）
  - regime_detector.py    — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理
  - etl.py                 — ETL インターフェース（ETLResult 再エクスポート）
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - stats.py               — 統計ユーティリティ（zscore_normalize）
  - quality.py             — データ品質チェック
  - audit.py               — 監査テーブル定義 / 初期化
  - jquants_client.py      — J-Quants API クライアント（fetch / save）
  - news_collector.py      — RSS ニュース収集
- research/
  - __init__.py
  - factor_research.py     — ファクター計算（momentum / value / volatility）
  - feature_exploration.py — 前方リターン / IC / サマリ等
- research: 研究用のユーティリティ群（factor / feature）

テスト & 開発
--------------
- 単体テストや CI を組む場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを回避できます。
- LLM 呼び出しや外部 API はモック可能に設計されています（内部の _call_openai_api や _urlopen などを patch）。

ライセンス / コントリビュート
-----------------------------
（プロジェクト固有のライセンス・貢献ルールはここに追記してください）

付録：便利な関数リファレンス（抜粋）
---------------------------------
- ETL / データ取得
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(...)

- ニュース / AI
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 監査ログ
  - kabusys.data.audit.init_audit_db(path)
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)

質問や追加したいドキュメント項目があれば教えてください。README のサンプルコードや .env.example を作成することもできます。