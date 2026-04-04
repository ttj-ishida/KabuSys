KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株向けのデータパイプライン、ニュースNLP、ファクター研究、監査ログ等を含む技術基盤ライブラリです。J-Quants API からのデータ取得（株価・財務・カレンダー）、RSS ニュース収集、OpenAI を用いたニュースセンチメント解析と市場レジーム判定、DuckDB ベースの ETL／品質チェック、監査テーブル初期化などを提供します。バックテスト／研究環境と本番発注ロジックを分離して設計されています。

主な機能
--------
- データ収集 / ETL
  - J-Quants から株価日足・財務情報・マーケットカレンダーを差分取得して DuckDB に保存（ページネーション・レート制御・自動トークンリフレッシュ対応）
  - ETL の差分計算・バックフィル機能および品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_update_job による JPX カレンダーの夜間更新

- ニュース収集 / NLP
  - RSS フィード収集（SSRF/トラッキングパラメータ対策、XML 防御）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（ai_scores テーブルへ書込）
  - マクロニュース＋ETF（1321）MA200乖離を組み合わせた市場レジーム判定（bull/neutral/bear）

- 研究用ユーティリティ
  - ファクター計算（モメンタム／バリュー／ボラティリティ等）
  - 将来リターン計算、IC（Spearman）やファクター統計サマリー、Zスコア正規化

- 監査・トレーサビリティ
  - signal_events / order_requests / executions を備えた冪等設計の監査スキーマ生成と専用 DB 初期化ユーティリティ

- 設定管理
  - .env / .env.local / OS 環境変数から設定を読み込む（パッケージ内で自動ロード。無効化フラグあり）
  - 環境に応じた挙動切替（development / paper_trading / live）・ログレベル検証

セットアップ手順
---------------
1. 必要環境
   - Python 3.10 以上（型注釈に | を使用）
   - pip

2. 依存ライブラリのインストール（例）
   - 必要に応じて仮想環境を作成してください。
   - 最小の例:
     pip install duckdb openai defusedxml

   - 実運用で必要な追加ライブラリ（例）:
     - requests 等を好む場合は任意で導入できますが、本実装は urllib を使用しています。

3. 環境変数 / .env
   - プロジェクトルートの .env（または .env.local）に必要な設定を置くと、自動で読み込まれます。
   - 自動ロードを無効化したい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 主な環境変数（Settings から抜粋）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API 用パスワード（必須）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が利用）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（プロセス監視設定）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

4. データディレクトリ作成
   - DUCKDB_PATH の親ディレクトリ等を作成してください（init 関数の多くは自動で親ディレクトリを作成しますが、念のため）。

基本的な使い方（サンプル）
-------------------------

- DuckDB 接続の生成
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（株価・財務・カレンダーの差分 ETL + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントのスコアリング（OpenAI 必須）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
  print(f"書き込み銘柄数: {n}")

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB 初期化（専用 DB）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルへアクセス

- カレンダーバッチ更新（J-Quants から）
  from kabusys.data.calendar_management import calendar_update_job
  calendar_update_job(conn)

ログ設定
--------
このライブラリは標準 logging を使用します。スクリプト側で logging.basicConfig(level=...) やハンドラ設定を行ってください。LOG_LEVEL 環境変数（Settings.log_level）も検証されます。

よくある実行フロー（例）
-----------------------
1. 夜間バッチ（cron 等）
   - run_daily_etl を実行してデータを取り込む
   - calendar_update_job を併用（pipeline 内で calendar_etl が最初に実行されます）

2. 朝（取引前）
   - score_news -> ai_scores テーブルにメタデータ作成
   - calc_* 関数（research）でファクターを算出、シグナル生成ロジックに入力

3. 発注 / 監視
   - 監査テーブル（order_requests / executions）を使って発注フローをトレース
   - 実運用では kabu API 呼び出し部分（execution モジュール）と統合して発注

ディレクトリ構成
----------------
以下はコードベース内の主要ファイル／モジュール（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      : 環境変数・.env ロード設定
  - ai/
    - __init__.py
    - news_nlp.py                   : ニュースセンチメントスコアリング（OpenAI）
    - regime_detector.py            : ETF + マクロで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             : J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                   : ETL パイプライン（run_daily_etl 等）
    - etl.py                        : ETL 型／再エクスポート（ETLResult）
    - stats.py                      : 共通統計ユーティリティ（zscore_normalize）
    - quality.py                    : データ品質チェック
    - news_collector.py             : RSS ニュース収集・正規化
    - calendar_management.py        : 市場カレンダー管理
    - audit.py                      : 監査ログ（監査スキーマ初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py            : モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py        : 将来リターン・IC・統計サマリー
  - research/...                     : 研究ユーティリティ群
  - (そのほか) strategy/, execution/, monitoring/ の公開は __all__ に含まれるが、この抜粋では data/ ai/ research/ に実装が集中

注意事項 / 設計上のポイント
--------------------------
- Look-ahead bias を避ける設計:
  - 各モジュールは内部で date.today() を不用意に参照せず、target_date を明示的に受け取って処理します。
  - prices_daily のクエリは target_date 未満 / 以前等で厳密に制約を付けています。

- フェイルセーフ設計:
  - OpenAI 呼び出しや外部 API 失敗時は例外を投げずにフォールバック（0.0 など）する箇所があり、パイプライン全体の継続を優先します。
  - ETL は各ステップで個別に例外処理し、可能な範囲で処理を継続して結果を返します。

- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE / INSERT ... ON CONFLICT を用いて冪等に設計されています（重複挿入抑止）。

- セキュリティ考慮:
  - news_collector は SSRF 対策・受信サイズ制限・XML の安全パーサを用いています。
  - jquants_client は 401 時のトークン自動リフレッシュやレート制御を備えています。

ライセンス・貢献
----------------
- 本サンプルコードにはライセンス記載がありません。実運用・公開時には適切なライセンスを付与してください。
- バグ報告や改善提案は issue / PR で行ってください（リポジトリ運用ルールに従うこと）。

補足（参考コマンド）
-------------------
- pip による依存インストール例:
  pip install duckdb openai defusedxml

- 環境例（.env）
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=your_kabu_password
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

以上。必要があれば README にサンプルコードや CI / Docker 化手順、より詳細な環境変数一覧（.env.example 形式）を追加します。どの部分を拡張したいか教えてください。