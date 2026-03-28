# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
DuckDB を中心としたデータ ETL、ニュースの NLP スコアリング、LLM を使った市場レジーム判定、ファクター計算、監査ログ（発注→約定トレース）などを提供します。

---

## 概要

このパッケージは次の領域をカバーします：

- データ取得・ETL（J-Quants API 連携、差分取得、品質チェック）
- ニュース収集と NLP による銘柄センチメント算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコア合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ 等）
- マーケットカレンダー管理（JPX カレンダー同期、営業日判定）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 各種ユーティリティ（統計正規化、品質チェック、URL 正規化、RSS 収集等）

設計上のポイント：
- Look-ahead バイアス対策（内部で date.today() を直接参照しない関数設計）
- DuckDB を用いたローカル永続化（冪等保存パターン）
- 外部 API 呼び出しに対するリトライ・バックオフ・レート制御
- LLM 呼び出しは JSON モードを使いレスポンスを厳密に検証

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env / 環境変数の自動ロード、設定ラッパ（settings）
- kabusys.data
  - jquants_client: J-Quants API の取得・保存（raw_prices, raw_financials, market_calendar 等）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得と raw_news への保存
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - audit: 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM に送り銘柄ごとの ai_score を ai_scores に書き込み
  - regime_detector.score_regime: ETF(1321) とマクロニュースを合成して market_regime を計算
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 前提条件

- Python 3.10 以上（型注釈に PEP 604 の union 型 `|` を使用）
- DuckDB
- OpenAI SDK（openai パッケージ）
- defusedxml（RSS の安全なパース）
- その他標準ライブラリ（urllib 等を使用）

推奨インストールパッケージ（例）:
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <このリポジトリ>
   cd <リポジトリ>
   ```

2. 開発用インストール（pip editable 推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   pip install -e .
   ```

3. 環境変数の設定
   プロジェクトルートに `.env`（または `.env.local`）を作成すると、自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   必須の環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - SLACK_BOT_TOKEN=<your_slack_bot_token>
   - SLACK_CHANNEL_ID=<your_slack_channel_id>
   - KABU_API_PASSWORD=<kabu_station_api_password>
   - OPENAI_API_KEY=<your_openai_api_key>  # news_nlp / regime_detector を環境変数で使う場合

   任意 / デフォルトを確認する設定:
   - KABUSYS_ENV=development|paper_trading|live  (default: development)
   - LOG_LEVEL=DEBUG|INFO|... (default: INFO)
   - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (default: data/kabusys.duckdb)
   - SQLITE_PATH (default: data/monitoring.db)

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. データベースディレクトリ作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトでの利用例です。

- DuckDB 接続を開く（settings.duckdb_path を利用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（J-Quants トークンは settings.jquants_refresh_token が使われます）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニューススコアリング（ai_scores への書き込み）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB ファイルを作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- カレンダー更新ジョブ（JPX カレンダー取得・保存）
  ```python
  from datetime import date
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print("保存件数:", saved)
  ```

注意点：
- LLM を使う関数（score_news, score_regime）は OPENAI_API_KEY を環境変数で読み取るか、api_key 引数で明示的に渡してください。
- J-Quants API の呼び出しには JQUANTS_REFRESH_TOKEN が必要です（get_id_token が内部で使用）。
- ETL や保存処理は DuckDB に対して BEGIN/COMMIT を適切に用いるため、他のトランザクションとの同時利用には注意してください。

---

## よく使う API（要点）

- run_daily_etl(conn, target_date=None, id_token=None, ...)
  - 日次の ETL（calendar/prices/financials + 品質チェック）をまとめて実行します。ETLResult を返します。

- score_news(conn, target_date, api_key=None)
  - 指定ウィンドウのニュースを LLM に送り、ai_scores テーブルを更新します。戻り値は書き込み銘柄数。

- score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を更新します。

- init_audit_db(path) / init_audit_schema(conn)
  - 監査テーブルを初期化します。init_audit_db はファイル作成とスキーマ初期化を行い接続を返します。

- jquants_client.get_id_token(refresh_token=None)
  - J-Quants の id_token を取得します（内部で refresh を行う）。

---

## ディレクトリ構成

（リポジトリの src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  # ニュース NLP スコアリング（score_news）
    - regime_detector.py           # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（fetch/save）
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - etl.py                       # ETL 結果型再エクスポート
    - news_collector.py            # RSS 収集と raw_news への保存
    - calendar_management.py       # カレンダー管理・営業日判定
    - quality.py                   # データ品質チェック
    - stats.py                     # 統計ユーティリティ（zscore_normalize）
    - audit.py                     # 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py           # ファクター計算（mom/value/vol）
    - feature_exploration.py       # 将来リターン / IC / 統計サマリー

---

## 開発・運用上の注意

- 自動で .env を読み込む動作は、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト時に便利）。
- OpenAI / J-Quants など外部 API 呼び出しにはレートや課金が伴います。テストではモック patch を使って外部呼び出しを防いでください。
- DuckDB に対する executemany の挙動（空リスト不可）など、実装上の細かい挙動に依存する箇所があります（pipeline 内で対応済み）。
- 監査テーブルは削除しない前提です（ON DELETE RESTRICT）。監査ログ保存は運用上重要です。
- LLM のレスポンスは JSON モードを前提にパース・検証を行っていますが、API の挙動変更や非期待値はログで警告しフォールバックする設計になっています。

---

## ライセンス・貢献

本プロジェクトに関するライセンス情報・貢献ガイドラインはリポジトリのルートに追記してください（この README はコードベースの概要説明に特化しています）。

---

何か動かしたい処理や、README に追加してほしい具体的な手順（例：Docker 化、CI 設定、サンプル .env.example のテンプレート）などがあれば教えてください。必要に応じて追記します。