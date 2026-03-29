# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）による銘柄センチメント評価、マーケットレジーム判定、リサーチ用ファクター計算、監査ログなどの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム取引に必要な以下の主要機能を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB への永続化（ETL パイプライン）
- データ品質チェック（欠損値・重複・スパイク・日付整合性）
- RSS ベースのニュース収集と前処理（raw_news テーブル）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（ai_scores）
- マクロ + テクニカルを組み合わせた市場レジーム判定（market_regime）
- リサーチ用のファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- 発注・約定までの監査ログ（signal / order_request / execution）スキーマと初期化ユーティリティ

設計上の注力点として、ルックアヘッドバイアス回避（日時参照の抑制）、フェイルセーフ（API失敗時の安全なフォールバック）、DuckDB を用いた効率的な SQL ベース処理、冪等性（ON CONFLICT/UPDATE）があります。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch/save 系）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS の安全な取得・正規化・保存）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date, api_key=None): ETF (1321) MA200 とマクロニュースを組み合わせて market_regime に書き込む
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数管理（.env 自動読み込み、必須設定の検証、settings オブジェクト）

---

## セットアップ手順

1. Python 環境を準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージをインストール
   - プロジェクトルートで:
     - pip install -e .
     - または requirements.txt がある場合: pip install -r requirements.txt

   ※ このコードベースは以下の主要依存が想定されています（プロジェクト側で管理してください）:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の依存がある場合は requirements.txt を参照）

3. 環境変数の設定
   - .env（プロジェクトルート） または OS 環境変数で下記を設定します。
   - 自動で .env を読み込む機能が有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 読み込み優先度: OS 環境変数 > .env.local（上書き） > .env（初期設定）。ただし OS 環境変数は保護されます。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN : Slack 通知用 BOT トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネル ID（必須）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : SQLite（モニタリング）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV : environment (development | paper_trading | live)（デフォルト: development）
   - LOG_LEVEL : ログレベル (DEBUG, INFO, WARNING, ERROR, CRITICAL)（デフォルト: INFO）
   - OPENAI_API_KEY : OpenAI API キー（ai.score_news / regime_detector で使用）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

下記は Python REPL やスクリプトでの利用例です。

- DuckDB 接続例:
  ```
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行:
  ```
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（OpenAI 必須）:
  ```
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数に設定しておく（または api_key 引数で渡す）
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定:
  ```
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  # OPENAI_API_KEY を環境変数に設定しておく（または api_key 引数で渡す）
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算:
  ```
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は [{'date': ..., 'code': 'XXXX', 'mom_1m': ..., ...}, ...]
  ```

- 監査ログ用 DuckDB 初期化:
  ```
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit 上で監査テーブルが作成されます
  ```

注意点:
- AI 呼び出し（news_nlp / regime_detector）は OpenAI API を利用します。API キーが必要です。API 呼び出しは失敗に対してフォールバック動作を行いますが、キーが未設定の場合は例外が発生します。
- DuckDB の executemany に空リストを与えるとエラーとなる点など、実装依存の挙動に注意してください（ライブラリ実装側で対策済みの関数が提供されています）。

---

## ディレクトリ構成（概要）

以下はソースツリー（src/kabusys）内のおもなファイル・モジュールです。

- kabusys/
  - __init__.py
  - config.py  — 環境変数・設定読み込み（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメントを ai_scores に書き込む
    - regime_detector.py — ETF MA200 とマクロニュースで market_regime を判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - etl.py                — ETL 結果クラス再エクスポート
    - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
    - news_collector.py     — RSS 取得・正規化・保存ロジック
    - quality.py            — データ品質チェック（QualityIssue）
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py    — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py— 将来リターン・IC・統計サマリー等

上記は主要モジュールのみ抜粋しています。細かいユーティリティや内部実装はそれぞれのモジュール内の docstring を参照してください。

---

## 補足 / 注意事項

- 自動 .env ロード:
  - config モジュールはパッケージのファイル位置を起点にプロジェクトルートを探索し、.git または pyproject.toml を見つけて .env / .env.local を読み込みます。
  - OS 環境変数が最優先で保護されます。テストや特殊ケースで自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ルックアヘッドバイアス対策:
  - 研究・AI モジュールは内部で datetime.today() を直接参照しない設計になっており、target_date を明示的に渡して過去データのみを使う実装です。バックテストでの利用時は target_date の扱いに注意してください。
- ログ:
  - settings.log_level でログレベルを制御できます（DEBUG/INFO/...）。  
- テスト:
  - テストモックのしやすさ（_call_openai_api の差し替えなど）を考慮した実装が散見されます。ユニットテストを作成する際は該当関数をパッチしてください。

---

必要であれば、README に「具体的な .env.example」「依存パッケージ一覧（requirements.txt）」「CLI ラッパー例」「ユースケース別ワークフロー（ETL 時系列 / AI バッチスケジューリング）」などの追記を作成します。どの情報を優先して追加しますか？