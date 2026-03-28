KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP による銘柄センチメント評価、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注／約定トレース）などを含みます。

主な設計方針
- Look-ahead バイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を主要なデータストアとして想定（ローカルファイル化可能）
- 外部 API 呼び出しにはリトライ・レート制御を実装（J-Quants / OpenAI）
- ETL / 品質チェック / 監査ログ等は冪等性を重視して設計

機能一覧
- データ取得（J-Quants クライアント）
  - 日次株価（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダー
  - レートリミッタ・リトライ・トークン自動更新
- ETL パイプライン（差分取得・保存・品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース収集（RSS）と前処理
  - RSS 取得、URL 正規化、トラッキングパラメタ除去、SSRF 対策、前処理
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に送信し ai_scores テーブルへ保存（score_news）
  - レート制限・バッチ処理・レスポンス検証・スコアクリップ付き
- 市場レジーム判定（ETF + マクロニュース + OpenAI）
  - 1321 の 200日移動平均乖離とマクロニュースセンチメントを合成（score_regime）
- 研究用モジュール
  - Momentum / Value / Volatility 等ファクター計算、将来リターン計算、IC（Spearman）等
  - zscore_normalize 等の統計ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル定義、初期化ユーティリティ
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）、環境変数アクセスのラッパ（kabusys.config.settings）

セットアップ手順（開発環境）
- 前提
  - Python 3.10+ を推奨（typing の一部表記を使用）
- リポジトリをクローンして package を編集可能モードでインストール:
  - git clone <repo>
  - cd <repo>
  - pip install -e .  （requirements はプロジェクト側で管理してください）
- 必要な主要依存（最低限の目安）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリのみで多くを実装していますが、実行環境で不足がある場合は適宜追加してください。

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - SLACK_BOT_TOKEN — Slack 通知に使用するボットトークン（プロジェクトで通知実装する場合）
  - SLACK_CHANNEL_ID — 通知先チャンネル ID
  - KABU_API_PASSWORD — kabuステーション API に接続する場合
- 任意 / デフォルトあり
  - KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（テスト用）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みをスキップします
- OpenAI
  - OPENAI_API_KEY — OpenAI を利用する場合に参照（score_news, score_regime は引数 api_key でも渡せます）
- データベースパス（デフォルト）
  - DUCKDB_PATH — data/kabusys.duckdb
  - SQLITE_PATH — data/monitoring.db

（例）.env（抜粋）
- .env.example をプロジェクトに含めている想定です。主なキー:
  - JQUANTS_REFRESH_TOKEN=...
  - OPENAI_API_KEY=...
  - SLACK_BOT_TOKEN=...
  - SLACK_CHANNEL_ID=...
  - KABU_API_PASSWORD=...
  - DUCKDB_PATH=data/kabusys.duckdb

使い方（抜粋サンプル）
- DuckDB 接続を開いて ETL を実行する（簡易例）
  - Python REPL / スクリプト例:
    - import duckdb
    - from datetime import date
    - from kabusys.data.pipeline import run_daily_etl
    - conn = duckdb.connect("data/kabusys.duckdb")
    - result = run_daily_etl(conn, target_date=date(2026,3,20))
    - print(result.to_dict())
- ニュース NLP（指定日）の実行
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - conn = duckdb.connect("data/kabusys.duckdb")
  - count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
- 市場レジームの判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
- 監査ログ DB を初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/kabusys_audit.duckdb")
  - # conn を使って order_logs 等に書き込めるようになります
- テスト時の取り扱い
  - OpenAI 呼び出しや外部ネットワークを伴う関数は内部で分離されており、
    unittest.mock.patch などで _call_openai_api やネットワーク層を差し替え可能です。

主な API（モジュール/関数の要約）
- kabusys.config
  - settings — 各種環境設定（プロパティ経由で取得）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により .env の自動読み込みを無効化可能
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（refresh token から id token を取得）
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) — 日次 ETL を統合実行、ETLResult を返す
- kabusys.data.quality
  - run_all_checks(conn, target_date, ...) — 品質チェックをまとめて実行
- kabusys.data.news_collector
  - fetch_rss(url, source) / preprocess_text(...) 等
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None) — 銘柄ごとの AI スコアを ai_scores に書込
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None) — market_regime にレジーム判定を保存
- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.audit
  - init_audit_schema(conn) / init_audit_db(path) — 監査ログテーブルの初期化

ディレクトリ構成（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: pipeline ETL 用ユーティリティ、クライアントラッパ等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai, research, data の下に各種ユーティリティ／補助モジュールが配置されています

運用上の注意
- OpenAI / J-Quants 利用時は API キーの管理に注意してください（.env / CI シークレット等）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI 等で不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany や INSERT 文はバージョン依存で挙動が異なる箇所があるため、本ライブラリは互換性を考慮した実装になっています（例: executemany へ空リストを渡さない等）。
- ニュース収集は外部 RSS を利用するため SSRF 対策、レスポンスサイズ上限、XML の安全パース等の防御を施していますが、運用時は RSS 元の安定性と法的利用範囲を確認してください。

ライセンス / 貢献
- リポジトリに LICENSE ファイルを用意してください（ここでは省略）。
- 貢献する際は PR にてテストとドキュメントの更新をお願いします。

質問やサンプルコードの追加が必要であれば、あなたのユースケース（ETL の実行頻度、使いたいデータセット、バックテスト連携など）を教えてください。具体的な利用例を元に README へ追記します。