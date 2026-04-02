KabuSys — 日本株自動売買プラットフォーム（README）
概要
KabuSys は日本株のデータ基盤・研究・AI スコアリング・ETL・監査ログなどを備えた自動売買支援ライブラリです。J-Quants からのデータ取り込み、DuckDB を用いたデータ保存・集計、OpenAI を用いたニュースセンチメント評価、ファクター計算・特徴量探索、監査ログ（オーダー／約定のトレーサビリティ）など、実運用・研究に必要な各コンポーネントをモジュール化して提供します。

主な特徴（機能一覧）
- 環境変数・設定管理
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（例: JQUANTS_REFRESH_TOKEN 等）
- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、カレンダー等）
  - 差分取得 / ページネーション対応 / レートリミット・リトライ実装
  - ETL パイプライン（run_daily_etl 等）
  - 品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集・前処理
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、gzip 対応）
  - raw_news / news_symbols への冪等保存ロジック
- AI ベースの NLP スコアリング
  - ニュースセンチメント分析（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（ETF の MA とマクロニュースを合成する kabusys.ai.regime_detector.score_regime）
  - OpenAI（gpt-4o-mini）を JSON mode で利用、堅牢なリトライ/フォールバック
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算（kabusys.research）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - zscore_normalize 等の共通統計ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
  - すべて UTC タイムスタンプで保存、冪等な初期化をサポート
- 運用監視向け設定（PID ファイル、CPU/メモリ/ディスク閾値 等）

セットアップ手順
前提
- Python 3.9+（typing, Path 型の使用や型注釈のため）を想定
- DuckDB、OpenAI SDK、defusedxml 等が必要

推奨手順（例）
1. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. パッケージのインストール
   # プロジェクトルート（setup.cfg / pyproject.toml がある場所）で:
   pip install -e . 
   # もしパッケージ化されていない場合は最低限以下をインストールしてください:
   pip install duckdb openai defusedxml

3. 環境変数の設定 (.env)
   プロジェクトルートに .env を作成すると自動で読み込まれます（.env.local は .env の上書き）。
   自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定します（テスト等で利用）。

   必要な環境変数（主要）
   - JQUANTS_REFRESH_TOKEN    （必須）: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD        （必須）: kabu API のパスワード（発注等を使う場合）
   - SLACK_BOT_TOKEN          （必須）: Slack 通知を使う場合
   - SLACK_CHANNEL_ID         （必須）: Slack チャンネル ID
   - OPENAI_API_KEY           （必須）: OpenAI を使う機能（ニューススコア等）で必要
   - DUCKDB_PATH              （任意）: デフォルト data/kabusys.duckdb
   - SQLITE_PATH              （任意）: デフォルト data/monitoring.db
   - KABUSYS_ENV              （任意）: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL                （任意）: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   .env の簡易例 (.env.example)
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

使い方（簡単なコード例）
※ 以下は基本的な呼び出し例です。実運用ではログ設定、エラーハンドリング、認証トークン管理などを適切に行ってください。

1) DuckDB に接続して日次 ETL を実行する
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

2) ニュースセンチメント（AI）で銘柄ごとにスコアを作成する
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.ai import score_news  # kabusys/ai/__init__.py で score_news をエクスポート

   conn = duckdb.connect(str(settings.duckdb_path))
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"scored {written} codes")

   - OpenAI API キーを引数で渡すことも可能: score_news(conn, date, api_key="...")

3) 市場レジーム判定を実行する
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で指定

4) 監査ログテーブルを初期化する（別 DB を使う場合）
   from pathlib import Path
   import duckdb
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db(Path("data/audit.duckdb"))
   # これで signal_events/order_requests/executions 等が作成されます

5) J-Quants データ取得を個別に使う（テストやデバッグ用）
   from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を利用
   quotes = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))

運用上の注意・実装上のポイント
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基に行われます。テスト実行時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI を利用する関数はリトライとフォールバック（失敗時は中立スコア 0.0）を備えています。テストでは内部の _call_openai_api をモックして安定化させてください。
- J-Quants クライアントはレート制限（120 req/min）や 401 自動リフレッシュ、指数バックオフを組み込んであります。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、該当箇所では空チェックを行っています。
- 監査ログ（audit）テーブルは削除しない前提で設計されています（ON DELETE RESTRICT 等）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                      (パッケージ宣言、version)
  - config.py                        (環境変数・設定管理)
  - ai/
    - __init__.py                    (score_news を公開)
    - news_nlp.py                    (ニュースセンチメント：score_news 等)
    - regime_detector.py             (市場レジーム判定：score_regime)
  - data/
    - __init__.py
    - jquants_client.py              (J-Quants API クライアント、保存処理)
    - pipeline.py                    (ETL パイプライン、run_daily_etl 等)
    - etl.py                         (ETLResult の再エクスポート)
    - calendar_management.py         (市場カレンダー管理・営業日判定)
    - stats.py                       (zscore_normalize 等統計ユーティリティ)
    - quality.py                     (データ品質チェック)
    - news_collector.py              (RSS 収集・前処理)
    - audit.py                       (監査ログテーブル定義・初期化)
  - research/
    - __init__.py
    - factor_research.py             (モメンタム/バリュー/ボラティリティ等)
    - feature_exploration.py         (将来リターン / IC / 統計サマリー)
  - (strategy/, execution/, monitoring/ 等のサブパッケージも想定されますが、
     上記コードベースには一部コンポーネントが含まれます)

開発・テスト
- OpenAI 呼び出しや外部 HTTP 呼び出しはモックしやすいように内部関数でラップされています（例: _call_openai_api, _urlopen 等）。ユニットテストではこれらを patch してください。
- .env.local をテスト用に用意すると実行環境ごとに上書きが可能です。
- DuckDB を ":memory:" で使い、init_audit_db(":memory:") 等でテスト用 DB を作成できます。

ライセンス / コントリビューション
- (ここにはプロジェクトで使用するライセンスや貢献手順を記載してください。)

最後に
この README はコードベースを参照して要点をまとめたものです。実運用前に各設定値・秘密情報の扱い（環境変数管理・シークレットのローテーション）、テスト・監査ポリシーを確立してください。質問や補足が必要であれば、実行したいユースケース（ETL のスケジュール、バックテスト/実運用、API キーの管理）をお知らせください。