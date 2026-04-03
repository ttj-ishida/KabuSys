KabuSys
=======

概要
----
KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
J-Quants からのデータ取得（株価・財務・マーケットカレンダー）、RSS ニュース収集と NLP によるニュースセンチメント評価、ファクター計算（リサーチ）、監査ログ・発注監視、そして市場レジーム判定などの機能を持ち、ETL パイプラインと分析 / 監視処理を提供します。

主な特徴
--------
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- DuckDB を使った ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ニュース収集（SSRF対策・トラッキングパラメータ除去・冪等保存）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（ai.score_news）と市場レジーム判定（ai.score_regime）
- ファクター計算・特徴量探索（momentum / volatility / value / forward returns / IC 等）
- 監査ログ（signal → order_request → executions）テーブルの初期化ユーティリティ
- 設定管理（.env 自動読み込み、環境変数ベースの Settings）

セットアップ
-----------

前提
- Python 3.10+（typing | 機能に依存）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

必須パッケージ（代表例）
- duckdb
- openai
- defusedxml

インストール（開発環境）
- リポジトリルート（pyproject.toml がある場所）で以下を実行します:
  - pip install -e .[dev] など（setup/pyproject に合わせて）  
  - または最低限: pip install duckdb openai defusedxml

環境変数 / .env
- プロジェクトルートに .env / .env.local を置くと、自動で読み込まれます（CWD ではなくパッケージ位置からプロジェクトルートを探索します）。
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（必須/任意）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for AI 関連関数): OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_PASSWORD (必須 if using kabu API): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): デフォルト "http://localhost:18080/kabusapi"
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (任意): LINE 通知用
- DUCKDB_PATH (任意): デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (任意): 監視用 SQLite データベース、デフォルト "data/monitoring.db"
- PID_FILE_PATH, KILL_FLAG_PATH 等の監視設定
- KABUSYS_ENV: "development" / "paper_trading" / "live"（デフォルト development）
- LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"

使い方（代表例）
----------------

1) 設定と DuckDB 接続の準備
- Python から Settings を参照して DB パス等を取得できます。

例:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())  # ETLResult の要約

3) ニュースセンチメントスコアを計算して ai_scores に書き込む
  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

4) 市場レジーム（bull/neutral/bear）を計算して market_regime に保存
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))

- OpenAI キーは api_key 引数でも渡せます（テストや複数キー運用時に便利）。
- API 呼び出しの失敗は多くの場合フェイルセーフで処理継続（スコアを 0 にフォールバック）しますが、キー未設定は ValueError を送出します。

5) 監査ログ用 DB の初期化（監査専用 DuckDB を作る）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # テーブル群が作成されます（UTC タイムゾーンに固定）

よく使うモジュール / 関数
- kabusys.config.settings: 環境設定取得
- kabusys.data.jquants_client: J-Quants API 操作用（fetch_*/save_*）
- kabusys.data.pipeline.run_daily_etl: 日次 ETL エントリポイント
- kabusys.data.news_collector.fetch_rss: RSS 取得ユーティリティ
- kabusys.data.quality.run_all_checks: データ品質チェック
- kabusys.ai.news_nlp.score_news: ニュース NLP のスコアリング
- kabusys.ai.regime_detector.score_regime: 市場レジーム判定
- kabusys.research.*: ファクター計算 / 特徴量探索ユーティリティ

注意事項 / 運用上のポイント
--------------------------
- OpenAI を使用する処理（score_news / score_regime）は API コスト・レート制限・レスポンスの不確実性を伴います。実運用時はレート制御・エラーハンドリング設定に注意してください。
- J-Quants の API レートは守られるよう実装済みですが、ID トークンの扱いには注意（get_id_token と内部キャッシュを使用）。
- DuckDB のスキーマ（raw_prices / raw_financials / raw_news 等）が前提です。ETL を初めて動かす場合はスキーマ初期化手順（data.schema 相当）やマイグレーションが必要です（本コードベースには監査スキーマ初期化ユーティリティを含む）。
- Look-ahead bias（将来情報参照）を防ぐ設計が各所に施されています（target_date の扱い、fetched_at 記録など）。バックテストや解析時は target_date を明示して使用してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テスト環境等で自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                # 環境設定・.env ローダ
- ai/
  - __init__.py
  - news_nlp.py            # ニュース NLP（score_news）
  - regime_detector.py     # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      # J-Quants API クライアント（fetch/save）
  - pipeline.py           # ETL パイプライン（run_daily_etl 等）
  - etl.py                # ETLResult 再エクスポート
  - news_collector.py     # RSS 収集（fetch_rss 等）
  - quality.py            # データ品質チェック
  - stats.py              # 統計ユーティリティ（z-score 正規化）
  - calendar_management.py# マーケットカレンダー管理（is_trading_day など）
  - audit.py              # 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py    # モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py# 将来リターン・IC・統計サマリー等

ライセンス / コントリビューション
--------------------------------
- 本 README はコードベースに基づく簡易ドキュメントです。実プロジェクトへの適用時は LICENSE や CONTRIBUTING ガイドラインを確認してください。

付記（参考）
-------------
- 自動読み込みされる .env のパースはシェルの export 形式やクォートを考慮しており、コメント処理やエスケープもサポートします。
- AI 関連処理はテスト容易性のため内部 API 呼び出し関数をモック差し替え可能になっています（ユニットテストでの置き換えを想定）。

必要であれば、README に含めるサンプル .env.example、初期スキーマ作成手順（raw_* テーブル DDL）、あるいは具体的なデプロイ / systemd / supervisor 用の実行例も作成します。どの情報を追加しましょうか？