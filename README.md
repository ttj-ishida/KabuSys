# KabuSys

日本株向け自動売買 / データプラットフォームユーティリティ群

バージョン: 0.1.0

---

概要
- KabuSys は日本株のデータ取り込み（ETL）、品質チェック、ニュース収集、AI を使ったニュースセンチメントや市場レジーム判定、リサーチ用ファクター計算、監査ログ (audit) などを備えた内部ツール群です。
- DuckDB をデータレイクとして利用し、J-Quants API からのデータ取得、RSS ニュース収集、OpenAI（gpt-4o-mini）による NLP 評価、ETL の差分更新／冪等保存、データ品質チェックが主な機能です。
- バックテスト/リサーチ用の機能（ファクター計算、IC 計算、前方リターン計算）と、運用向けの監査ログ／監視用設定も含みます。

主な機能一覧
- データ取得・ETL
  - J-Quants から株価日足、財務データ、マーケットカレンダーを差分取得（ページネーション、レートリミット、リトライ、トークン自動リフレッシュ対応）
  - DuckDB へ冪等保存（ON CONFLICT / upsert 相当）
  - 日次 ETL の統合エントリポイント（run_daily_etl）
- データ品質
  - 欠損、スパイク、重複、将来日付や非営業日の検出（QualityIssue を返却）
  - 全チェック一括実行（run_all_checks）
- ニュース収集 / 前処理
  - RSS からニュース取得、テキスト前処理、SSRF 対策、トラッキングパラメータ除去、記事 ID は正規化 URL の SHA-256（先頭 32 文字）で冪等化
- AI（OpenAI）連携
  - ニュースごとの銘柄センチメントをバッチで取得し ai_scores に保存（score_news）
  - マクロニュース + ETF（1321）200 日 MA 乖離を合成して市場レジーム判定（score_regime）
  - API 呼び出しはリトライ／バックオフ／フェイルセーフ（失敗時は中立スコア等）実装
- Research（リサーチ用）
  - モメンタム / ボラティリティ / バリュー のファクター計算（prices_daily / raw_financials 参照）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Z スコア正規化ユーティリティ
- 監査（Audit）
  - signal_events / order_requests / executions を含む監査スキーマの初期化・接続ユーティリティ（init_audit_db / init_audit_schema）
- 設定管理
  - 環境変数および .env(.local) 自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - 多数の設定（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, DUCKDB_PATH, KABU_API_PASSWORD, PAPER_FILL_MODE など）

設計・品質に関するポイント（抜粋）
- Look-ahead bias を避ける実装（target_date より未来データを参照しない、datetime.today() を直接参照しない関数設計）
- 冪等性（DB への保存は upsert、監査の order_request_id は冪等キー）
- API 呼び出しはレート制御 / リトライ / トークンリフレッシュ対応
- ニュース収集は SSRF 対策・XML 安全パーサ（defusedxml）を使用
- テスト容易性のため、OpenAI 呼び出しなどの内部関数をモック差替え可能

セットアップ手順（開発環境向け）
1. 前提
   - Python 3.10 以上
   - DuckDB、OpenAI SDK、defusedxml などの依存ライブラリが必要

2. リポジトリをクローン
   - git clone <repo-url>

3. 仮想環境を準備
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際の requirements.txt があればそれを使用してください:
   - pip install -r requirements.txt

5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env を作成すると自動で読み込まれます（.env.local は .env を上書きする形で読み込み）。
   - 自動読み込みを無効にするには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - DUCKDB_PATH: データ格納用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE: paper trading の埋めモード（instant | partial | never | reject）
   - PID_FILE_PATH / KILL_FLAG_PATH / その他監視閾値系の設定
   - KABUSYS_ENV: development | paper_trading | live
   - LOG_LEVEL: DEBUG | INFO | ...

6. データベース初期化（監査用）
   - 監査ログ専用 DB を初期化する例:
     - Python から:
       from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

基本的な使い方（コード例）
- 日次 ETL 実行（DuckDB 接続が必要）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントスコア（OpenAI 必須）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
    print(f"written {n_written} scores")

- 市場レジーム判定（ETF 1321 の MA とマクロニュースの合成）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- Research API（ファクタ計算）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    momentum = calc_momentum(conn, date(2026, 3, 20))
    # momentum は各銘柄の辞書リスト

運用上の注意
- OpenAI 呼び出しは課金が発生するため、テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替えてください。
- J-Quants トークンは .env へ保存するか CI のシークレット機能を利用してください。
- ETL 実行時は DuckDB ファイルのバックアップやロック競合に注意してください。
- news_collector は外部 URL を取得するため SSRF ガードやタイムアウトの設定を厳格に保つことを推奨します。

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env 自動ロードと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py       — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py       — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS ニュース収集
    - calendar_management.py — マーケットカレンダー管理
    - quality.py        — データ品質チェック
    - stats.py          — 共通統計ユーティリティ（zscore_normalize）
    - audit.py          — 監査ログスキーマ初期化
    - etl.py            — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - research/* （他ユーティリティ）
  - その他:
    - strategy/, execution/, monitoring/ など（パッケージとして __all__ に含まれます）

テストとモックのポイント
- OpenAI 呼び出し部分（_call_openai_api）はモック差し替えしやすく実装されています。
- news_collector._urlopen や regime_detector/news_nlp の OpenAI 呼び出しなどはテストでパッチ可能です。
- .env 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テストで環境汚染を防ぐために便利です）。

ライセンス・貢献
- （ここにライセンス情報や貢献方法、CONTRIBUTING.md への参照を追記してください）

問い合わせ・追加情報
- 実装方針や各モジュールの詳しい振る舞いはソース内の docstring / コメントに詳述されています。特に Look-ahead bias、冪等性、リトライ設計などは各モジュール冒頭に記載していますので参照してください。

以上。README の内容やサンプルを特定の運用フロー（例: systemd サービス化、Docker 化、CI 実行コマンド）向けに拡張したい場合は、利用環境や要件を教えてください。