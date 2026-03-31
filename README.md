# KabuSys

日本株向け自動売買データプラットフォーム / 研究・NLP・監査を含むユーティリティ群

概要
- KabuSys は日本株向けのデータパイプライン、ニュースNLP、レジーム判定、ファクター計算、監査ログ管理等を含むライブラリ群です。
- 主に J-Quants API と連携してデータ取得（株価・財務・マーケットカレンダー）→ DuckDB へ保存 → 研究・シグナル生成・監査に使える形で提供します。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別・マクロ）評価や、市場レジーム判定機能を備えています。

主な機能
- 環境変数 / .env 読込み（自動ロード機能、.env.local 優先）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX カレンダー取得（ページネーション対応・認証自動リフレッシュ）
  - 保存関数（DuckDB へ冪等保存）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- ニュース収集（RSS 収集・前処理・SSRF対策・DB保存補助）
- ニュース NLP（銘柄別センチメント score_news、LLM 呼び出しのリトライ/バッチ処理）
- レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントを合成）
- 研究用ユーティリティ（モメンタム・バリュー・ボラティリティ等のファクター計算、forward returns、IC、Zスコア正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions テーブル定義・初期化ユーティリティ）
- ユーティリティ（カレンダー管理、統計、URL 正規化、RSS パースの安全化）

セットアップ手順（開発 / 利用開始）
1. Python 環境
   - Python 3.10+ を推奨
2. 依存ライブラリ（例）
   - duckdb
   - openai
   - defusedxml
   - （必要に応じて他の標準ライブラリは requirements に追加）
   インストール例:
   ```
   python -m pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）
3. パッケージインストール（開発）
   ```
   pip install -e .
   ```
   （setup/pyproject がある場合。無い場合はパスを PYTHONPATH に追加して利用）
4. 環境変数 / .env の準備
   - プロジェクトルートの .env または .env.local に設定することで自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知用（使わない場合もあり）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID
     - KABU_API_PASSWORD — kabu API 用パスワード
     - OPENAI_API_KEY — OpenAI を利用する場合（score_news / score_regime 用）
   - デフォルト例 (.env.example):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=your_slack_token
     SLACK_CHANNEL_ID=your_channel_id
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - .env のパースはシェル形式をかなり柔軟に扱えます（export prefix、クォート内のエスケープ、コメント処理など）。
5. データベース準備
   - DuckDB を利用する場合、ファイルパス（例: data/kabusys.duckdb）へ接続してスキーマ初期化等を行ってください。
   - 監査用 DB を別ファイルで初期化するユーティリティもあります（init_audit_db）。

基本的な使い方（短い例）
- DuckDB 接続を取得して ETL を実行する（Python スクリプト例）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # 例: 今日分の ETL
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニューススコア（銘柄別 ai_score）を生成する:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定を実行する:
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB を初期化する:
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests 等の操作が可能
  ```

- スキーマ初期化（必要に応じて自作の init スクリプトを用意してください）
  - 本リポジトリはスキーマ生成ユーティリティを含みます（例: audit.init_audit_schema）。主要テーブルの DDL は各モジュールに定義されています。実運用では事前に schema 初期化関数を呼び出してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード、設定ラッパ
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別）スコアリング
    - regime_detector.py — 市場レジーム判定（MA200 + マクロ・LLM）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save）
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS ニュース収集（SSRF対策・前処理）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - stats.py — 統計ユーティリティ（zscore_normalize 等）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログテーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — momentum/value/volatility 等のファクター計算
    - feature_exploration.py — forward returns, IC, factor_summary, rank
  - research/...（その他ユーティリティ）
- pyproject.toml / setup.cfg 等はプロジェクトルートに置く想定（本コードは src 配下にある前提）

注意事項 / 運用メモ
- Look-ahead バイアス対策
  - 多くの関数は date.today() / datetime.today() を直接参照しない設計（target_date を外部から渡す方式）になっています。バッチ処理・バックテスト時は target_date の指定を忘れないでください。
- OpenAI（LLM）呼び出し
  - OpenAI API はレスポンスのパースやエラーを多重に扱う実装になっています。テスト時は各モジュール内部の _call_openai_api をモックすることを推奨します。
  - リトライやタイムアウトは組み込まれていますが、API鍵の設定（OPENAI_API_KEY）は必須です。
- J-Quants API
  - レート制限（120 req/min）を遵守する RateLimiter を実装済み。get_id_token による自動リフレッシュ・ページネーション対応を行います。
- セキュリティ/安全性
  - news_collector は SSRF 対策、gzip/サイズ上限、defusedxml による XML パースを行います。
- テスト
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config の自動 .env ロードを無効化でき、ユニットテストで環境ごとの差し替えが容易です。

トラブルシュート（よくある質問）
- 「OpenAI API キーが見つからない」
  - OPENAI_API_KEY を .env に設定するか、score_news/score_regime の api_key 引数にキーを渡してください。
- 「J-Quants の認証で 401 が出る」
  - settings.jquants_refresh_token を .env で設定してください。get_id_token はリフレッシュトークンから id_token を取得します。
- 「DuckDB にテーブルがない」
  - ETL を初回実行する前に必要スキーマを作成するスクリプト（プロジェクト用の schema 初期化）が必要です。audit 用の初期化は data.audit.init_audit_db / init_audit_schema を参照してください。

貢献/開発
- コードの拡張・修正は Pull Request を通じて行ってください。
- ユニットテストでは外部 API 呼び出し（OpenAI / J-Quants / RSS）をモック化して実行することを推奨します。

ライセンス
- （本サンプル README ではライセンス情報は省略。実際のリポジトリでは LICENSE ファイルを明示してください）

以上がこのコードベースの概要・導入・基本的な使い方のまとめです。必要であれば利用シナリオ別の詳細例（CI/CD、運用バッチ、バックテスト用スクリプト等）も作成します。どの部分を優先して詳しく説明しますか？