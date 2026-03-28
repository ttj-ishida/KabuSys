# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注トレーサビリティ）などのユーティリティを含みます。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価・財務・市場カレンダー等のデータを差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集・前処理、および OpenAI を用いた銘柄単位のニュースセンチメントスコア生成
- ETF の移動平均乖離とマクロニュースの LLM センチメントを組み合わせた市場レジーム判定
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order_request → executions）用のスキーマ初期化ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計方針として、ルックアヘッドバイアスの排除、冪等性（DB 保存の ON CONFLICT）、API リトライ・レート制御、外部呼び出しのフェイルセーフなどを重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_* 関数
  - カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - ニュース収集: RSS フェッチ / 前処理 / raw_news への保存補助（news_collector）
  - データ品質チェック: run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - 監査ログ初期化: init_audit_schema, init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai/
  - ニュース NLP: score_news（銘柄ごとの ai_scores 書き込み）
  - 市場レジーム判定: score_regime（ETF 1321 の MA とマクロセンチメント合成）
- research/
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank
- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクトによる環境変数管理
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

1. リポジトリを取得してパッケージをインストール（開発モード推奨）
   - 例:
     - git clone <repository>
     - cd <repository>
     - python -m venv .venv
     - source .venv/bin/activate
     - pip install -e .

2. 必要な主な依存パッケージ
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリの urllib 等も使用）
   - 例:
     - pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — （通知機能を使う場合）Slack ボットトークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - KABU_API_PASSWORD — kabuステーション API のパスワード（発注を行う場合）
     - OPENAI_API_KEY — OpenAI を使う関数を直接呼ぶ場合はここに設定するか、関数呼び出し時に api_key を渡す
   - 任意（デフォルトあり）:
     - KABUSYS_ENV = development | paper_trading | live (default: development)
     - LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL
     - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 （自動ロードを無効化）
     - DUCKDB_PATH（default: data/kabusys.duckdb）
     - SQLITE_PATH（default: data/monitoring.db）
     - KABU_API_BASE_URL（default: http://localhost:18080/kabusapi）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方

ここでは代表的な利用例を紹介します。すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取ります。

- DuckDB 接続を作る（デフォルトファイルは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- ETL を日次実行（市場カレンダー、株価、財務を差分取得して品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコア生成（OpenAI API を使用）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {n_written}")
  ```
  注意: score_news は対象時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）内のニュースを処理します。テスト用に _call_openai_api をモック可能です。

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  # market_regime テーブルに書き込みます
  ```

- 監査ログ用 DB 初期化（監査専用 DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要なテーブル・インデックスが作成される
  ```

- 監査スキーマを既存接続に追加
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # transactional=False がデフォルト
  ```

- リサーチ用: モメンタム計算
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  recs = calc_momentum(conn, target_date=date(2026,3,20))
  # recs は各銘柄ごとの dict のリスト
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

重要な設計上の注意：
- ルックアヘッドバイアス防止のため、各モジュールは date.today / datetime.today を内部で直接参照しない設計です。必ず target_date を明示するか run_daily_etl の引数で日付を与えてください。
- OpenAI / J-Quants などの外部 API は呼び出しコスト・レート制限・課金が発生します。テスト時はモックすることを推奨します。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイルとフォルダ構成（抜粋）です：

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
    - ...（他ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (README の先頭で __all__ に含まれていますが、実装は省略または別ファイル)
  - execution/ (発注関連のモジュールがある想定)
  - strategy/ (戦略層のモジュールがある想定)

実際のリポジトリではさらにテスト、ドキュメント、CLI スクリプト等が含まれる可能性があります。

---

## 環境変数一覧（代表）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（関数引数で上書き可能）
- SLACK_BOT_TOKEN (必須 / 通知機能使用時)
- SLACK_CHANNEL_ID (必須 / 通知機能使用時)
- KABU_API_PASSWORD (必須 / 発注機能使用時)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite モニタリング DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — ログレベル
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

settings オブジェクト経由でアクセスできます：
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live, settings.jquants_refresh_token)
```

---

## 開発・テストのヒント

- OpenAI 呼び出しや外部 HTTP はユニットテストでモック可能です（各モジュール内で _call_openai_api や _urlopen を差し替えられるように設計されています）。
- .env の自動ロードはプロジェクトルートの検出（.git または pyproject.toml）を行います。CI やユニットテストで制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、明示的に環境をセットしてください。
- DuckDB をインメモリで使う場合は db_path に ":memory:" を渡すことでテストが容易になります（例: init_audit_db(":memory:")）。

---

## ライセンス・貢献

（リポジトリの LICENSE や貢献ガイドラインをここに記載してください。）

---

不明点や追加で README に含めたいサンプルや CLI 例があれば教えてください。README の内容を用途に合わせて調整します。