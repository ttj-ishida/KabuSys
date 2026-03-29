# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。  
ETL（J-Quants）、データ品質チェック、ニュース収集・NLP（OpenAI経由）、市場レジーム判定、ファクター計算、監査ログなどを含むモジュール化されたコードベースです。

---

## プロジェクト概要

KabuSys は次のような目的で設計されています。

- J-Quants API からの差分取得（株価・財務・市場カレンダー）と DuckDB への冪等保存
- ニュースの収集と OpenAI（gpt-4o-mini）を用いた銘柄別センチメント生成
- ETF の移動平均乖離とマクロニュースセンチメントを組み合わせた市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注／約定の監査用テーブル初期化（監査ログ）

設計上の特徴：
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない等）
- API呼び出しに対するリトライとフェイルセーフ（失敗時はスコアを 0 にフォールバックする等）
- DuckDB を中心としたローカル分析基盤（ETL・研究処理に最適化）

---

## 主な機能（モジュール一覧）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート基準）と環境変数管理
- kabusys.data
  - jquants_client: J-Quants API クライアント（認証、取得、DuckDB保存）
  - pipeline: 日次 ETL 実行（run_daily_etl 等）
  - quality: データ品質チェック（run_all_checks 等）
  - calendar_management: 市場カレンダー管理・営業日判定
  - news_collector: RSS 取得・前処理・raw_news 保存
  - audit: 監査ログ（signal_events, order_requests, executions）テーブル初期化
  - etl: ETLResult の再エクスポート
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント生成（OpenAI）
  - regime_detector.score_regime: ma200 とマクロニュースで市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提条件

- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリのみで多くは実装されています）
- J-Quants API と OpenAI の API キー（環境変数で提供）

※ 実際のインストール要件はプロジェクトの packaging/requirements に従ってください。

---

## セットアップ手順（ローカル実行向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .\.venv\Scripts\activate     # Windows (PowerShell 例)
   ```

3. 必要なパッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはパッケージ化されている場合:
   # pip install -e .
   ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key       # AI モジュール利用時
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）
     SLACK_BOT_TOKEN=your_slack_token
     SLACK_CHANNEL_ID=your_slack_channel
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development   # development | paper_trading | live
     LOG_LEVEL=INFO
     ```

---

## 使い方（主要な例）

以下は Python REPL / スクリプトからの簡単な利用例です。

- DuckDB 接続（設定にあるパスを利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を None にすると今日（環境）を基準に実行
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- ファクター計算 / 研究系関数
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026,3,20))
  # z-score 正規化
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db, init_audit_schema

  # 監査専用 DB を作る例
  audit_conn = init_audit_db("data/audit.duckdb")
  # 既存接続に対しては init_audit_schema(conn, transactional=True)
  ```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: デフォルト DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化（テスト用）

注意: kabusys.config はプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を探索して `.env` / `.env.local` を自動で読み込みます。

---

## ディレクトリ構成（主なファイル）

（下記は src/kabusys の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py          # ニュース NLP / score_news
    - regime_detector.py   # 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント + DuckDB 保存
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - etl.py               # ETLResult 再エクスポート
    - quality.py           # データ品質チェック
    - stats.py             # 統計ユーティリティ（zscore_normalize）
    - calendar_management.py  # 市場カレンダー管理（営業日判定等）
    - news_collector.py    # RSS ニュース収集
    - audit.py             # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py   # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py  # calc_forward_returns / calc_ic / factor_summary / rank

---

## 実装上の注意点 / 動作特性

- OpenAI 呼び出し部分はリトライ・フェイルセーフが組み込まれており、API 失敗時はスコアを 0.0 にフォールバックし例外を上位に伝播しない設計が多く採用されています（ニュースNLP・レジーム判定）。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で行われます。
- ETL や品質チェックは個別に例外処理され、1 ステップ失敗でも残り処理を継続するようになっています。
- ルックアヘッドバイアス対策として、各モジュールは target_date 引数を明示的に受け取り、内部で現在時刻を参照しない設計が意図されています。
- news_collector には SSRF 対策、XML パース防護（defusedxml）、レスポンスサイズ上限などの安全対策が実装されています。

---

## よくある質問・トラブルシューティング

- .env が自動で読み込まれない場合
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。プロジェクトルートに .env または .env.local が存在するか確認してください。
- OpenAI レスポンスが不正（JSONパースエラー等）
  - ライブラリ側でパース失敗時はログを出して無視（空スコア）にする設計です。API レスポンスの整合性、モデルの応答フォーマット設定（JSON Mode）を確認してください。
- DuckDB に接続できない・ファイルパスにディレクトリがない
  - デフォルト path（data/kabusys.duckdb）の親ディレクトリを作成するか、settings.duckdb_path を適切に設定してください。

---

この README はコードベースの主要機能・利用方法の概要を示しています。実運用や本格的な開発を行う際は、ソース内の docstring・ログ出力・各モジュールの設計コメントを参照してください。必要であれば、README に実行スクリプト例（cron / systemd / Airflow / CI）や依存関係を追加で記載できます。