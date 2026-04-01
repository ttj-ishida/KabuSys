# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）

軽量な DuckDB ベースのデータプラットフォーム、J-Quants / RSS / OpenAI を組み合わせた
ETL、ニュースNLP（LLMによるセンチメント）、市場レジーム判定、研究用ファクター計算、
監査ログ等のユーティリティ群を提供します。

主な設計方針:
- ルックアヘッドバイアス対策（内部で datetime.today() を直接参照しない等）
- 冪等性（DB 保存は ON CONFLICT で上書き）
- 外部 API へのリトライ・レート制御やフェイルセーフを備えた実装
- テスト容易性（環境変数自動ロードの無効化など）

---

## 機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（settings オブジェクト）

- データ取り込み / ETL（kabusys.data）
  - J-Quants API クライアント（fetch / save / 認証・リフレッシュ）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF 防御、トラッキング除去、記事ID生成）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events, order_requests, executions の DDL と初期化ユーティリティ）

- ニュースNLP / 市場レジーム（kabusys.ai）
  - gpt-4o-mini を用いたニュースセンチメント（score_news）
  - ETF（1321）200日MA乖離とマクロセンチメントを合成したレジーム判定（score_regime）
  - OpenAI 呼び出しに対するリトライ・パース保護（フェイルセーフで 0.0 にフォールバック）

- 研究用ユーティリティ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（情報係数）、ファクターサマリ、Zスコア正規化

- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize など

---

## 要件

- Python 3.10+
- 主要ライブラリ（例）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリの urllib 等を使用

実運用では Slack / kabuステーション 連携用の設定（トークン等）が必要になります。

---

## 環境変数（.env の例）

以下は主に使用される環境変数です（README 用の抜粋）。実装は `kabusys.config.Settings` を参照してください。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID
- KABU_API_PASSWORD: kabuステーション API のパスワード

任意 / デフォルトあり:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live) — default: development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) — default: INFO

自動 .env ロード:
- .env / .env.local がプロジェクトルート（.git または pyproject.toml の親）にあれば自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

---

## セットアップ手順（開発環境向け）

1. Python と仮想環境を準備
   - Python 3.10 以上を推奨
   - 仮想環境作成: python -m venv .venv && source .venv/bin/activate

2. 依存ライブラリをインストール（例）
   - pip install duckdb openai defusedxml

   ※ プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを使用してください。

3. .env を作成
   - リポジトリルートに .env を作り、上記の必須キーを設定してください。
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_password

4. DuckDB データベース用ディレクトリを作成（必要に応じて）
   - デフォルトの DB は data/kabusys.duckdb（settings.duckdb_path）です。
   - 例: mkdir -p data

---

## 使い方（簡易ガイド）

以下はライブラリの主要なユースケースと簡単なコード例（対話的に使う場合）。

- DuckDB 接続を開いて ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written {written} codes")
  ```

- 市場レジームをスコアリングして market_regime に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DB を初期化する
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # または既存接続にスキーマを追加:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクタ計算（例: momentum）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意点:
- OpenAI 呼び出し時は api_key を引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants はリフレッシュトークンを使用して ID トークンを取得します（settings.jquants_refresh_token を設定）。
- ETL / API 呼び出しはネットワークエラー・429 等へのリトライとフェイルセーフが組み込まれていますが、API レートはサービス側の制限に従ってください。

---

## ディレクトリ構成

（コードベースから抽出した主要ファイル構成の抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - calendar_management.py
      - news_collector.py
      - stats.py
      - quality.py
      - audit.py
      - pipeline.py (ETLResult 再エクスポート)
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/ (上記)
    - research/ (上記)

各モジュールの責務（簡潔）
- config.py: 環境設定読み込み・検証・自動 .env ロード
- data/jquants_client.py: J-Quants API の取得・保存（rate limit / retry / token refresh）
- data/pipeline.py: 日次 ETL の Orchestrator（run_daily_etl 等）
- data/news_collector.py: RSS → raw_news（SSRF 対策・前処理）
- data/quality.py: データ品質チェック
- data/audit.py: 監査ログテーブル DDL と初期化ユーティリティ
- ai/news_nlp.py: OpenAI を用いた銘柄別ニュースセンチメント（score_news）
- ai/regime_detector.py: ETF MA とマクロセンチメントの合成による市場レジーム判定（score_regime）
- research/*: ファクター計算・IC 等

---

## 設計上の注意 / 運用メモ

- ルックアヘッドバイアス防止: 日付参照は明示的な target_date を受け取り、内部で現在時刻を直接参照しない設計を優先しています。バッチ / バックテストで target_date を適切に与えてください。
- 冪等性: DB 保存は ON CONFLICT DO UPDATE を採用し、再実行や部分失敗に対する安全性を確保しています。
- 外部 API の扱い: J-Quants には固定間隔スロットリング、OpenAI 呼び出しは JSON モード + エラーハンドリング（429/5xx の再試行）を備えています。呼び出し回数に注意してください。
- セキュリティ: news_collector では SSRF 防御（リダイレクト検査・プライベートIP 拒否）・XML パースに defusedxml を利用しています。

---

## テスト / 開発ヒント

- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテスト等で環境を制御しやすくなります）。
- OpenAI / J-Quants 呼び出しはモックしやすいように内部 API 呼び出しを関数で分離してあります（例: news_nlp._call_openai_api を patch する等）。
- DuckDB はインメモリ ":memory:" を使えます（audit.init_audit_db 等でサポート）。

---

READMEに記載した以外の詳細は各モジュールの docstring を参照してください（コード内に設計方針・処理フロー・安全策が丁寧にコメントされています）。質問や特定の使い方の例が必要であれば教えてください。