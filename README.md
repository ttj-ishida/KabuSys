KabuSys — 日本株自動売買 / データ基盤ライブラリ
=================================

概要
----
KabuSys は日本株向けのデータ ETL、ニュース NLP、マーケットレジーム判定、ファクター計算、
監査ログ（トレーサビリティ）などを含む内部ライブラリ群です。
主にバックテスト用データパイプラインや研究（Research）、および自動売買システムの基盤処理を目的としています。

主な設計方針
- DuckDB を中心としたローカルデータベースで差分 ETL／品質チェックを実行
- J-Quants API から株価・財務・カレンダーを取得（レート制御・リトライ・トークン自動更新）
- ニュースは RSS から収集し OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを評価
- レジーム判定は ETF(1321) の MA とマクロニュースの LLM スコアを合成
- 監査ログ（signal → order_request → executions）を DuckDB に冪等初期化

機能一覧
---------
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須/既定設定のラッパー（settings オブジェクト）
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から日次株価、財務、マーケットカレンダーを差分取得・保存
  - run_daily_etl で日次 ETL をまとめて実行
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合などの検出
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news への冪等保存（SSRF 対策・サイズ制限）
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI による銘柄別センチメント算出、ai_scores へ保存
- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に保存
- ファクター計算・研究ユーティリティ（kabusys.research）
  - momentum / volatility / value 等のファクター計算、将来リターン、IC、統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマ作成・初期化ユーティリティ
- 汎用統計（kabusys.data.stats）
  - Zスコア正規化など

セットアップ手順
----------------

前提
- Python >= 3.10（typing の | 演算子や型ヒントを利用）
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パースの安全化）
- （任意）その他：requests 等が必要な場合はプロジェクト要件に追加してください

推奨インストール例
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（最低限の例）
   - pip install duckdb openai defusedxml

3. ローカル開発としてパッケージを editable インストールする場合
   - pip install -e .

環境変数 / .env
- 自動ロード: パッケージ起点でプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探し、
  .env → .env.local の順で読み込みます。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（settings で参照されるもの）
  - JQUANTS_REFRESH_TOKEN (必須) : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD (必須) : kabu ステーション API パスワード
  - KABU_API_BASE_URL (任意) : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
  - OPENAI_API_KEY (必須 for AI 呼び出し) : OpenAI API キー（score_news / score_regime で参照）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意) : 通知用
  - DUCKDB_PATH (任意) : デフォルト data/kabusys.duckdb
  - SQLITE_PATH (任意) : 監視 DB 用デフォルト data/monitoring.db
  - PID_FILE_PATH, KILL_FLAG_PATHなど監視用パス
  - KABUSYS_ENV : development / paper_trading / live のいずれか
  - LOG_LEVEL : DEBUG/INFO/...

例（.env）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    KABU_API_PASSWORD=your_kabu_password
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development

使い方（コード例）
------------------

基本的な DuckDB 接続と ETL 実行例
    import duckdb
    from datetime import date
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

ニュース NLP を使って ai_scores を書く（OpenAI API キーが必要）
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込んだ銘柄数: {written}")

市場レジーム判定（OpenAI API キーが必要）
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

監査ログ DB の初期化（別ファイルで監査用 DB を作る場合）
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで signal_events, order_requests, executions 等のテーブルが作成される

設定（settings）の参照例
    from kabusys.config import settings
    print(settings.jquants_refresh_token)
    print(settings.duckdb_path)
    if settings.is_live:
        # 本番設定の分岐処理
        ...

注意点
- OpenAI 呼び出し関数は API の失敗時にフォールバック動作（0.0 返却）やログ出力を行うよう設計されていますが、
  API キーの有無は呼び出し元が保証してください（score_news / score_regime はキー未設定時 ValueError を投げます）。
- DuckDB のバージョン相違（0.10 系など）により executemany の仕様差異があるため、ETL 内では空リストバインド回避の工夫があります。
- .env の自動読み込みはプロジェクトルートを基準とするため、テストや外部から直接パッケージを import する場合に想定と異なる挙動が出ることがあります。
  その場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するか明示的に os.environ をセットしてください。

ディレクトリ構成（抜粋）
-----------------------
（ルート: src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                    — 環境設定の読み込み/Settings
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースのセンチメント評価（OpenAI）
    - regime_detector.py         — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ロジック
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の再エクスポート
    - news_collector.py          — RSS 収集処理
    - calendar_management.py     — マーケットカレンダー管理 / 営業日判定
    - quality.py                 — データ品質チェック
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログ（テーブル作成 / init）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算 (momentum/value/volatility)
    - feature_exploration.py     — 将来リターン、IC、統計サマリー

トラブルシューティング / よくある問題
-------------------------------------
- ValueError: 環境変数 'JQUANTS_REFRESH_TOKEN' が設定されていません
  → .env を準備するか環境変数をセットしてください。

- OpenAI まわりで JSON パース失敗や API エラーが出る
  → レート制限やネットワーク、モデルレスポンスの不整合が原因のことがあります。ログを確認し、
    API キー・モデル名・ネットワークを確認してください。ライブラリ側はリトライとフォールバックを実装しています。

- DuckDB に書き込めない / executemany のエラー
  → DuckDB のバージョン差異（特に 0.10 周辺）を疑ってください。pip で duckdb を最新安定版に合わせることを推奨します。

ライセンス・貢献
----------------
- この README ではライセンス情報は含めていません。実際のリポジトリでは LICENSE ファイルを参照してください。
- 貢献する場合は機能追加前に設計意図（Look-ahead バイアス回避、冪等化ポリシー等）を理解の上、単体テスト・統合テストを追加してください。

付記
----
この README はソースコードの docstring・コメントに基づいて作成しています。より詳細な設計資料（DataPlatform.md, StrategyModel.md 等）がある場合は併せて参照してください。質問や追加のドキュメント化が必要であれば教えてください。