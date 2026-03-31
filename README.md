# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants / RSS / OpenAI（LLM）等を組み合わせて、データ取得（ETL）、品質チェック、ニュースNLP、市場レジーム判定、ファクター計算、監査ログ管理などの機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得（ETL）
  - J-Quants API から株価日足、財務データ、JPX マーケットカレンダーを差分取得・保存（ページネーション・レート制御・リトライ対応）
  - ETL 結果を ETLResult として集約
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェックを実行（QualityIssue を返す）
- ニュース収集 / NLP
  - RSS 取得・前処理（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（score_news）
- 市場レジーム判定（score_regime）
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して 'bull'/'neutral'/'bear' を判定
- 研究用ユーティリティ
  - ファクター計算（モメンタム／ボラティリティ／バリューなど）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 監査ログ（audit）
  - シグナル → 発注 → 約定までをトレースする監査テーブル定義・初期化ユーティリティ
- マーケットカレンダー管理（calendar_management）
  - 営業日判定、前後営業日の取得、夜間バッチ更新ジョブなど

---

## 動作要件（推奨）

- Python 3.10+
- DuckDB（Python パッケージ）
- OpenAI Python SDK（OpenAI API を呼ぶ部分を利用する場合）
- defusedxml（RSS のパースに安全対策）
- 標準ライブラリ以外の主な依存:
  - duckdb
  - openai
  - defusedxml

プロジェクト固有の環境変数を多数参照します（下記参照）。

---

## セットアップ手順

1. リポジトリをクローン（またはプロジェクトファイルを取得）:

   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化:

   macOS / Linux:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. 必要パッケージをインストール（例）:

   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに pyproject.toml / requirements.txt があればそれを利用してください。）

4. 環境変数を設定（.env/.env.local を使用可能）。以下は主要な必須変数の例です（詳細は下記参照）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注等を行う場合）
   - SLACK_BOT_TOKEN: Slack 通知用トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）

   自動で .env / .env.local をプロジェクトルートから読み込みます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 環境変数（主な一覧）

- 認証／API
  - JQUANTS_REFRESH_TOKEN (必須)
  - OPENAI_API_KEY (LLM を利用する関数呼び出し時に引数で渡すことも可)
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)

- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)

- データベース / パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視ログ用、デフォルト: data/monitoring.db)
  - PID_FILE_PATH (実行監視用、デフォルト: data/execution.pid)

- 実行環境 / ログ
  - KABUSYS_ENV (development / paper_trading / live)
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

その他は config.Settings クラスで参照されています。必須のものが未設定だと例外が発生します（Settings のプロパティ参照時）。

---

## 使い方（主要な利用例）

以下は Python スクリプト/REPL からの簡単な利用例です。すべての例は duckdb の接続オブジェクト（kabusys.data が期待）を渡します。

- DuckDB 接続のサンプル:

  ```python
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')  # Path は環境に合わせて変更
  ```

- 日次 ETL の実行:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # ETL を今日で実行
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコア付け（銘柄ごとの ai_scores へ書き込む）:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーを環境変数に設定済みであれば api_key=None で可
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"スコアを書き込んだ銘柄数: {written}")
  ```

- 市場レジームスコアの算出:

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ（audit）スキーマの初期化:

  ```python
  from kabusys.data.audit import init_audit_db

  # ファイルベース DB を初期化し接続を受け取る
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ユーティリティの例（モメンタム計算）:

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

各関数はドキュメント文字列で挙動・戻り値・例外を詳述しています。LLM 呼び出しを含む関数は API キーの未設定時に ValueError を送出します。

---

## 注意点・設計方針（重要）

- Look-ahead bias 対策
  - 多くの関数で datetime.today()/date.today() を直接参照せず、target_date を明示的に渡す設計になっています。バックテスト等でデータ知見の漏洩を避けるため、ターゲット日を明示してください。
- 冪等性
  - ETL の保存関数は ON CONFLICT（または同等の手段）で既存データを上書きするため複数回実行しても安全な作りです。
- フェイルセーフ
  - LLM/API 呼び出し失敗時は多くの場合フォールバック（例えば macro_sentiment=0.0）して処理を続行します。致命的な場合は例外が上がります。
- セキュリティ
  - RSS 取得では SSRF 対策、XML の安全パーサ(defusedxml)、レスポンスサイズ制限等を行っています。
- テスト容易性
  - 内部の API 呼び出し（OpenAI など）はテスト時に差し替え可能（モック）を想定した設計です。

---

## ディレクトリ構成（抜粋）

src/kabusys パッケージ内の主要ファイル・モジュール:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py          - ニュースセンチメント解析（score_news）
    - regime_detector.py   - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    - J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py          - ETL パイプライン（run_daily_etl 等）
    - etl.py               - ETLResult の再エクスポート
    - calendar_management.py - マーケットカレンダー管理（営業日判定）
    - news_collector.py    - RSS 収集（fetch_rss など）
    - quality.py           - データ品質チェック
    - stats.py             - 統計ユーティリティ（zscore_normalize）
    - audit.py             - 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py   - モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py - 将来リターン/IC/統計サマリー 等
  - ai/、data/、research/ 以下に設計コメントと詳細な docstring を含みます。

（上記は主なファイルの概要です。各モジュールにより細かなユーティリティ関数が定義されています。）

---

## 追加情報

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行われます。環境によって自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部はモデル名やリトライ方針がコード内で定義されています。利用時は API 料金とレート制限に注意してください。
- DuckDB スキーマ（テーブル定義）はデータ保存関数の前提に依存します。新規環境で初期スキーマを作成するユーティリティがリポジトリに含まれている場合はそれを利用してください（audit.init_audit_db のような関数は監査テーブルの初期化を行います）。

---

README に書かれている使い方はコードベースの公開 API に基づく参考例です。実運用ではログ設定・エラーハンドリング・トークン管理（安全な保管）等を適切に実装してください。質問や利用例の追加要望があればお知らせください。