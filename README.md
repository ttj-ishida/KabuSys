# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
J-Quants からの市場データ取得、DuckDB を用いたデータ保存・品質チェック、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究（ファクター計算）や監査ログの初期化までをカバーします。

---

## 概要

KabuSys は以下の主要機能を持つ Python パッケージです。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存・品質チェック・監査ログ
- RSS ニュース収集と LLM による銘柄別センチメント（news_nlp）
- マクロニュース + ETF MA を用いた市場レジーム判定（regime_detector）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析
- 設定の .env 自動ロード、ログレベル / 環境切替（development / paper_trading / live）

パッケージは src/kabusys 以下にモジュールを配置しています（duckdb 接続を多用）。

---

## 主な機能一覧

- data.jquants_client: J-Quants API クライアント（リトライ・レート制御・IDトークン自動リフレッシュ）
- data.pipeline: 日次 ETL（run_daily_etl）・個別 ETL ジョブ（prices/financials/calendar）
- data.quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
- data.news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策・サイズ制限）
- ai.news_nlp: OpenAI を用いた銘柄別センチメントスコア（score_news）
- ai.regime_detector: ETF（1321）MA とマクロセンチメント合成による市場レジーム判定（score_regime）
- research: ファクター計算・IC・統計サマリー（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）
- data.audit: 監査ログテーブル初期化（init_audit_schema / init_audit_db）
- config: 環境変数/.env 管理と Settings（settings オブジェクト）

---

## 動作要件

- Python 3.10 以上（型ヒントに | が使われているため）
- 主な依存ライブラリ:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外はインストールが必要）
- J-Quants API のリフレッシュトークン、OpenAI API キー、kabu API パスワードなどの環境変数

推奨: 仮想環境（venv / poetry / pipenv 等）で隔離して使用してください。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   例（pip）:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用）

4. .env ファイルの作成（プロジェクトルートに配置）
   - パッケージは起動時に自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   例 `.env`（必須項目は環境に応じて設定）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C....
   KABUSYS_ENV=development            # development|paper_trading|live
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. DuckDB 初期化（監査ログ用 DB を作る例）
   - Python REPL やスクリプトで:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # init_audit_db はテーブルとインデックスを作成します
   ```

---

## 使い方（主要な API と実行例）

以下は簡単な Python スニペット例です。実行には前述の環境変数設定とパッケージ依存のインストールが必要です。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date を指定しなければ今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai.news_nlp.score_news）を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored codes:", n_written)
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentums = calc_momentum(conn, date(2026, 3, 20))
  values = calc_value(conn, date(2026, 3, 20))
  vols = calc_volatility(conn, date(2026, 3, 20))
  ```

- 設定参照（環境変数の確認）:
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

注意点:
- OpenAI 呼び出しは API コストとレート制限があるため、実行は慎重に行ってください（モック可能）。
- ETL / API 呼び出しはネットワーク・認証に依存します。J-Quants の取得トークンや OpenAI の API キーを準備してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（data.jquants_client.get_id_token で使用）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（実行系で使用）
- SLACK_BOT_TOKEN: Slack 通知用トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル

任意 / デフォルトあり:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると自動 .env 読み込みを無効化
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: データ保存先（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）

---

## ディレクトリ構成

主要ファイル / ディレクトリのツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数/.env 管理（settings）
    - ai/
      - __init__.py
      - news_nlp.py                   — ニュース NLP（score_news）
      - regime_detector.py            — 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py             — J-Quants API クライアント（fetch/save）
      - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
      - etl.py                        — ETLResult のエクスポート
      - news_collector.py             — RSS 収集・前処理
      - quality.py                    — データ品質チェック
      - stats.py                      — 統計ユーティリティ（zscore_normalize）
      - calendar_management.py        — 市場カレンダー管理
      - audit.py                      — 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py            — ファクター計算（momentum/value/volatility）
      - feature_exploration.py        — 将来リターン / IC / 統計サマリー
    - ai/、data/、research/ は主要機能群（上に詳述）
- pyproject.toml / setup.py 等（プロジェクトルートに存在する想定）
- .env, .env.local（プロジェクトルートで自動読み込み）

---

## 注意事項・設計上のポイント

- Look-ahead bias 回避:
  - ai モジュール・ETL は date 引数を明示的に受け取り、datetime.today()/date.today() を直接参照しないよう設計されています。
  - prices_daily 等のクエリは target_date 未満（排他）を使う等の工夫があります。

- リトライ / フェイルセーフ:
  - OpenAI/J-Quants へのリクエストはリトライ・エクスポネンシャルバックオフを実装。API 失敗時はフェイルセーフ（ゼロスコアやスキップ）で継続するところが多いです。

- セキュリティ:
  - RSS 収集は SSRF 防止、XML 安全パーサ（defusedxml）、レスポンスサイズ制限などを実装しています。
  - J-Quants トークンは .env に置くか環境変数で管理してください。

---

## 開発・テスト

- テスト環境では自動 .env 読み込みが邪魔になる場合があるため:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しや外部 API はモックしてユニットテストを実行してください（モジュール内で _call_openai_api 等を patch 可能）。

---

もし README に含めてほしい追加情報（例: CI 設定、より詳しい .env.example、実運用時の cron 設定例や systemd サービス例など）があれば教えてください。必要に応じて追記します。