# KabuSys

日本株自動売買プラットフォームのライブラリ（内部モジュール群）。データ収集（J-Quants / RSS）、ETL、データ品質チェック、特徴量計算、ニュースNLP（LLM を利用したセンチメント）、市場レジーム判定、監査ログ（発注→約定トレース）など、アルゴリズムトレードに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ取得 / ETL
  - J-Quants API から株価日足・財務データ・上場情報・マーケットカレンダーの差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（quality モジュール）
- カレンダー管理
  - market_calendar の管理と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - 夜間バッチ更新ジョブ（calendar_update_job）
- ニュース収集・NLP
  - RSS からのニュース収集（news_collector）
  - OpenAI を使った銘柄単位ニュースセンチメント（news_nlp.score_news）
- 市場レジーム判定
  - ETF 1321 の MA とマクロニュースを統合して日次レジーム（bull / neutral / bear）を計算（ai.regime_detector.score_regime）
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility 等）、将来リターン、IC 計算、Z スコア正規化（research モジュール）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマの初期化（data.audit.init_audit_schema / init_audit_db）

---

## 要件

- Python 3.10 以上（PEP 604 型記法などを使用）
- 主な依存パッケージ（インストール方法は次節参照）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリも広く使用）

環境変数・API キーを多く利用するため、.env ファイルで管理することを想定しています。

---

## インストール

1. 仮想環境を作成・有効化（任意）:
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（例）:
   ```
   pip install duckdb openai defusedxml
   ```

3. このパッケージを開発環境にインストールする場合:
   ```
   pip install -e .
   ```

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを利用してください）

---

## 環境変数 / 設定

自動でプロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を読み込みます（優先度: OS環境 > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に参照される環境変数:

- J-Quants 関連
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- kabu ステーション
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- OpenAI
  - OPENAI_API_KEY（score_news / score_regime 等で未指定時に参照）
- Slack（監視/通知用）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス（省略時デフォルト）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 実行環境 / ログ
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

必須変数が未設定の場合は Settings.accessor が ValueError を発生させます（kabusys.config.settings 経由で取得）。

---

## セットアップ手順（簡易）

1. リポジトリルートに `.env` を作成（`.env.example` を参考に必要項目を設定）。
2. DuckDB 用データディレクトリを用意（デフォルト: data/）:
   ```
   mkdir -p data
   ```
3. OpenAI / J-Quants の API キーやトークンを `.env` に設定。
4. 必要な Python パッケージをインストール（上記参照）。

---

## 使い方（主要な呼び出し例）

以下はライブラリ関数を直接呼ぶ簡単な例です。どれも DuckDB 接続（duckdb.connect(...））を受け取ります。

- 日次 ETL を実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に書き込む:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定していれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定を実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DB を初期化する:
  ```python
  import kabusys.data.audit as audit
  conn = audit.init_audit_db("data/audit.duckdb")
  # または既存接続にスキーマを追加する:
  # audit.init_audit_schema(conn, transactional=True)
  ```

- カレンダー更新ジョブを実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"保存件数: {saved}")
  ```

注意:
- OpenAI を呼ぶ関数（score_news, score_regime）は api_key 引数にキーを渡すか、環境変数 OPENAI_API_KEY を利用します。
- J-Quants 呼び出しは settings.jquants_refresh_token（環境変数 JQUANTS_REFRESH_TOKEN）を使用します。

---

## 実装上の設計ポリシー（要点）

- ルックアヘッドバイアス防止のため、内部実装は date.today() / datetime.today() を不用意に参照せず、明示的な target_date を受け取る設計です。
- ETL・API 呼び出しには冗長なリトライと指数バックオフ、レートリミッティング（J-Quants）を組み込んでいます。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / INSERT … ON CONFLICT）で実装。
- ニュース取得では SSRF 対策、レスポンスサイズ制限、XML の安全なパース（defusedxml）などセキュリティ考慮をしています。
- OpenAI 呼び出しは JSON mode を想定し、入力 / 出力のバリデーションを行います。API 失敗時にはフェイルセーフでゼロスコアにフォールバックする実装があります。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント・保存ロジック
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 公開エントリ（ETLResult）
    - calendar_management.py        — マーケットカレンダー管理
    - news_collector.py             — RSS ニュース収集
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/vol）
    - feature_exploration.py        — 将来リターン / IC / summary
  - monitoring/ (未列挙: 監視・Slack 連携等の想定モジュール)
  - execution/, strategy/ など（パッケージ公開名に含まれるが実装は別途）

（上記は本コードベースで提供されている主要モジュールを抜粋）

---

## 注意事項 / 運用上のヒント

- OpenAI API のコストとレート制限に注意してください。batch サイズやトークン量を調整してください。
- J-Quants の API レート制限（120 req/min）に準拠するため、jquants_client 内で固定間隔の RateLimiter を実装しています。ETL 実行時は連続実行でレートを超えないよう配慮してください。
- 本ライブラリはバックテストや実運用の基盤として設計されていますが、発注（execution）や実口座での運用時は追加の安全検証（テスト、監視、ロールバック手順）を必ず導入してください。
- .env の自動読み込みを無効化したい場合は、プロセス起動前に環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（単体テスト等で有用）。

---

もし README に追加したいサンプルスクリプト、CI 設定、より詳しい API 使用例（J-Quants / OpenAI の呼び出しフロー）やデータスキーマ（テーブル定義）などがあれば、その内容に合わせて追補版を作成します。