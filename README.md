# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）などを一通り備えています。

---

## 特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、JPX カレンダーの差分取得（ページネーション対応／レートリミッティング／トークン自動リフレッシュ）
  - ETL 結果の品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL エントリポイント（run_daily_etl）
- ニュース収集
  - RSS 取り込み（SSRF 対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols との紐付けを前提とした保存設計
- AI（OpenAI）
  - ニュースを銘柄ごとに集約して LLM（gpt-4o-mini）でセンチメント算出（score_news）
  - ETF（1321）200 日 MA とマクロニュースから市場レジームを判定（score_regime）
  - API 呼び出しはリトライ・エラーハンドリング・JSON モードでの厳密なパース
- 研究（research）
  - Momentum / Volatility / Value などのファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Z スコア正規化ユーティリティ
- 監査（audit）
  - signal_events / order_requests / executions を含む監査用スキーマの初期化・管理（冪等）
  - order_request_id による冪等性保証、UTC タイムスタンプ、インデックス構成
- 汎用ユーティリティ
  - 環境変数読み込み（.env 自動読み込み、無効化フラグあり）
  - DuckDB ベースの一貫したデータアクセス

---

## 必要条件 / 前提

- Python 3.10+
- 主要依存パッケージ（抜粋）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、ニュース RSS）

requirements.txt はプロジェクトに合わせて用意してください（本 README はパッケージ化済みを前提にしています）。

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作る
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .   # パッケージ化されている場合
   # または必要パッケージを個別にインストール
   pip install duckdb openai defusedxml
   ```

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（一覧と説明）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - OPENAI_API_KEY — OpenAI の API キー（AI モジュールを使う場合）
   - KABU_API_PASSWORD (必須 for kabu API 関連)
   - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知に使用（任意）
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_FILL_MODE — Paper Trading 時の挙動: instant | partial | never | reject（デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 実行監視用（任意）
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
   - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

3. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な呼び出し例）

※ 以下の例は Python REPL / スクリプト内で実行します。DuckDB に接続して各関数を呼び出します。

- 基本的な準備
  ```python
  from kabusys.config import settings
  import duckdb

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # デフォルトで target_date=今日
  print(result.to_dict())
  ```

- 市場カレンダー更新ジョブだけ実行する
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- ニュースセンチメント（AI）スコアを計算して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, date(2026, 3, 20))  # target_date を指定
  print("scored:", count)
  ```
  - OPENAI_API_KEY が必要です（関数引数に api_key を渡すことも可能）。

- 市場レジームを判定して market_regime に保存する
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, date(2026, 3, 20))
  ```
  - こちらも OpenAI の API キーが必要（api_key 引数または環境変数）。

- 監査ログスキーマを初期化する（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")  # ディレクトリ自動作成
  ```

- 研究用：ファクター計算・IC 等
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns
  from datetime import date
  mom = calc_momentum(conn, date(2026, 3, 20))
  vols = calc_volatility(conn, date(2026, 3, 20))
  vals = calc_value(conn, date(2026, 3, 20))
  fwd = calc_forward_returns(conn, date(2026, 3, 20))
  ```

- ニュース RSS を取得する（保存は呼び出し側で行う想定）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])
  ```

---

## 注意事項 / トラブルシューティング

- AI モジュール（news_nlp / regime_detector）は OpenAI に依存します。API レートや課金に注意してください。API エラー時はフォールバックロジック（スコアを 0.0 にする等）が組み込まれていますが、精度・成功率は入力データに依存します。
- J-Quants API はレートリミット（デフォルト 120 req/min）に対応したロジックを備えています。refresh token が必要です。
- DuckDB の executemany に空リストを渡すとバージョンによってはエラーになるため、モジュール内で空チェックを行っています。もしアップデートで問題が出たら DuckDB のバージョンを確認してください。
- .env 自動読み込みはプロジェクトルート（.git か pyproject.toml が存在するディレクトリ）を基準に行います。テストで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（gpt-4o-mini を用いる）
    - regime_detector.py — 市場レジーム判定ロジック（ETF 1321 MA200 とマクロニュースの合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジックを含む）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL 結果型のエクスポート（ETLResult）
    - calendar_management.py — マーケットカレンダー管理・判定ユーティリティ
    - news_collector.py — RSS 収集・前処理（SSRF 対策等）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — 共通統計ユーティリティ（zscore 正規化）
    - audit.py — 監査ログスキーマ作成 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value ファクター計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank
  - research/*.py その他研究向けユーティリティ

---

## 開発 / 貢献

- バグや改善要望は Issue を立ててください。
- テストは各モジュールを単体で mock を使って呼び出す設計になっています（特に外部 API 呼び出し部分は差し替え可能に実装）。

---

README に載せきれない細かい実装上の注意（例: DuckDB の日付型扱い、OpenAI JSON mode のパース回復処理、news_collector の SSRF 対策詳細など）はソース内の docstring に記載しています。実装を読むことを推奨します。