# KabuSys

日本株向けのデータ基盤・研究・自動売買支援ライブラリです。  
DuckDB を使ったデータETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定トレース）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的を持ったモジュール群を含みます。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）と DuckDB への保存（ETL）
- RSS ニュース収集・前処理と OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究用のファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → executions のトレース可能化）
- 設定管理（.env / 環境変数）

設計上、バックテストでのルックアヘッドバイアスを防ぐ工夫（日時の明示、DBクエリの排他条件、API呼び出し箇所の限定）を行っています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - news_collector：RSS 収集と前処理（SSRF 対策・トラッキング除去）
  - quality：データ品質チェック（欠損/スパイク/重複/日付不整合）
  - audit：監査ログ（監査用テーブル作成・初期化）
  - calendar_management：営業日判定・次/前営業日取得・カレンダー更新ジョブ
  - stats：zscore_normalize 等の汎用統計ユーティリティ
- ai
  - news_nlp.score_news(conn, target_date, api_key=None)：ニュースを集約して銘柄ごとに LLM スコアを ai_scores テーブルへ書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None)：MA とマクロニュースを合成して market_regime に書き込み
- research
  - calc_momentum, calc_value, calc_volatility（prices_daily / raw_financials ベース）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量解析）
- 設定管理
  - kabusys.config.settings：.env/.env.local の自動読み込み（プロジェクトルート検出）、必須環境変数チェック

---

## セットアップ手順

1. Python 環境（3.9+ 推奨）を用意します。仮想環境を推奨します。

2. 必要パッケージをインストールします（例）:
   - 最低限必要なライブラリ（例）:
     - duckdb
     - openai
     - defusedxml
   - pip 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

3. 環境変数の設定:
   - プロジェクトルートに .env または .env.local を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（settings.jquants_refresh_token）
     - KABU_API_PASSWORD    : kabu API パスワード（kabu ステーション連携用）
     - SLACK_BOT_TOKEN      : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID     : 通知先 Slack チャンネル ID
   - OpenAI の API は直接関数呼び出しで api_key を渡すか、環境変数 `OPENAI_API_KEY` を設定してください（ai モジュールは環境変数を参照します）。

   参考（.env の例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データディレクトリ作成（必要に応じて）:
   ```
   mkdir -p data
   ```

---

## 使い方（よく使う例）

以下は Python REPL / スクリプトでの利用例です。DuckDB 接続は settings.duckdb_path のデフォルトを利用します。

- 基本インポート:
  ```python
  import duckdb
  from kabusys.config import settings
  ```

- DuckDB 接続:
  ```python
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務を差分取得して保存、品質チェックを実行）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーを環境変数に設定している、または api_key を渡す）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み件数: {written}")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査専用 DB を作る／スキーマを作成）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- データ品質チェック（単体実行）:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意:
- OpenAI 呼び出しは API レートや料金に依存します。テスト時は ai モジュールの内部 API 呼び出し関数をモック可能です（コード内でその旨がコメントされています）。
- J-Quants のトークンリフレッシュ・レート制限対応は実装済みですが、API 使用時は利用規約とレートに注意してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys）パッケージの主要モジュール:

- __init__.py
- config.py
  - 環境変数読み込み・Settings（.env 自動ロード、必須チェック）
- ai/
  - __init__.py
  - news_nlp.py             - ニュースを銘柄別に集約し LLM でスコア付け
  - regime_detector.py      - 市場レジーム判定（MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py       - J-Quants API クライアント（fetch/save、認証、RateLimiter）
  - pipeline.py             - ETL パイプライン（run_daily_etl 等）
  - etl.py                  - ETLResult 再エクスポート
  - news_collector.py       - RSS 取得・前処理（SSRF 対策等）
  - quality.py              - データ品質チェック
  - stats.py                - zscore_normalize 等
  - calendar_management.py  - 市場カレンダー更新・営業日ユーティリティ
  - audit.py                - 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py      - momentum/value/volatility 等
  - feature_exploration.py  - forward returns / IC / summary / rank

---

## 設定・動作に関する補足

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストや外部実行環境でこれを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings クラスは一部値にデフォルトを持ちます（例: KABUS_API_BASE_URL、DUCKDB_PATH 等）。必須トークンがない場合は起動時に ValueError を発生させます。
- J-Quants クライアントは内部で固定間隔の RateLimiter を用いて 120 req/min を尊重します。401 受信時は自動でリフレッシュして1回リトライします。
- ニュース収集では SSRF 対策・レスポンスサイズ制限・トラッキングパラメータ除去等の安全対策を行っています。

---

## トラブルシューティング

- OpenAI の呼び出しでエラーが出る／API キーがない:
  - 環境変数 `OPENAI_API_KEY` を設定するか、score_news/score_regime に api_key 引数を渡してください。
- J-Quants トークン周りの 401 や通信エラー:
  - JQUANTS_REFRESH_TOKEN が正しいか確認してください。get_id_token() が失敗する場合はログを確認してください。
- DuckDB にテーブルがない/スキーマ初期化が必要:
  - audit.init_audit_db() や自前のスキーマ初期化コードを呼び出してテーブルを作成してください。
- ETL が期待通りデータを取得しない:
  - run_daily_etl は market_calendar を先に更新して営業日補正を行います。ネットワーク・認証エラーや API 側の制限をログで確認してください。

---

この README はコードベース（src/kabusys）を元に要点をまとめたものです。利用例や運用スクリプトはプロジェクト側で用途に合わせて追加してください。必要があれば、セットアップ用のスクリプト / サービス定義（systemd / cron / Airflow など）や詳細な運用手順も別途作成できます。