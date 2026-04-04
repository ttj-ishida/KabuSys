# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、ファクター計算・リサーチ、監査ログ、マーケットカレンダー管理などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの差分取得と DuckDB への保存（ETL）
- RSS ニュース収集と LLM による銘柄別センチメント付与
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- ファクター計算・特徴量解析（研究用）
- データ品質チェック、マーケットカレンダー管理
- 発注〜約定のトレーサビリティ（監査ログ用スキーマ）

設計上の特徴：
- DuckDB を中心に SQL + Python で高速に処理
- Look-ahead バイアス回避（関数は明示的な target_date を受け取る）
- API 呼び出しはリトライ／バックオフ・レート制御を実装
- 冪等保存（ON CONFLICT / upsert）を重視

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（差分取得、保存）
  - pipeline: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得と前処理
  - calendar_management: JPX カレンダー管理（営業日判定、update job）
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - audit: 監査ログ（signal / order_request / executions テーブル定義・初期化）
  - stats: 汎用統計（Zスコア正規化）
- ai/
  - news_nlp.score_news: ニュースを LLM で解析して ai_scores に書き込み
  - regime_detector.score_regime: ma200 とマクロセンチメントを合成して market_regime に書き込み
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー等

---

## セットアップ手順

前提
- Python 3.10+（typing の | アノテーションを使用）
- DuckDB を利用可能な環境

1. リポジトリをチェックアウト（パッケージルートに `pyproject.toml` がある想定）

2. 必要パッケージをインストール（例）:
   pip install duckdb openai defusedxml

   ※プロジェクト用に requirements.txt/poetry を用意している場合はそちらを利用してください。

3. パッケージを開発モードでインストール（任意）:
   pip install -e .

4. 環境変数 / .env の設定

   Settings は環境変数から設定値を読み込みます（パッケージ読み込み時にプロジェクトルートの `.env` / `.env.local` を自動読み込みします。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   最低限設定が必要なキー:
   - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants の refresh token
   - KABU_API_PASSWORD      (必須) — kabuステーション API パスワード

   その他よく使うキー（任意・デフォルトあり）:
   - OPENAI_API_KEY         — OpenAI API キー（score_news/score_regime 呼び出し時に引数で渡すことも可能）
   - KABU_API_BASE_URL      — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - DUCKDB_PATH            — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            — 監視用 sqlite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH, KILL_FLAG_PATH 等の監視関連

   例 `.env`（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=yyyy...
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単なコード例）

以下は Python REPL / スクリプトでの利用例です。

- DuckDB 接続の作成:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー / 株価 / 財務 / 品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を省略すると今日（内部で営業日に調整）
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI API キーは環境変数 `OPENAI_API_KEY` または api_key 引数で指定）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  t = date(2026, 3, 20)
  mom = calc_momentum(conn, t)
  val = calc_value(conn, t)
  vol = calc_volatility(conn, t)
  ```

- 監査ログスキーマ初期化（DuckDB ファイルを新規作成する例）:
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # settings.duckdb_path を使うか別ファイルを指定
  audit_conn = init_audit_db(settings.duckdb_path)
  ```

注意点:
- score_news / score_regime は OpenAI の Chat API（gpt-4o-mini 等）を利用します。API 呼び出しが必要なため `OPENAI_API_KEY` を設定するか api_key 引数にキーを渡してください。API 失敗時はフェイルセーフとしてスコア 0 やスキップにフォールバックする実装です。
- jquants_client では `JQUANTS_REFRESH_TOKEN` が必須です。get_id_token() がこれを参照します。

---

## よく使う API 一覧（モジュール / 関数）

- kabusys.config.settings — 設定オブジェクト（jquants_refresh_token, kabu_api_password, duckdb_path 等）
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...) — 日次 ETL
- kabusys.data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...)
- kabusys.data.news_collector.fetch_rss(url, source) — RSS を取得して記事リストを返す
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) — ニュースセンチメントを ai_scores に書込
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime に書込
- kabusys.research.* — ファクター/統計関数
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn) — 監査ログ初期化

---

## ディレクトリ構成

以下は主要なファイル/モジュールのツリー（src/kabusys 以下の要約）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM スコアリング（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - news_collector.py      — RSS 取得・前処理・DB 保存補助
    - calendar_management.py — JPX カレンダー管理・営業日ロジック
    - quality.py             — データ品質チェック
    - stats.py               — zscore_normalize 等
    - audit.py               — 監査ログスキーマ定義・初期化
    - etl.py                 — ETLResult の公開
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン・IC・summary

---

## 注意事項 / 運用上のヒント

- 環境変数自動読み込み:
  - パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を起点）を探索して `.env` / `.env.local` を自動読み込みします。テストでこの挙動を抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し:
  - LLM 呼び出しはリトライやタイムアウト、レスポンス検証を行っていますが、API 利用料金とレート制限に注意してください。
- DuckDB スキーマ:
  - ETL / audit 等で想定するテーブル定義が前提となります。初期化用のスキーマ生成関数がない箇所は、運用側で migrations 等を準備してください（audit.init_audit_schema は監査用DDLを提供します）。
- テスト:
  - LLM / ネットワーク呼び出しはパッチ差し替え (unittest.mock.patch) に対応する形で設計されています。ユニットテスト時は外部 API 呼び出しをモックすることを推奨します。

---

必要であれば、README に「SQL スキーマの例」「運用スクリプト（cron/airflow）」や「サンプル .env.example」のセクションを追加できます。どの情報を追加しますか？