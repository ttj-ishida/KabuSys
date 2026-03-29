# KabuSys

日本株向けのデータパイプライン・リサーチ・自動売買支援ライブラリです。  
DuckDB を用いたデータ管理、J-Quants API からの ETL、ニュースの収集・LLM による NLP スコアリング、リサーチ用ファクター計算、監査ログ（トレーサビリティ）等の機能を提供します。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援する内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への冪等保存（ETL）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI を用いたニュースセンチメント（銘柄・マクロ）評価（gpt-4o-mini を想定）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）テーブル管理

設計上の特徴として、バックテスト時のルックアヘッドバイアス防止（内部で date.today() を直接参照しない等）、API 呼び出しの堅牢なリトライ・レート制御、DuckDB を中心とした効率的な SQL 処理を採用しています。

---

## 機能一覧

- 環境変数管理（.env 自動読み込み、必須キーの取得）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限・トークン自動リフレッシュ・リトライ対応
- ETL パイプライン（run_daily_etl 等）
- ニュース収集（RSS）および前処理（SSRF 対策、トラッキング除去、記事ID生成）
- ニュース NLP（OpenAI）
  - 銘柄別センチメント（score_news）
  - マクロセンチメントと ETF MA を合成した市場レジーム判定（score_regime）
- 研究モジュール（research）
  - モメンタム / バリュー / ボラティリティ ファクター計算
  - 将来リターン計算・IC 計測・統計サマリー
- データ品質チェック（quality モジュール）
- 監査ログ（audit モジュール）
  - 監査テーブル生成・初期化（init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の union 型表記、型注釈の互換性のため）
- DuckDB が動作する環境

1. リポジトリをチェックアウト／クローンし、パッケージをインストール（開発モード推奨）:
   - 例:
     - pip install -e .
     - 依存例: duckdb, openai, defusedxml
     - 具体的には:
       pip install duckdb openai defusedxml

2. 環境変数（.env）を用意する
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注系を使う場合）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能がある場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
     - OPENAI_API_KEY — OpenAI API キー（score_news, score_regime を使う場合）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

3. 初期化（監査 DB の例）
   - 監査用 DuckDB を作る:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存コネクションにスキーマを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（代表的な API）

以下は主要な利用例です。実際はアプリケーション側のラッパーやジョブスケジューラから呼び出します。

1. DuckDB 接続を作って日次 ETL を実行する
   ```python
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=None)  # target_date=None は今日
   print(result.to_dict())
   ```

2. ニュースセンチメント（銘柄単位）を計算して ai_scores に保存
   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date
   import duckdb

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026, 3, 20))  # 曜日等の扱いは内部で管理
   print(f"written scores: {written}")
   ```

3. 市場レジーム判定（ETF 1321 の MA200 とマクロ記事の LLM スコア合成）
   ```python
   from kabusys.ai.regime_detector import score_regime
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 研究用ファクター計算
   ```python
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   momentum = calc_momentum(conn, date(2026, 3, 20))
   volatility = calc_volatility(conn, date(2026, 3, 20))
   value = calc_value(conn, date(2026, 3, 20))
   ```

5. ニュース（RSS）の取得（低レベル）
   ```python
   from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

   articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
   ```

注意点・運用上のヒント
- OpenAI を使う処理（score_news, score_regime）は API キー（OPENAI_API_KEY）が必要です。失敗時はフェイルセーフ（スコア 0.0）で継続するよう設計されていますが、API 呼び出し料やレートに注意してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- テスト時には外部 API 呼び出しや時間関数をモックする設計（_call_openai_api を patch するなど）になっています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（data, strategy, execution, monitoring を __all__ に含む）
- config.py — 環境変数 / 設定管理（.env 自動読み込み、必須変数チェック、設定オブジェクト settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（score_news, calc_news_window 等）
  - regime_detector.py — マクロセンチメント + ETF MA 合成による市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limit / retry）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集・前処理・raw_news 保存ロジック
  - calendar_management.py — 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（missing/spike/duplicates/date_consistency）
  - audit.py — 監査ログ（テーブル DDL / init_audit_schema / init_audit_db）
- research/
  - __init__.py
  - factor_research.py — Momentum / Value / Volatility 計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank

（strategy, execution, monitoring パッケージは __all__ に含まれていますが、この README に含まれるコードベースでは未提示のため、実装は別途存在する想定です。）

---

## 開発・テストに関する補足

- 多くの外部呼び出し（OpenAI, J-Quants, HTTP RSS）にはリトライやバックオフが組み込まれており、テスト時はこれらをモックして高速化できます。モジュール内に差し替え可能な内部関数（例: kabusys.ai.news_nlp._call_openai_api や kabusys.data.news_collector._urlopen）があります。
- DuckDB を用いたクエリは SQL 内でウィンドウ関数等を多用しているため、DuckDB バージョンに依存する挙動（型の扱い等）に注意してください。
- ETL / calendar 更新ジョブ等は部分失敗でも他の処理が継続するよう設計されています。結果は ETLResult や QualityIssue リストとして返されるため、呼び出し元でログや通知を行ってください。

---

この README はコードベースから抽出した情報に基づく概要です。実運用前に各モジュールの詳細ドキュメント（関数の docstring）を確認し、必須環境変数や API レート制限などを適切に設定してください。質問や追加の使い方サンプルが必要であれば教えてください。