# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、ニュースNLP、ファクター計算、監査ログなど、トレーディングシステムの基盤となる機能群を提供します。

主な目的
- J-Quants API からのデータ取得と DuckDB への差分保存（ETL）
- RSS ニュース収集と LLM による銘柄センチメント算出
- 市場レジーム判定（ETF + マクロ記事の合成）
- ファクター計算・特徴量探索（研究用途）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）

要求環境
- Python 3.10+
- 推奨パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリのみで動作するモジュールも多く含まれます

（実際の環境では pip の requirements.txt を用意してインストールしてください）

機能一覧
- data.jquants_client: J-Quants API クライアント（差分取得、ページネーション、保存関数）
- data.pipeline: ETL パイプライン（run_daily_etl／個別 ETL）
- data.news_collector: RSS 収集 + 前処理 + raw_news への保存（SSRF 対策、gzip 上限など）
- ai.news_nlp: OpenAI を用いたニュースの銘柄別センチメント算出（JSON Mode、バッチ処理）
- ai.regime_detector: ETF（1321）200 日 MA 乖離 + マクロ記事センチメントから市場レジーム判定
- research.*: ファクター計算（モメンタム／ボラティリティ／バリュー）、将来リターン・IC・統計サマリ
- data.quality: ETL 後の品質チェック（欠損・重複・スパイク・日付不整合）
- data.audit: 監査ログテーブル定義・初期化ユーティリティ（init_audit_schema / init_audit_db）
- config: 環境変数管理（.env 自動読み込み、必須値チェック、KABUSYS_ENV, LOG_LEVEL 等）

セットアップ手順（ローカル開発向け）
1. Python を用意（推奨: 3.10+）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数を設定
   - プロジェクトルートの .env または .env.local を作成することで自動ロードされます（優先度: OS env > .env.local > .env）
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必要な環境変数（少なくとも以下を設定してください）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知が必要な場合
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - KABU_API_PASSWORD: kabu API パスワード（kabuステーション連携時）
     - OPENAI_API_KEY: OpenAI を利用する場合（score_news / score_regime を使う際に必要）
   - オプション:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env の例
（実運用では秘密情報は安全に管理してください）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（プログラム的に呼び出す例）
- DuckDB 接続を作成して ETL を実行する
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコア算出（ai.news_nlp.score_news）
  - 事前に raw_news / news_symbols テーブルにデータが存在していること
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print(f"written scores: {written}")

  - api_key を省略すると環境変数 OPENAI_API_KEY が使われます

- 市場レジーム算出（ai.regime_detector.score_regime）
  - 1321 の prices_daily と raw_news が必要
  - 例:
    from kabusys.ai.regime_detector import score_regime
    from datetime import date
    import duckdb

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY を利用

- 監査ログ DB の初期化
  - 単体の監査用 DB を作る例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit_kabusys.duckdb")
    # 以降 conn に対して発注／約定等の監査ログ操作が可能

- ニュース RSS の取得（data.news_collector.fetch_rss）
  - 例:
    from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
    for a in articles:
        print(a["id"], a["datetime"], a["title"])

注意事項 / 実装上のポイント
- Look-ahead bias 対策: ほとんどのモジュールは内部で date.today() / datetime.now() を直接参照せず、呼び出し側が target_date を与える設計です。バックテストなどでは必ず過去日時を用いてください。
- OpenAI 呼び出し:
  - gpt-4o-mini を使用（JSON Mode）。API の失敗やパースエラー時はフェイルセーフとしてスコアを 0.0 にする処理があります。
  - テストでは内部の _call_openai_api をモックして外部依存を切り離せます。
- J-Quants クライアント:
  - レートリミット（120 req/min）に合わせた RateLimiter を実装
  - 401 はトークン自動リフレッシュ（1回）してリトライ
  - 429 / 408 / 5xx は指数バックオフでリトライ
- news_collector:
  - SSRF 対策（リダイレクト検査、プライベート IP 拒否）
  - レスポンス上限（10MB）や gzip 対応
  - トラッキングパラメータ除去、記事ID は正規化 URL の sha256（先頭32文字）
- DuckDB の互換性:
  - 一部の操作（executemany に空リストを渡さない等）で DuckDB の挙動に配慮しています

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数読み込み・設定
  - ai/
    - __init__.py
    - news_nlp.py        — ニュース銘柄別センチメント算出
    - regime_detector.py — ETF + マクロ記事の合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント + 保存関数
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETLResult の再エクスポート
    - news_collector.py    — RSS ニュース収集
    - calendar_management.py — マーケットカレンダー管理（営業日判定、calendar_update_job）
    - quality.py           — データ品質チェック
    - stats.py             — 統計ユーティリティ（zscore_normalize）
    - audit.py             — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - その他（strategy / execution / monitoring といったパッケージを想定する __all__）

貢献 / 開発ルール（簡易）
- まずローカルで DuckDB にスキーマ（テーブル）を作成してから ETL を実行してください
- 外部 API 呼び出し（OpenAI / J-Quants / HTTP）はユニットテストでモックしてテストすること
- 機密情報は .env ではなくシークレットマネージャ等で管理するのが望ましい

ライセンス / 注意
- 本 README はソース内のドキュメント文字列を基に作成しています。実行前に各 API キーやパスワードの管理、外部APIの利用規約に従ってください。
- 実際の売買を行う際はリスク管理やバックテストを十分に行ってください。

質問や README に追加したい項目があれば教えてください。必要に応じて実行例や補足（スキーマ定義やテーブル作成 SQL、requirements.txt の候補）も作成します。