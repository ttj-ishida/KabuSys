# KabuSys

日本株向けのデータ基盤・研究・自動売買支援ライブラリです。  
DuckDB をデータストアに、J-Quants / RSS / OpenAI（LLM）を活用してデータ収集・品質管理・ニュースセンチメント解析・市場レジーム判定・ファクター研究・監査ログを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するためのモジュール群を含む Python パッケージです。主に以下を目的とします。

- J-Quants API からのデータ取得（株価日足、財務、マーケットカレンダー）
- RSS によるニュース収集と LLM（OpenAI）を用いたニュースセンチメント解析
- 日次 ETL パイプライン（差分取得・保存・品質チェック）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- マーケットレジーム判定（MA と マクロニュースセンチメントの合成）
- 監査ログ（signal → order_request → execution）用スキーマ初期化・管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の留意点として、ルックアヘッドバイアス回避（内部で datetime.today() をむやみに使わない）、冪等性（DB への保存は ON CONFLICT ベース）、フェイルセーフ（API 失敗時に処理継続）が徹底されています。

---

## 機能一覧

- 環境設定管理（.env の自動読み込み、settings オブジェクト）
- J-Quants クライアント
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - get_id_token（リフレッシュ）
- ETL パイプライン（data.pipeline）
  - run_daily_etl（カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック）
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
- ニュース収集（data.news_collector）
  - RSS フィード取得、安全対策（SSRF 防止・サイズ制限・トラッキング除去）
- ニュース NLP（ai.news_nlp）
  - calc_news_window / score_news（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（ai.regime_detector）
  - score_regime（ETF 1321 の MA200 乖離と LLM マクロセンチメントを合成）
- 研究用モジュール（research）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログスキーマ（data.audit）
  - init_audit_schema / init_audit_db（監査テーブルとインデックス初期化）

---

## セットアップ手順

前提: Python 3.10+（型注釈のユニオン等に依存）。プロジェクトは src 配下のパッケージ構成です。

1. 仮想環境の作成・有効化（任意）
   - macOS / Linux
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージのインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 実際の開発では requirements.txt や pyproject.toml を使って管理してください。
   - OpenAI SDK、duckdb、defusedxml（RSS の安全パース）などが想定されます。

3. 開発インストール（プロジェクトルートに pyproject.toml がある想定）
   ```bash
   pip install -e .
   ```
   （パッケージ名は `kabusys`）

4. 環境変数設定
   - .env または .env.local をプロジェクトルートに配置できます（kabusys.config により自動ロードされます）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必要に応じて）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: 通知用
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB など（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   - 自動読み込みを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（主要な例）

以降は Python REPL やスクリプトから利用する想定です。

- 設定オブジェクトにアクセスする
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を指定しない場合は今日が対象（日次 ETL が target_date に合わせて処理）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコアリングして ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を利用
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DB 初期化（監査専用 DuckDB）
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルへ書き込み/検索が行えます
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, date(2026,3,20))
  v = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

注意:
- OpenAI の呼び出し部分はリトライ・フォールバックが実装されています。テストでは関数内部の _call_openai_api をモックして挙動を制御できます。
- ETL や保存処理は冪等性（ON CONFLICT）を考慮して設計されています。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 配下に主要モジュールを配置しています。主な構成:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / .env ロード、settings
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント解析（score_news）
    - regime_detector.py     # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py # 市場カレンダー管理・営業日判定
    - etl.py                 # ETL API 再エクスポート
    - pipeline.py            # 日次 ETL パイプライン
    - stats.py               # 統計ユーティリティ（zscore_normalize 等）
    - quality.py             # データ品質チェック
    - audit.py               # 監査ログスキーマ定義 / 初期化
    - jquants_client.py      # J-Quants API クライアント（取得・保存）
    - news_collector.py      # RSS ニュース取得
  - research/
    - __init__.py
    - factor_research.py     # モメンタム / バリュー / ボラティリティ
    - feature_exploration.py # 将来リターン / IC / 統計サマリー
  - monitoring/               # （将来モジュール用、README の冒頭 __all__ に含まれる想定）
  - strategy/                 # 戦略・シグナル生成（将来実装想定）
  - execution/                # 発注・約定処理（将来実装想定）

この README に記載の機能はコード内ドキュメント（docstring）を優先しています。各モジュールには関数レベルで詳細な設計や仕様（フェイルセーフ、ルックアヘッド対策、トランザクション方針等）が記載されています。

---

## 注意事項 / 運用上のメモ

- セキュリティ:
  - news_collector では SSRF 防止、トラッキング除去、受信サイズ制限、defusedxml を用いた XML パース等の安全対策を実装しています。
  - J-Quants / OpenAI の API キーは外部に漏らさないようにしてください。
- データ一貫性:
  - ETL は差分取得・バックフィルを行い、DB への保存は冪等的です。運用時のジョブスケジューリング（cron / Airflow 等）を推奨します。
- ルックアヘッドバイアス:
  - 解析・研究系関数は内部で現在時刻を直接参照しない実装方針が採られています。バックテストや研究用途では target_date を明示的に指定してください。
- ロギング:
  - 設定により LOG_LEVEL を制御できます。prod 環境では INFO 以上、デバッグ時は DEBUG を推奨します。
- テスト:
  - OpenAI やネットワーク呼び出しはモック化してユニットテストしてください。モジュール内の _call_openai_api 等はテストで差し替え可能です。

---

必要であれば、README に .env.example のテンプレートやより詳細な使用例（cron / Dockerfile / CI 設定）を追加できます。どの情報を優先して追記するか指定してください。