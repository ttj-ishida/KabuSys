# KabuSys

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買の基盤ライブラリです。J-Quants や RSS、OpenAI（LLM）など外部データ・サービスと連携し、ETL・データ品質チェック・ファクター生成・ニュース NLP・市場レジーム判定・監査ログ（トレーサビリティ）などを提供します。

主な設計方針は「バックテストにおけるルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（外部API失敗時に安全に継続）」です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 必要な環境変数
- セットアップ手順
- 使い方（簡単な例）
- ディレクトリ構成
- 補足・運用メモ

---

プロジェクト概要
- 日本株向けに設計されたデータ取得（J-Quants）、ニュース収集、品質チェック、ファクター計算、LLM を用いたニュースセンチメント、ETF の MA に基づく市場レジーム判定、監査ログ（シグナル→発注→約定のトレース）などを含むライブラリ群。
- DuckDB を内部データストアとして多用し、ETL は差分取得・バックフィルを考慮した実装。LLM 呼び出しは OpenAI SDK（gpt-4o-mini 想定）に対応。

機能一覧
- 環境設定読み込み・管理（.env 自動読み込み、環境変数優先）
- J-Quants API クライアント（株価日足、財務、マーケットカレンダー、上場銘柄情報）
  - レート制御・リトライ・トークン自動リフレッシュ・ページネーション対応
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS）と前処理（SSRF 防御、URL 正規化、トラッキング除去）
- ニュース NLP（LLM を用いた銘柄ごとのセンチメントスコア） — kabusys.ai.news_nlp.score_news
- 市場レジーム判定（ETF 1321 の MA200 とニュースのセンチメントを合成） — kabusys.ai.regime_detector.score_regime
- リサーチ用ユーティリティ（モメンタム、ボラティリティ、バリュー、将来リターン、IC、統計サマリー）
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ

必要な環境変数
（少なくとも以下はプロダクションで必須。テスト時はモック可能）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI API を使う機能（news_nlp / regime_detector）を実行する場合

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring 用)（デフォルト data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live）、デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとパッケージインポート時の .env 自動読み込みを無効化できます（テスト時に便利）。

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. Python 環境（推奨: 3.10+）
   - virtualenv / venv を使う
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

3. 依存パッケージのインストール（主要なもの）
   - 本リポジトリには requirements.txt がない想定なので代表的な依存を手動で入れる:
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 必要に応じて他のライブラリ（requests 等）を追加してください。

4. 環境変数を準備
   - プロジェクトルートに `.env` として以下のように用意します（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   - 自動ロードはパッケージ import 時に実行されます（.env.local があれば優先）。

5. データベースディレクトリの作成（必要なら）
   ```bash
   mkdir -p data
   ```

6. 監査ログ用 DuckDB 初期化（任意）
   ```python
   >>> from kabusys.data.audit import init_audit_db
   >>> conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
   >>> conn.execute("SELECT name FROM sqlite_master")  # DuckDB の場合は information_schema 等で確認
   ```

使い方（簡単な例）
- DuckDB 接続を作成して ETL を実行する（run_daily_etl の例）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（ai スコア）を実行する:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_scores = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_scores}")
  ```

- 市場レジーム判定（score_regime）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（例: モメンタム）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(recs), recs[:3])
  ```

- 監査ログスキーマを既存 DB に追加:
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

運用上の注意
- OpenAI 呼び出しや J-Quants API は外部課金対象です。API キーやトークンは適切に管理してください。
- ETL は差分・バックフィル機構を持ちますが、初回は大量データを取得するため時間がかかる可能性があります。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあります（コード側で対策済みの箇所あり）。
- LLM 呼び出し部分はリトライ・フォールバック（失敗時ゼロスコア）して動作を継続する設計です。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 自動ロード、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP (score_news)
    - regime_detector.py         — 市場レジーム判定 (score_regime)
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch / save）
    - pipeline.py                — ETL（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - news_collector.py          — RSS 収集・前処理
    - quality.py                 — データ品質チェック
    - stats.py                   — zscore_normalize 等汎用統計
    - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
    - audit.py                   — 監査ログスキーマ初期化（signal/order/execution）
  - research/
    - __init__.py
    - factor_research.py         — モメンタム / ボラ / バリュー計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - research/*（その他ユーティリティが re-export される）

補足
- テスト: 各モジュールは外部依存（ネットワーク、OpenAI）を切り離してユニットテストしやすい設計（内部関数のパッチや id_token 注入など）になっています。
- 拡張: kabu ステーションとの実際の約定フローや Slack 通知などは別モジュール・運用スクリプトで組み合わせて利用してください。

この README はコードベースの概要と使い方の抜粋です。詳細な API（関数引数・戻り値）やスキーマは各モジュール内のドキュメンテーション文字列（docstring）を参照してください。