KabuSys — 日本株自動売買プラットフォーム（README）
=====================================

概要
----
KabuSys は日本株のデータ取得（J-Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースセンチメント（OpenAI）によるスコアリング、監査ログ（発注 / 約定トレース）などを含む、自動売買／リサーチ基盤のコアライブラリ群です。モジュール化されており、ETL バッチ、リサーチ処理、AI によるニュース評価、マーケットレジーム判定などの機能を提供します。

主な機能
-------
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得・ページネーション対応
  - レートリミット管理・リトライ・トークン自動リフレッシュ
- ETL パイプライン
  - run_daily_etl 等の差分更新（backfill サポート）、品質チェックの統合
  - ETL 実行結果を ETLResult として返す
- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付整合性チェックを実装
- ニュース収集・前処理
  - RSS 取得（SSRF / Gzip / サイズ制限対策）、トラッキングパラメータ除去、記事 ID 生成
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM で評価し ai_scores に書き込み
  - 市場マクロニュースから市場レジーム（bull/neutral/bear）を判定
- 研究（Research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルの DDL と初期化機能（冪等）
  - order_request_id を冪等キーとして二重発注防止を支援

前提・要件
----------
- Python 3.10+（型アノテーションや union 型を使用）
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI API、RSS ソース）
- J-Quants / OpenAI / kabuステーション 等の API キー

環境変数（重要）
----------------
以下は本パッケージで参照される主要な環境変数です。プロジェクトルートの .env / .env.local から自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI 呼び出し時に必要（score_news / score_regime の引数で上書き可）

任意 / デフォルトあり:
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
- LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（"1"）

セットアップ手順
----------------
1. リポジトリをクローン／配置
   - コードベースは src/kabusys 配下にあります。プロジェクトルート（.git または pyproject.toml がある場所）に .env を置くと自動的に読み込まれます。

2. Python 仮想環境と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）

3. 環境変数を設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 例:
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-xxxx
     SLACK_BOT_TOKEN=xoxb-xxxx
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=yourpassword

   - 自動ロードを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB データベースの準備
   - デフォルトは data/kabusys.duckdb。フォルダがなければ作成されます。
   - 監査ログ専用 DB を初期化する場合は kabusys.data.audit.init_audit_db を使用します（下記参照）。

基本的な使い方（コード例）
------------------------

- DuckDB 接続を開く
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（株価・財務・カレンダー・品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日を対象

- ニュースセンチメントを計算して ai_scores に保存
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - count = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY は環境変数か引数で指定可

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
  - from kabusys.ai.regime_detector import score_regime
  - res = score_regime(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（監査テーブルを含む専用 DB を生成）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- ファクター計算（研究用途）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - mom = calc_momentum(conn, target_date=date(2026,3,20))

- カレンダー関連ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

注意点 / 実運用上の留意事項
------------------------
- OpenAI 呼び出しは gpt-4o-mini を想定しており、JSON Mode を期待するプロンプト設計になっています。API エラー時はフェイルセーフ（スコア=0.0 など）で継続する設計です。
- J-Quants の API レート制限（120 req/min）に合わせて内部でレートリミットを設けていますが、大量同時実行時は注意してください。
- DuckDB に対する executemany の空リスト制約など実装に合わせた取り扱いがあるため、スキーマ／バージョンに注意してください（コメントやコードに互換性注意点あり）。
- datetime.today()/date.today() によるルックアヘッドバイアスを避ける設計が多くのモジュールで採用されています。バックテスト等で使用する際は target_date の明示を推奨します。

ディレクトリ構成（主要ファイル）
------------------------------
（抜粋 — 実ファイルは src/kabusys/ 配下）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理（.env 自動読み込み、settings）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメントスコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save 系）
    - pipeline.py                  — ETL パイプライン・run_daily_etl 等
    - etl.py                       — ETLResult のエクスポート
    - news_collector.py            — RSS 取得・記事前処理
    - quality.py                   — データ品質チェック（check_missing_data 等）
    - stats.py                     — zscore_normalize 等統計ユーティリティ
    - calendar_management.py       — 市場カレンダー / 営業日判定 / calendar_update_job
    - audit.py                     — 監査ログ DDL・初期化（init_audit_schema, init_audit_db）
  - research/
    - __init__.py
    - factor_research.py           — Momentum/Value/Volatility 等ファクター計算
    - feature_exploration.py       — 将来リターン calc_forward_returns, IC, rank, summary
  - research/*                      — 研究用ユーティリティ群
  - (その他: strategy, execution, monitoring という公開名は __init__ で想定されるが本コードベースでは data/research/ai が中心)

開発・テストのヒント
--------------------
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml が存在する場所）を基準に行われます。テストで環境変数制御が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効化してください。
- OpenAI / J-Quants 呼び出しは外部 API を使うため、ユニットテストでは各モジュールの _call_openai_api や jquants_client._request 等をモックすると安定します。
- DuckDB はインメモリ(":memory:") でも初期化可能なため、テストでは監査 DB を :memory: で作成して処理を検証できます。

ライセンス・貢献
----------------
- 本 README はコードベース説明を目的としたドキュメントです。実運用・配布時は LICENSE ファイルをプロジェクトに追加してください。
- バグ修正や機能追加は Pull Request を歓迎します。API キーや機密情報をコミットしないでください。

補足（問い合わせ）
------------------
- 実行時のエラーや API 認証まわりの問題は、まず設定（.env）とネットワークアクセス、依存パッケージのバージョンを確認してください。
- 具体的なコードの使い方で迷った点があれば、使いたいユースケース（例: ETL のスケジュール方法、OpenAI のレスポンス処理）を教えてください。実例を交えて補足します。