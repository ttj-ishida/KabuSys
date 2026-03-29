# KabuSys

KabuSys は日本株のデータプラットフォームと自動売買のためのユーティリティ群をまとめたライブラリです。  
DuckDB を中心としたデータ収集（ETL）・品質チェック・ニュース収集・AIによるニュースセンチメント評価・市場レジーム判定・ファクター計算・監査ログ管理などの機能を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- データ取得 / ETL（J-Quants API 経由）
  - 日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーの差分取得（ページネーション・レート制御・リトライ対応）
  - DuckDB へ冪等的に保存（ON CONFLICT / UPDATE）
  - 日次パイプライン run_daily_etl による統合実行

- データ品質管理
  - 欠損チェック、スパイク検出、重複検出、日付整合性チェック
  - QualityIssue を返す集約 API（run_all_checks）

- カレンダー管理
  - market_calendar テーブルを使った営業日判定、次営業日/前営業日の取得、期間内営業日取得
  - JPX カレンダーの差分更新ジョブ

- ニュース収集（RSS）
  - RSS フィードの取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - タイムウィンドウやバッチ処理、レスポンス検証、リトライ処理を内蔵

- 市場レジーム判定（AI + テクニカル）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成で日次レジーム（bull/neutral/bear）を作成（score_regime）

- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（スピアマン・ランク相関）、統計サマリー、Zスコア正規化

- 監査ログ（audit）
  - signal → order_request → executions のトレーサビリティ用テーブルの定義・初期化（冪等）
  - 監査用 DuckDB 初期化ヘルパー

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェックと Settings オブジェクト（settings）

---

## 環境要件・依存パッケージ（想定）

- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- （プロジェクト内に requirements.txt がある場合はそちらを使用してください）

※ 実際のパッケージ名・バージョンはプロジェクトの配布物に合わせてください。

---

## セットアップ手順

1. リポジトリを取得（例）
   - git clone して下さい。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 例:
     - pip install duckdb openai defusedxml
   - またはプロジェクト配布の setup/pyproject / requirements.txt に従う:
     - pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成します。.env.example を参考にしてください。主に必要な変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
     - SLACK_BOT_TOKEN: Slack 通知用（任意/必要時）
     - SLACK_CHANNEL_ID: Slack チャンネルID（任意/必要時）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   - 自動 .env 読み込みはデフォルトで有効です。テスト等で無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース用ディレクトリ作成（必要に応じて）
   - data/ ディレクトリを作成しておくと便利です（DUCKDB_PATH の親ディレクトリを自動作成する関数もありますが手動で用意しておくと安心）。

---

## 基本的な使い方（例）

以下の例は Python スクリプトや REPL から実行する想定です。OpenAI を使う処理は OPENAI_API_KEY を環境変数で設定するか、関数の api_key 引数で渡します。

- DuckDB に接続して日次 ETL を実行する
  - 例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
    ```

- ニュースのセンチメントスコアを生成（score_news）
  - 例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026,3,20))
    print("scored:", n_written)
    ```

  - APIキーを関数引数で渡すことも可能（api_key="sk-..."）。

- 市場レジーム判定を実行（score_regime）
  - 例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20))
    ```

- 監査ログ用 DB の初期化
  - 例:
    ```python
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで監査テーブルが作成されます
    ```

- 研究用ユーティリティの利用（例）
  - calc_momentum, calc_volatility, calc_value は kabusys.research 以下から利用可能：
    ```python
    from kabusys.research import calc_momentum
    from datetime import date
    import duckdb

    conn = duckdb.connect("data/kabusys.duckdb")
    res = calc_momentum(conn, date(2026,3,20))
    ```

---

## 設定（Settings）と自動 .env 読み込み

- settings = kabusys.config.settings を通して設定値にアクセスできます（例: settings.jquants_refresh_token）。
- .env/.env.local はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に自動ロードされます。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須の環境変数が欠けている場合、Settings のプロパティは ValueError を投げます（例: JQUANTS_REFRESH_TOKEN が未設定）。

---

## よく使うコマンド・注意点

- OpenAI 呼び出しは外部 API を利用します。API 利用制限やコストに注意してください。
- J-Quants API 呼び出しはレート制御（120 req/min）・自動トークンリフレッシュ・リトライを備えています。
- ETL / ニュース / AI 処理は Look-ahead bias を避けるため、内部で date.today() / datetime.today() を不用意に参照しない設計になっています。必ず処理対象の日付を明示するか、ライブラリに沿って使用してください。
- DuckDB の executemany に空リストを与えると問題になるバージョンがあるため、内部で空チェックを行っています。

---

## ディレクトリ構成（抜粋）

以下はこのコードベースで提供されている主要モジュールのツリー（抜粋）です：

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
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - (その他 jquants_client で使用するユーティリティ等)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - (strategy/, execution/, monitoring/ は __all__ に含まれているがここでは省略)

各モジュールは機能別にまとまっており、data は ETL/保存/品質/カレンダーなどのデータ基盤処理、ai は OpenAI を使った NLP・レジーム判定、research は研究用ファクター・統計処理を提供します。

---

## トラブルシューティング（FAQ）

- 「環境変数が見つからない」と出る
  - settings のプロパティは必須変数がないと ValueError を投げます。`.env` を用意するか、OS 環境変数を設定してください。

- OpenAI 呼び出しで失敗する・429 が返る
  - ライブラリはリトライとバックオフ処理を組み込んでいますが、APIキーやクォータ、ネットワーク状態を確認してください。

- J-Quants から 401 が返る
  - jquants_client はリフレッシュトークンを使って id_token を再取得しリトライします。JQUANTS_REFRESH_TOKEN を正しく設定してください。

---

## 開発・テストについて

- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（単体テスト時に便利）。
- OpenAI 呼び出し部分は内部で _call_openai_api を定義しており、テスト時にモックで差し替え可能です。
- ネットワーク依存の処理（RSS 取得 / API 呼び出し）はモックしてユニットテストを作成することを推奨します。

---

もし README に追加したい事項（インストール方法の詳細、CI / Docker の手順、.env.example の内容など）があれば教えてください。必要に応じてサンプル .env.example も作成します。