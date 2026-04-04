# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
データ ETL、品質チェック、ニュース NLP / LLM 解析、リサーチ用ファクター計算、監査ログ（発注→約定トレース）などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータプラットフォームを構成する共通ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からのデータ取得（株価日足・財務・市場カレンダー）と DuckDB への差分 ETL
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集と LLM を用いた銘柄別センチメント算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 発注〜約定まで追跡可能な監査ログ（監査テーブルを DuckDB に初期化）

設計上の特徴：
- ルックアヘッドバイアスを避けるために内部で date.today() や datetime.today() を参照しない設計がなされています（関数に target_date を与える形）。
- DuckDB を主要なストレージとして使用し、冪等な保存（ON CONFLICT … DO UPDATE 等）とトランザクション管理を行います。
- API 呼び出しに対してリトライ・バックオフ・レート制御を行う実装が含まれます。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存用ユーティリティ）
  - pipeline / etl: 日次 ETL パイプライン（差分取得、保存、品質チェック）
  - news_collector: RSS 収集、前処理、raw_news テーブルへの冪等保存
  - quality: データ品質チェック（missing / spike / duplicates / date consistency）
  - audit: 発注・約定の監査テーブル定義・初期化ユーティリティ
  - calendar_management: JPX カレンダー管理・営業日判定
  - stats: 汎用統計ユーティリティ（zscore_normalize 等）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約して OpenAI でスコア化し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）200 日 MA 乖離とマクロニュースを合成して market_regime に保存
- research/
  - factor_research: モメンタム / ボラティリティ / バリューの定量ファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマンρ）、統計サマリー等

- config: .env ファイル・環境変数から設定を自動ロードするユーティリティ（自動ロードはプロジェクトルート検出に基づく、無効化フラグあり）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | 表記を使用しているため）
- Git が利用可能

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   （実際のプロジェクトでは requirements.txt / poetry などを用意してください）

4. 環境変数設定
   - プロジェクトルートに `.env`（と必要に応じて `.env.local`）を作成します。自動ロード順序は OS 環境変数 > .env.local > .env です。
   - 主要な環境変数例:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI の API キー（ai 機能を使う場合に必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: INFO 等
   - 自動 .env ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な例）

下記は Python REPL / スクリプトでの利用例です。

- DuckDB 接続を作る例:
  - import duckdb
  - conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- ETL（日次パイプライン）を走らせる:
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - result = run_daily_etl(conn, target_date=date.today())
  - print(result.to_dict())

- ニューススコアリング（AI）:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で設定

- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須

- 監査 DB を初期化:
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - # テーブルが作成される（UTC タイムゾーン設定等）

- J-Quants 認証トークン取得（ライブラリ内で自動的に管理されますが、個別に取得する場合）:
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # JQUANTS_REFRESH_TOKEN が必要

- リサーチ用ファクター計算:
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - records = calc_momentum(conn, target_date=date(2026,3,20))

注意点:
- AI 呼び出し部分は OpenAI SDK（新しい v1 SDK を想定）を使用しています。API のレスポンスや料金に注意してください。
- テスト時は内部の API 呼び出し関数（例: kabusys.ai.news_nlp._call_openai_api）をモックすることで外部呼び出しを回避できます。

---

## 設定（config モジュールのポイント）

- 自動 .env ロード
  - プロジェクトルートは __file__ の親階層を辿って `.git` または `pyproject.toml` から検出されます。見つからない場合は自動ロードをスキップします。
  - .env の読み込みは `.env` → `.env.local` の順で行い、`.env.local` は上書きします。
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます。

- 主要な設定アクセス例:
  - from kabusys.config import settings
  - settings.jquants_refresh_token
  - settings.duckdb_path
  - settings.env / settings.is_live / settings.log_level
  - 監視閾値 (cpu/memory/disk) や PID/kill flag のパスも settings で取得可能

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の src/kabusys 以下を示した簡易ツリー）

- src/kabusys/
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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (モジュールが存在する想定: __all__ に入っていますが省略)
  - strategy/ (戦略関連モジュール群: 実装に応じて配置)
  - execution/ (発注実行関連: 実装に応じて配置)

※ 上記はコードベースに含まれる主要モジュールを抜粋しています。

---

## 開発・運用に関する注意

- Python バージョンは最低 3.10 以上を推奨します（構文: X | Y などの使用）。
- DuckDB のバージョン依存や executemany の挙動差異に対応するコードになっています（空リストの executemany 等）。
- 外部 API（J-Quants / OpenAI）呼び出しにはレート制御・リトライが実装されていますが、本番運用では API レートやコストを監視してください。
- LLM 呼び出しはレスポンスのフォーマット・バリデーションを厳密に行う実装です。OpenAI 側の挙動変化に備えてテスト用のモックを活用してください。
- 監査ログは削除しない前提で設計されています。約定や失敗情報を必ず保存することでトレーサビリティを確保します。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認してください。
  - プロジェクトルートに .git または pyproject.toml が存在するか確認してください。自動検出はファイルの存在に依存します。

- OpenAI 呼び出しで失敗する
  - OPENAI_API_KEY が環境変数に設定されているか確認してください。
  - ネットワークや API レートにより一時エラーが発生した場合、実装側でリトライを行いますが失敗時はフェイルセーフとしてスコアを 0.0 にする等の挙動があります。

- DuckDB のスキーマが未作成でエラーになる
  - 必要テーブルは ETL や init 関数で作成されますが、監査用テーブルは init_audit_db / init_audit_schema を使って明示的に初期化してください。

---

必要であれば、特定モジュールの使い方（例: jquants_client のページネーション処理、news_collector の RSS フロー、quality の詳細なチェック結果の取り扱い）やサンプルスクリプトを追記します。どの部分の例を優先してほしいか教えてください。