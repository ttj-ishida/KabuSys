# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（データ取得 / ETL / ニュースNLP / 研究用ファクター計算 / 監査ログ等）

このリポジトリは、J-Quants や RSS、OpenAI を組み合わせて日本株のデータ基盤・研究・AI判定・監査ログを提供するモジュール群です。実際の発注（ブローカー連携）や実運用のオーケストレーションは別レイヤーで実装する前提のライブラリ設計になっています。

バージョン: 0.1.0

---

## 主な機能

- データ取得（J-Quants API 経由）
  - 日次株価（OHLCV）取得・ページネーション対応
  - 財務データ（四半期）取得
  - JPX マーケットカレンダー取得
  - 上場銘柄一覧取得

- ETL パイプライン（差分取得・バックフィル）
  - run_daily_etl を入口にカレンダー／株価／財務を差分で取得・保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集（RSS）
  - RSS から記事を取得・前処理・冪等保存（raw_news / news_symbols）
  - SSRF 対策、応答サイズ制限、トラッキングパラメータ除去など堅牢性に配慮

- ニュースNLP / 市場レジーム判定
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成した市場レジーム判定（score_regime）

- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value / Liquidity）
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化 等

- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査トレーサビリティ（UUID）を考慮した設計、UTC タイムスタンプ

- 設定管理
  - .env / 環境変数の自動ロード（プロジェクトルート検出）
  - settings オブジェクト経由でアクセス（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）

---

## 動作環境 / 前提

- Python 3.10 以上（typing の | 記法などを使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS フィード, OpenAI）

（実行環境に合わせてパッケージ管理ファイルを作成してください。requirements.txt を用意すると便利です。）

---

## セットアップ手順

1. リポジトリをクローン、仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   - 開発用途で editable install:
     - pip install -e .

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（config.py による自動ロード。ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI を使う機能実行時に必要（score_news / score_regime）
   - 任意 / デフォルトあり
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | …
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT など監視設定

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     OPENAI_API_KEY=sk-xxxx...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. データベース用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

以下のサンプルはライブラリ API を直接呼ぶ方法です。実運用ではジョブスケジューラ（cron / systemd / Airflow 等）から呼び出してください。

- DuckDB 接続を作成して日次 ETL を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを作る（OpenAI API キーは env または api_key 引数で渡す）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
  print("written:", n_written)
  ```

- 市場レジームを判定して保存:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー関連ユーティリティ:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 設定値を参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意:
- OpenAI を使うスコア関数は API 呼び出しに失敗した場合にフォールバック（ゼロ・スキップ）する設計です。API キーは環境変数 `OPENAI_API_KEY` で与えるか、各関数の api_key 引数を使って注入してください。
- J-Quants は API レート制限があるため、fetch / save 処理では内部でスロットリングと再試行を行います。

---

## 主要モジュール説明（ディレクトリ構成）

以下は src/kabusys 配下の主要ファイルと簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、settings オブジェクト（JQUANTS_REFRESH_TOKEN, KABU_API_BASE_URL, SLACK_* 等）
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news(conn, target_date, api_key=None): raw_news を集約して OpenAI へ送信 → ai_scores に保存
    - regime_detector.py
      - score_regime(conn, target_date, api_key=None): ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して market_regime に保存
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / token refresh / rate limiter）
    - pipeline.py
      - ETL の高レベル制御（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
      - ETLResult データクラス
    - news_collector.py
      - RSS フィード取得・正規化・SSRF 対策・raw_news 保存ロジック
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・calendar_update_job
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）DDL と初期化ユーティリティ
    - etl.py
      - pipeline.ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value
    - feature_exploration.py
      - calc_forward_returns / calc_ic / factor_summary / rank
  - ai, data, research の各モジュールは DuckDB 接続を受け取り DB 操作を行います。

---

## 環境変数（要約）

最低限必要なもの:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（ETL 実行時に必要）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- KABU_API_PASSWORD — kabu ステーション API を使う場合
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知を使う場合

運用設定:
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config.py の .env 自動読み込みを無効化できます（テスト時に便利）。

---

## 開発・テストに関するメモ

- DuckDB を使っているため、SQL を直接実行してテーブルの状態を確認できます。
- OpenAI / J-Quants 呼び出し部分はリトライやフェールセーフを備えていますが、ローカルテストでは API 呼び出しをモックすることを推奨します（各モジュールは _call_openai_api 等を内部で分離しており、ユニットテストで patch しやすい設計です）。
- news_collector は外部ネットワークへアクセスするため、テスト時は _urlopen をモックしてください。

---

## 参考（注意点）

- 多くの処理は「ルックアヘッドバイアス」を防ぐ設計になっています（関数内で date.today() や datetime.today() を直接参照しない等）。バックテスト用途では、ETL によるデータ取得タイミングを適切に管理してください。
- J-Quants の利用には API 利用規約、課金、レート制限の遵守が必要です。
- OpenAI 利用時は API 利用料が発生します。大量バッチ処理の実行はコストに注意してください。

---

README で扱ってほしい追加の項目（例: CLI 実行方法、systemd ユニット例、Dockerfile、具体的な依存バージョン等）があれば教えてください。必要に応じて追記・補完します。