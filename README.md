# KabuSys

日本株向けのデータ基盤 / リサーチ / 自動売買支援ライブラリです。  
DuckDB をデータレイクとして利用し、J-Quants / RSS / OpenAI（LLM）などを統合して、ETL・品質チェック・ニュースNLP・市場レジーム判定・ファクター計算・監査ログ管理を提供します。

主な用途例:
- 日次 ETL（株価、財務、カレンダー）の自動化
- ニュース記事のセンチメントスコアリング（銘柄毎）
- 市場レジーム（bull / neutral / bear）判定
- ファクター計算およびリサーチ用ユーティリティ
- 発注・約定フローの監査ログ用スキーマ初期化

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（基本例）
- ディレクトリ構成
- 環境変数一覧（主要）
- 補足・注意点

---

プロジェクト概要
- KabuSys は日本株向けのデータパイプラインと研究ツール群を集めた Python パッケージです。
- ETL（J-Quants からの株価/財務/カレンダー取得）、データ品質チェック、ニュース収集と LLM によるセンチメント解析、ファクター計算、監査ログ（注文 → 約定の追跡）などを提供します。
- DuckDB を中核に使い、ETL は冪等的に保存される設計（ON CONFLICT / upsert 相当）になっています。

---

機能一覧
- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存・自動リフレッシュ・レート制御・リトライ）
  - カレンダー管理（営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job）
  - ニュース収集（RSS 取得、安全対策（SSRF 対応）、前処理、news_symbols 連携）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログ（signal_events / order_requests / executions テーブル定義・初期化）
  - 統計ユーティリティ（zscore_normalize 等）
- ai
  - ニュース NLP（銘柄毎センチメントを LLM で算出: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュース LLM を合成: score_regime）
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 特徴量解析（将来リターン計算、IC、サマリー、ランク関数）
- config
  - .env 自動読み込み（プロジェクトルートを発見して .env / .env.local をロード）
  - Settings オブジェクトから環境変数を型安全に参照

---

セットアップ手順（例）
1. リポジトリをクローン
   - git clone … && cd your-repo

2. Python と仮想環境
   - 推奨 Python: 3.10 以上（typing の union 型や pathlib 等を使用）
   - 仮想環境作成例:
     python -m venv .venv
     source .venv/bin/activate

3. 依存ライブラリをインストール
   - 本コードベースで利用される主なパッケージ（例）:
     pip install duckdb openai defusedxml
   - 実際は requirements.txt / pyproject.toml に依存関係がある想定なので、プロジェクトに合わせてインストールしてください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に自動で .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定が必要な環境変数（主要）は以下「環境変数一覧」を参照してください。
   - サンプル: .env
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB ファイル準備（任意）
   - デフォルトでは data/kabusys.duckdb を使用（settings.duckdb_path）。
   - 監査用 DB 初期化例（コード内 util を使用）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

使い方（基本的なコード例）

1) DuckDB 接続を作って ETL を実行（日次 ETL）
- 例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ETLResult に取得数・保存数・品質チェック結果・エラーが格納されます。

2) ニュースセンチメントのスコアリング
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # APIキーは引数でも渡せる。None の場合は環境変数 OPENAI_API_KEY を使用
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")

- score_news は raw_news / news_symbols / ai_scores テーブルを参照/更新します。OPENAI API 呼び出しは gpt-4o-mini を利用する想定。

3) 市場レジーム判定
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 内部で ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成し、market_regime テーブルへ冪等書き込みします。

4) 監査スキーマの初期化
- 例（監査専用 DB を作る）:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring_audit.duckdb")
  # これで signal_events, order_requests, executions テーブルが作成されます

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・Settings
  - ai/
    - __init__.py
    - news_nlp.py             # ニュース NLP スコアリング
    - regime_detector.py      # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得・保存）
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - etl.py                  # ETLResult エクスポート
    - calendar_management.py  # マーケットカレンダー管理
    - news_collector.py       # RSS ニュース収集（SSRF 対策等）
    - quality.py              # データ品質チェック
    - stats.py                # 統計ユーティリティ（zscore_normalize 等）
    - audit.py                # 監査ログ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py      # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py  # 将来リターン・IC・summaries
  - monitoring/ (※ present in __all__ in package init — 実装は省略されている可能性あり)

ファイル詳細はソースを参照してください。主要な処理は DuckDB 接続を受け取って SQL を実行するため、テストやバッチ実行が容易です。

---

環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用リフレッシュトークン。jquants_client.get_id_token に利用。
- OPENAI_API_KEY
  - OpenAI（LLM）呼び出し時に使用。ai.score_news / ai.score_regime は引数で API キーを渡せますが、未指定時はこの環境変数を参照します。
- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
- SQLITE_PATH (任意, default: data/monitoring.db)
- PID_FILE_PATH (任意, default: data/execution.pid)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT (任意)
- KABUSYS_ENV (任意, default: development)
  - 有効値: development / paper_trading / live
- LOG_LEVEL (任意, default: INFO)
  - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化

.env の読み込み順:
- OS 環境変数 > .env.local > .env
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行います。

---

補足・注意点
- Look-ahead bias に配慮した実装:
  - 日付処理は target_date を明示的に渡す設計（datetime.today()/date.today() を直接参照しない実装方針）。
  - ETL / スコアリング関数は target_date を受け取り、過去データのみを参照します。
- API リトライ / フェイルセーフ:
  - J-Quants / OpenAI 呼び出しはリトライやバックオフ処理を備え、致命的エラー時はログを残して継続する設計の箇所があります（完全に例外を投げる部分と WARN でフォールバックする部分が混在）。
- セキュリティ:
  - news_collector は SSRF 対策、XML の安全なパース（defusedxml）、レスポンスサイズ制限を備えています。
- テスト:
  - OpenAI 呼び出し等は内部の _call_openai_api をモック／差し替えてテスト可能な設計です。
- 依存パッケージや細かいランタイム要件は pyproject.toml / requirements.txt を確認してください（プロジェクト配布時に同梱される想定）。

---

問題報告・貢献
- バグ報告や改善提案は Issue を作成してください。Pull Request は歓迎します。

以上。README に記載して欲しい追加の使い方（例: cron 設定、具体的な SQL スキーマ一覧、CI 設定など）があれば教えてください。必要に応じて追記します。