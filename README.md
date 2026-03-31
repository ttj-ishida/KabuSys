# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリ。  
J-Quants / kabuステーション / OpenAI 等を組み合わせ、データ収集（ETL）・品質チェック・ニュースNLP・市場レジーム判定・研究用ファクター計算・監査ログ管理を行うためのユーティリティ群を提供します。

主に DuckDB をデータバックエンドとして想定し、バックフィル可能な日次 ETL、ニュースの LLM スコアリング、ファクター計算・探索、監査テーブル初期化などを備えています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（設定項目）
- ディレクトリ構成

---

プロジェクト概要
- 目的：日本株向けのデータ収集・前処理・品質検査・特徴量生成・LLM を使ったニュース解析・市場レジーム判定・監査ログ整備など、自動売買システムの基盤処理を提供する。
- データソース：J-Quants API（株価・財務・カレンダー）、RSS ニュース等
- 永続化：主に DuckDB（軽量 OLAP 対応ローカルDB）、監視用に SQLite などを想定
- LLM：OpenAI（gpt-4o-mini など）を利用したニュースセンチメント評価・マクロセンチメント評価

---

主な機能一覧
- 環境設定読み込み（.env 自動ロード、環境変数優先）
- J-Quants API クライアント：取得・保存（株価・財務・カレンダー）、ページネーション、トークン自動リフレッシュ、レート制御、リトライ
- ETL パイプライン（data.pipeline）
  - run_daily_etl: カレンダー、株価、財務の差分取得 + 品質チェック
  - 個別ジョブ：run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 結果のデータクラス ETLResult
- データ品質チェック（data.quality）：
  - 欠損、重複、スパイク、日付整合性チェック
- カレンダー管理（data.calendar_management）
  - 営業日判定、次/前営業日取得、期間内営業日取得、夜間のカレンダー更新ジョブ
- ニュース収集（data.news_collector）
  - RSS 収集、URL 正規化・SSRF 対策、前処理、記事 ID 生成
- ニュース NLP（ai.news_nlp）
  - calc_news_window、score_news: 銘柄毎にニュースをまとめて LLM でセンチメント付与し ai_scores テーブルへ保存
- 市場レジーム判定（ai.regime_detector）
  - ETF（1321）200日 MA 乖離とマクロニュース LLM スコアを合成して daily market_regime に判定を書き込み
- 研究用モジュール（research）
  - モメンタム / ボラティリティ / バリュー 等のファクター計算、将来リターン、IC・統計集計、Zスコア正規化
- 監査ログ（data.audit）
  - signal_events / order_requests / executions の DDL と初期化ユーティリティ（冪等）
- ユーティリティ（data.stats など）：外部ライブラリに頼らない統計処理

---

セットアップ手順（例）
1. 必要環境
   - Python 3.10+
   - 推奨パッケージ（例）
     - duckdb
     - openai
     - defusedxml
   （本リポジトリの requirements.txt があれば pip install -r で導入）

2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai defusedxml
   # 開発時はパッケージを editable install
   pip install -e .
   ```

3. 環境変数 / .env
   - プロジェクトルートの .env または .env.local（.env.local は .env を上書き）を用意します。
   - 自動読み込みはデフォルトで有効。無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主な環境変数（詳細は下記「環境変数」参照）
     - JQUANTS_REFRESH_TOKEN（必須）
     - OPENAI_API_KEY（score_news / score_regime に未指定時に参照）
     - KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など

4. データベース準備
   - DuckDB ファイルのディレクトリを作成する（settings.duckdb_path の parent）
   - 監査DBを別途作る場合（data/audit のユーティリティを使用）
     - 例: from kabusys.data.audit import init_audit_db; conn = init_audit_db("data/audit.duckdb")

---

使い方（主要 API の例）

- 共通準備
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings

  # settings.duckdb_path は Path オブジェクト（デフォルト "data/kabusys.duckdb"）
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（カレンダー→株価→財務→品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 個別 ETL（例: 株価のみ）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date

  fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
  ```

- ニューススコアリング（LLM 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数に設定されていれば api_key 引数は不要
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  ```

- 市場レジーム判定（LLM 必須）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

  - 両関数とも api_key を引数で明示的に渡すことも可能（テストや複数キー運用向け）。

- 監査テーブル初期化（監査用 DuckDB を作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存の conn にテーブルを追加
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- カレンダーユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  from datetime import date

  d = date(2026, 3, 20)
  is_trade = is_trading_day(conn, d)
  nxt = next_trading_day(conn, d)
  days = get_trading_days(conn, date(2026,3,1), date(2026,3,31))
  ```

- 研究用 API（ファクター計算）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  ```

- RSS フェッチ（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss

  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  # 返り値は NewsArticle 型のリスト（id, datetime, source, title, content, url）
  # raw_news テーブルへの保存ロジックはアプリ側で実装する（保存は ON CONFLICT で冪等化が推奨）
  ```

注意点
- OpenAI 呼び出し時の例外はモジュール側で一定のフェイルセーフ（0.0 スコアやスキップ）を設けていますが、APIキーが未設定の場合は ValueError を送出します。
- DuckDB の executemany はバージョン依存の挙動に注意している箇所があります（コード内参照）。
- 時刻は基本的に UTC / UTC naive を内部処理で使う旨の方針が多くのモジュールで採用されています（Look-ahead バイアス対策）。

---

環境変数（主な項目）
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- OPENAI_API_KEY
  - OpenAI API キー。news_nlp.score_news や regime_detector.score_regime のデフォルト参照先。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード
- KABU_API_BASE_URL (任意)
  - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot Token
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視 / モニタリング用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意)
  - 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意)
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 1 を設定するとプロジェクトルートの .env 自動読み込みを無効化

.env の自動読み込みルール
- 読み込み優先順位（上書き順）:
  - OS 環境変数（最優先、上書き不可）
  - .env.local（override=True、OS 環境変数を除いて上書き）
  - .env（override=False、未設定のみセット）
- 自動ロードはプロジェクトルート（.git または pyproject.toml の親ディレクトリを探索）から行います。プロジェクトルートが見つからない場合は自動ロードをスキップします。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境設定 / .env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch_*, save_*）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult 再エクスポート
    - news_collector.py   — RSS 収集ユーティリティ
    - calendar_management.py — 市場カレンダー管理
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計（zscore_normalize）
    - audit.py            — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py  — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — forward returns / IC / rank / summary

（上記は主要モジュールのみを抜粋した構成です）

---

開発ノート / 設計方針（抜粋）
- Look-ahead バイアス防止: 日時参照や DB クエリは将来データ参照を避けるよう設計
- 冪等性の確保: ETL の保存処理は基本的に ON CONFLICT を用いた上書き（idempotent）
- フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時は全停止させず、部分失敗はログ・警告・スキップで処理を継続
- セキュリティ: RSS 取得で SSRF 対策、defusedxml を利用した XML パース等を採用

---

貢献 / ライセンス
- 本 README ではライセンス・コントリビューション規約は未記載です。実運用や公開時は LICENSE を追加してください。

---

この README はコードベース（src/kabusys 以下）の主要機能と使い方をまとめたものです。細かな API 引数・例外挙動は各モジュール（data.pipeline, ai.news_nlp, ai.regime_detector, data.jquants_client など）の docstring を参照してください。必要であれば、サンプルスクリプトや運用手順（cron / Airflow / GitHub Actions による定期実行など）のテンプレートも作成します。要望があれば教えてください。