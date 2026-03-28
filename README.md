KabuSys
=======

日本株向けの自動売買／データ基盤ライブラリのリポジトリ（読み取り専用ドキュメント）。
本 README はローカル開発や簡易運用開始のための概要・セットアップ手順・代表的な使い方をまとめたものです。

ポイント要約
- 日本株のデータ ETL、ニュース収集・NLP（OpenAI 利用）、市場レジーム判定、
  ファクター計算・リサーチユーティリティ、監査ログ（発注追跡）などを含むモジュール群。
- データ保存は DuckDB（分析 DB）を中心に設計。J-Quants API からの差分取得をサポート。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価やマクロセンチメントを実装。
- 設定は環境変数 / .env ファイル経由で管理。自動読み込み機能あり。

主な機能
- data
  - ETL パイプライン（run_daily_etl）: 市場カレンダー、株価日足、財務データの差分取得・保存・品質チェック。
  - J-Quants クライアント: ページネーション・レートリミット・トークン自動リフレッシュ付き。
  - カレンダー管理（営業日判定、next/prev_trading_day 等）。
  - ニュース収集（RSS → raw_news）: SSRF 対策、トラッキング除去、前処理、冪等保存。
  - データ品質チェック（欠損・重複・スパイク・日付不整合）。
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ。
  - 統計ユーティリティ（zscore 正規化等）。
- ai
  - ニュース NLP（銘柄ごとのセンチメントを ai_scores に保存する score_news）。
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成 -> market_regime に書込む score_regime）。
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）。
  - 特徴量探索（将来リターン計算 / IC / 統計サマリ / ランク関数）。
- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルート検出）と Settings ラッパー。

必要条件（推奨）
- Python 3.10 以上（型ヒントの '|' 表記を使用しているため）
- 必須ライブラリ（最小限、プロジェクトごとに requirements.txt を用意してください）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース など）

セットアップ手順（開発環境・ローカル実行向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 環境を作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （必要なら pytest / mypy / black 等の開発ツールを追加）
4. 環境変数設定
   - プロジェクトルートに .env を置くと自動で読み込みます（優先順: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（例: .env に書く）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO
   - .env のパースはシェル風の export KEY=VAL, クォート、コメントを考慮します。
5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

簡単な使い方（コード例）
- DuckDB 接続を作って日次 ETL を実行する
  - Python スクリプト例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントを算出して ai_scores に保存（OpenAI API キー必要）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"written: {written}")

- 市場レジーム判定を実行して market_regime に書き込む
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB を初期化する（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って order_requests 等を扱えるようになる

設定詳細
- 自動 .env 読み込み:
  - プロジェクトルートは __file__ の親から上に向かって .git または pyproject.toml を探して決定します。見つからない場合は自動読み込みをスキップします。
  - 読み込み順序: .env → .env.local（.env.local は上書き）
  - OS 環境変数は保護され、.env の上書き対象にはなりません（ただし .env.local は override=True のため上書き可能）。
- Settings API:
  - kabusys.config.settings を通してアプリ設定にアクセス可能（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live 等）。

よく使う関数 / エントリポイント
- data.pipeline.run_daily_etl(conn, target_date, ...) : 日次 ETL（カレンダー→株価→財務→品質チェック）
- data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl : 個別 ETL
- data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar : API 取得
- data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar : DuckDB 保存（冪等）
- data.news_collector.fetch_rss / preprocess_text : RSS 取得・前処理
- ai.news_nlp.score_news(conn, target_date) : ニュース NLP スコアリング（ai_scores へ書込）
- ai.regime_detector.score_regime(conn, target_date) : 市場レジーム判定（market_regime へ書込）
- data.audit.init_audit_db / init_audit_schema : 監査スキーマ初期化

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py                (パッケージ公開)
  - config.py                  (環境変数 / 設定管理)
  - ai/
    - __init__.py
    - news_nlp.py              (ニュースセンチメント)
    - regime_detector.py       (市場レジーム判定)
  - data/
    - __init__.py
    - pipeline.py              (ETL パイプライン、ETLResult)
    - jquants_client.py        (J-Quants API クライアント + DuckDB 保存)
    - calendar_management.py   (市場カレンダー管理)
    - news_collector.py        (RSS ニュース収集)
    - quality.py               (データ品質チェック)
    - stats.py                 (zscore など統計ユーティリティ)
    - audit.py                 (監査ログスキーマ初期化)
    - etl.py                   (ETL インターフェース再エクスポート)
  - research/
    - __init__.py
    - factor_research.py       (ファクター計算: momentum/value/volatility)
    - feature_exploration.py   (forward returns / IC / summary / rank)
  - research/__init__.py
- tests/                       （テストがあれば配置）

開発・運用上の注意
- Look-ahead bias（将来情報の参照）を避ける設計思想:
  - 多くの関数は内部で date.today() を参照せず、target_date を明示的に受け取るようにしています。バックテストや再現性のある処理では target_date を必ず指定してください。
- OpenAI / J-Quants の API 呼び出しはネットワークエラーやレート制限に対するリトライを組み込んでいますが、API キーは安全に保管してください。
- ETL は部分失敗に強い設計（各ステップで例外をキャッチして継続）ですが、品質チェック結果（errors / quality_issues）を必ず確認して運用方針を決めてください。
- news_collector は SSRF 防御、レスポンスサイズ制限、XML パースの安全化（defusedxml）を行っています。

サンプル .env（例）
- .env.example（プロジェクトルートに置いて利用してください）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C0123456789
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

テスト / 静的解析
- pytest 等でユニットテストを実行してください（tests ディレクトリがある場合）。
- 外部 API 呼び出しはモックしてテストすることを推奨します（コード内にも unittest.mock.patch を使った差し替えを想定した実装あり）。

ライセンス / コントリビューション
- 本 README はコードを読みやすくまとめるための補助ドキュメントです。実際のライセンス表記やコントリビューション規約（CONTRIBUTING.md）がある場合はリポジトリルートのファイルを参照してください。

問い合わせ
- 実運用や拡張を行う際は、J-Quants / OpenAI の利用制限・コスト、証券会社 API（kabu ステーションなど）の安全性、発注ロジックのリスク管理を十分に検討してください。

以上。README に記載したコマンドや使用例はローカル開発向けの最小例です。運用環境での監査、権限、秘密情報管理、障害対策は別途整備してください。