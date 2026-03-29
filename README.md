# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買（リサーチ・ETL・AI スコアリング・監査ログ）を目的とした Python パッケージです。J-Quants API や RSS ニュース、OpenAI（LLM）を用いた処理を含み、DuckDB を中心にデータを保存・解析します。

主な設計方針：
- ルックアヘッドバイアスを避ける（date/target_date を明示的に扱う）
- DuckDB を用いた効率的な SQL + Python 処理
- 冪等性（ON CONFLICT 等）・リトライ・レート制御・フェイルセーフ設計
- 外部 API 呼び出しは明示的に安全対策（SSRF、防御的 XML パース 等）を実装

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env ファイル自動ロード（プロジェクトルート検出、OS 環境優先）
  - 必須環境変数の明示的チェック

- データ ETL（J-Quants 経由）
  - 株価日足（OHLCV）取得・保存（ページネーション対応・レート制御・再取得（backfill））
  - 財務データ（四半期）取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分更新・品質チェック（欠損・重複・スパイク・日付整合性）

- ニュース収集 / NLP
  - RSS フィードからのニュース収集（SSRF/サイズ制限/トラッキング除去）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニュースセンチメント算出（ai_scores への保存）
  - マクロニュースを使った市場レジーム判定（ma200 と LLM センチメントの合成）

- 研究ユーティリティ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化

- 監査ログ（オーダー追跡）
  - signal_events / order_requests / executions のスキーマ提供
  - 監査テーブルの初期化ユーティリティ（DuckDB）

---

## セットアップ手順

前提
- Python 3.10+（typing に | を使うため）
- DuckDB が利用可能（Python パッケージ duckdb を使用）
- J-Quants API と OpenAI API のキー（環境変数設定を推奨）

1. レポジトリをクローンしてインストール（開発モードの例）

   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 必要な依存パッケージ（例）

   ```
   pip install duckdb openai defusedxml
   ```

   実際の requirements はプロジェクトに合わせて管理してください。

3. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効にする場合は環境変数をセット：
     - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

   主な環境変数（必須は下記を参照）：
   - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD：kabu API のパスワード（必須）
   - KABU_API_BASE_URL：kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN：Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID：通知先チャネル ID（必須）
   - OPENAI_API_KEY：OpenAI API キー（AI スコアリング時に使用）
   - DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH：監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV：development / paper_trading / live（デフォルト development）
   - LOG_LEVEL：DEBUG/INFO/...（デフォルト INFO）

   Note: Settings クラスは必須値が未設定だと ValueError を投げます。

4. データベース準備（監査ログ用の例）

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # またはインメモリ
   # conn = init_audit_db(":memory:")
   ```

---

## 使い方（主要ユースケース）

以下は代表的な利用方法のサンプルです。実行はアプリケーションの用途に合わせて適宜ラップしてください。

- DuckDB 接続を作る・settings を使う例

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を指定しない場合は今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 単独の ETL（株価/財務/カレンダー）を個別で呼ぶ

  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  # それぞれ conn と target_date を渡す
  ```

- ニュースのスコアリング（OpenAI API キーを env または引数で指定）

  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を None にすると環境変数 OPENAI_API_KEY を参照
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 市場レジーム判定

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 研究系ファクター計算

  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  ```

- 統計ユーティリティ（Zスコア正規化）

  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m"])
  ```

- 監査スキーマ初期化（既存接続へ追加）

  ```python
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点：
- OpenAI 呼び出しには gpt-4o-mini（JSON Mode）を使用する想定です。API 利用量に注意してください。
- news_nlp / regime_detector は API 呼び出し失敗時にフォールバックする設計（0.0 を返す等）ですが、API キーが未設定だと ValueError を投げます。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なモジュールと役割（提供されたコードベースに基づく）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - RSS / raw_news を元に OpenAI で銘柄ごとのセンチメントを算出し ai_scores に保存
    - regime_detector.py
      - ETF 1321 の MA200 乖離 と マクロニュースの LLM センチメントを合成し market_regime を更新
  - data/
    - __init__.py
    - calendar_management.py
      - JPX カレンダー管理、営業日判定、calendar_update_job
    - pipeline.py
      - ETL の主エントリ（run_daily_etl）と個別 ETL ジョブ（prices/financials/calendar）
      - ETLResult データクラス
    - jquants_client.py
      - J-Quants API クライアント（取得 / 保存 / レート制御 / リトライ）
    - news_collector.py
      - RSS 収集と raw_news 保存（SSRF 対策、サイズ制限）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）DDL と初期化ユーティリティ
    - etl.py
      - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value などのファクター計算
    - feature_exploration.py
      - 将来リターン算出・IC・統計サマリー・ランク変換 等

（上記は抜粋です。プロジェクト全体の実装に応じて他ディレクトリ/ファイルが存在する場合があります。）

---

## 運用上の注意・ベストプラクティス

- 環境変数には秘密情報（J-Quants リフレッシュトークン、OpenAI キー、kabu API パスワード等）を使います。`.env` を GIT 管理しないでください。
- 本番（live）環境では KABUSYS_ENV=live を設定し、ログレベル・監視を厳格にしてください。
- OpenAI 呼び出しはコストが発生します。バッチサイズや頻度を調整して利用量を管理してください。
- DuckDB のファイルは定期的にバックアップしてください（特に監査ログ等は不可逆な重要データとなります）。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まなくなり、環境切り替えが容易です。
- モジュール内の API 呼び出し関数（_call_openai_api 等）はテスト用にパッチ可能な設計になっています。ユニットテストではモックを使って外部呼び出しを切り離してください。

---

必要であれば README に以下を追加します：
- インストール用の requirements.txt / pyproject.toml の推奨内容
- よくあるトラブルシュート（OpenAI レスポンスパース失敗、DuckDB の型エラー等）
- 具体的な運用スケジュール（ETL の cron/airflow 設定例）
- 追加のコード例・CLI や systemd / k8s でのデプロイ例

追加を希望する項目があれば教えてください。