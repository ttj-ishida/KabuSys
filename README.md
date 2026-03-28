# KabuSys

日本株向け自動売買・データプラットフォームライブラリ

概要
- KabuSys は日本株のデータ取得（J‑Quants）、ETL、データ品質チェック、ニュース収集・NLP、リサーチ（ファクター計算）、監査ログ（オーダー／約定追跡）などを組み合わせた自動売買基盤向けの Python モジュール群です。
- DuckDB をデータ層に使用し、OpenAI（gpt-4o-mini）を用いたニュース/マクロセンチメント評価機能も備えます。
- モジュールはバックテストや運用バッチでの利用を想定して設計されています（ルックアヘッドバイアス回避、冪等性、フェイルセーフ等）。

主な機能
- データ取得 / ETL
  - J‑Quants API から株価日足・財務データ・マーケットカレンダー等を差分取得（ページネーション/リトライ/レート制御対応）。
  - run_daily_etl で日次一括 ETL（カレンダー → 株価 → 財務 → 品質チェック）。
- データ品質管理
  - 欠損、重複、将来日付、スパイク（急騰/急落）などのチェックを実行（quality.run_all_checks）。
- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、トラッキング除去、前処理）。
  - OpenAI を使った銘柄別ニュースセンチメント（news_nlp.score_news）。
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（ai.regime_detector.score_regime）。
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ）や将来リターン、IC 計算、Z スコア正規化等。
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル定義・初期化（init_audit_schema / init_audit_db）。

必要条件（主な依存）
- Python 3.9+（型注釈は 3.10 以降の表記を含むが互換性はプロジェクトに依存）
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （標準ライブラリ以外は必要に応じて追加で pip インストール）

セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
2. 依存ライブラリをインストール（例）
   - pip install duckdb openai defusedxml
   - 必要に応じて logging 等を設定
3. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。
   - 自動ロード: パッケージ初期化時に `.env` → `.env.local` が自動で読み込まれます（OS 環境変数優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN : Slack 通知用 BOT トークン
     - SLACK_CHANNEL_ID : 通知対象 Slack チャンネル ID
     - KABU_API_PASSWORD : kabu API（発注等）のパスワード
     - OPENAI_API_KEY : OpenAI を使用する機能を呼ぶ場合（score_news / score_regime など）
   - 任意 / デフォルト
     - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL : DEBUG/INFO/…（デフォルト INFO）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH : 監視用 sqlite（デフォルト data/monitoring.db）
4. データベース初期化（監査ログ例）
   - Python REPL またはスクリプトで:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - または既存 DuckDB 接続に対して init_audit_schema(conn)

基本的な使い方（サンプル）
- DuckDB 接続の作成（デフォルトパスを使用）
  - from duckdb import connect
    from kabusys.config import settings
    conn = connect(str(settings.duckdb_path))
- 日次 ETL を実行
  - from kabusys.data.pipeline import run_daily_etl
    from datetime import date
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
- ニュースセンチメントスコア（1日分）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, date(2026, 3, 20))  # 戻り値は書き込んだ銘柄数
- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, date(2026, 3, 20))
- 研究／ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    mom = calc_momentum(conn, date(2026, 3, 20))
- データ品質チェック
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2026,3,20))
    for i in issues: print(i)

環境変数読み込みについて
- 自動読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストや CI で利用）。
- .env のパースはシェル風の key=value を幅広くサポートしています（export プレフィックスやクォート、インラインコメント等）。

注意点 / トラブルシューティング
- OpenAI 呼び出し：API エラーやタイムアウトは内部でリトライし、最終的に失敗してもフェイルセーフとしてスコアを 0 に戻す等の挙動があります（サービス利用料金やレート制限に注意）。
- J‑Quants API：モジュールは 120 req/min を守るための RateLimiter を実装しています。get_id_token はリフレッシュを自動で行います。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、モジュール内で空リストチェックがされています。
- ニュース取得は SSRF 対策や受信サイズ制限等の安全対策を実装していますが、実運用ではさらに監視を推奨します。
- テスト時は ai モジュール内の _call_openai_api をパッチしてモックすることで外部呼び出しを抑制できます。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（version）
  - config.py — 環境変数 / 設定管理（自動 .env 読込、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM ベースセンチメント（score_news）
    - regime_detector.py — マクロ + MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J‑Quants API クライアント（fetch/save）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — マーケットカレンダー管理（is_trading_day, next_trading_day 等）
    - quality.py — データ品質チェック（QualityIssue、check_*）
    - stats.py — zscore_normalize 等汎用統計
    - audit.py — 監査ログスキーマ／初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン / IC / rank / summary
  - ai/, data/, research/ などは上位公開 API を __all__ で整備

開発・コントリビュート
- コードスタイルやテストはプロジェクト内の方針に従ってください。API 周り（外部通信）を伴う箇所はモック可能な設計になっています。
- 自動 env ロードを無効化したり、OpenAI や J‑Quants 呼び出しをモックすることでユニットテストを書きやすくしています。

ライセンス / その他
- このリポジトリのライセンス情報や .env.example（存在を想定）を確認して下さい。

以上が README.md の概要です。必要であればサンプル .env.example のテンプレートや具体的な CLI 実行例／systemd / cron ジョブ例、requirements.txt の候補を追記しますか？