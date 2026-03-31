# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、研究用ファクター計算、監査ログ／発注トレーサビリティなどの機能を提供します。

主な設計方針は「バックテストでのルックアヘッドバイアスを避ける」「DuckDB を中心にローカルに保存する」「外部 API 呼び出しはリトライやレート制御を行う」「各処理は冪等・フォールバックを重視する」となっています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数（設定）
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API を用いた株価・財務・カレンダーの ETL
- RSS ベースのニュース収集と記事前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄別 / マクロ）
- 研究（research）用のファクター計算・特徴量探索ユーティリティ
- DuckDB を用いたデータ保存、監査ログ（order/signals/executions）用スキーマと初期化
- データ品質チェック（欠損・スパイク・重複・日付整合性）

---

機能一覧（主要）
- data/
  - ETL パイプライン (run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl)
  - J-Quants クライアント（fetch/save 帯）
  - calendar_management（営業日判定・next/prev/get_trading_days）
  - news_collector（RSS 取得・前処理・保存）
  - quality（データ品質チェック）
  - audit（監査ログテーブルの初期化/監査 DB 初期化関数）
  - stats（zscore_normalize 等）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメントを ai_scores に書き込む）
  - regime_detector.score_regime（ETF 1321 の MA200 とマクロニュースを合成して market_regime に書き込む）
- research/
  - factor_research (calc_momentum / calc_value / calc_volatility)
  - feature_exploration (calc_forward_returns / calc_ic / factor_summary / rank)
- config.py
  - .env 自動読み込み（プロジェクトルートの .env / .env.local をロード）
  - Settings オブジェクト経由で設定を取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）

設計上の注記：
- 多くの関数は datetime.today() / date.today() を内部で盲目的に参照せず、呼び出し元から target_date を渡すことでルックアヘッドを防止します。
- OpenAI や J-Quants 呼び出しはリトライ・バックオフ・レート制限・エラーハンドリングを実装しています。

---

セットアップ手順（開発用）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - このコードベースは以下の主要依存が想定されています（requirements.txt を用意している場合はそちらを使用してください）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - 開発インストール（パッケージ化されている場合）
     - pip install -e .
4. 環境変数 / .env の準備
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に .env を作成してください。
   - 自動ロードはデフォルトで有効です。テスト時に無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
5. DuckDB / データディレクトリ作成
   - デフォルトの DuckDB パスは data/kabusys.duckdb（Settings.duckdb_path）
   - 監査用 SQLite は data/monitoring.db（Settings.sqlite_path）
   - 必要に応じてディレクトリを作成してください（init_audit_db が自動で親ディレクトリを作成する場合あり）。

---

主要な環境変数（Settings）
- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants API 用のリフレッシュトークン。jquants_client.get_id_token で使用されます。
- OPENAI_API_KEY (必須 for AI 呼び出し)
  - OpenAI API を利用する場合に使用。score_news / score_regime に渡すことも可能。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（注文関連を組み込む際に必要）。
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID (必須 if Slack integration used)
- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視/監査用 SQLite のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意)
  - 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意)
  - ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

.env の簡易例:
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C00000000
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=DEBUG

注意: .env は安全に管理してください。リポジトリにコミットしないでください。

---

使い方（簡単なコード例）
- DuckDB 接続を作って ETL を回す例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコアして DB に書き込む（OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、api_key 引数に渡す）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores テーブルへ書き込み
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB（監査専用 DuckDB）を初期化する:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルにレコードを挿入 / クエリ実行
```

注意点:
- OpenAI 呼び出しは API 利用料が発生します。テスト時は関数内の _call_openai_api をモックすることを推奨します（README 内の関数はテスト用に差し替え可能）。
- J-Quants API の呼び出しはレート制限・リトライを実装していますが、大量連続実行は API 利用制限に注意してください。

---

主要な公開 API（抜粋）
- kabusys.config.settings: 設定オブジェクト
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
- kabusys.data.jquants_client: fetch_* / save_* / get_id_token
- kabusys.data.news_collector.fetch_rss(...)
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py  (ETLResult re-export)
    - pipeline.py (run_daily_etl, run_prices_etl, ...)
    - stats.py (zscore_normalize)
    - quality.py (データ品質チェック)
    - audit.py (監査テーブル DDL / init)
    - jquants_client.py (API client: fetch/save)
    - news_collector.py (RSS 取得 / 前処理)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py (calc_forward_returns / calc_ic / factor_summary / rank)

上記以外に strategy / execution / monitoring 等のパッケージが __all__ にリストされていますが、今回提示されたコードでは主に data / ai / research 周りが実装されています。

---

テスト & 開発上のヒント
- AI 呼び出しや外部 API はユニットテストでモックする設計になっています（モジュール内の _call_openai_api や network 関数を patch する）。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境で有用）。
- DuckDB の executemany は空リストバインドに制約があるため、コード内では空リストを渡さないガードを行っています。独自スクリプトで利用する際は注意してください。

---

ライセンス / 貢献
- （この README を配布先のプロジェクトに合わせて適宜補記してください）

---

README はここまでです。必要に応じて「API 詳細」「テーブルスキーマ」「運用手順（cron / Airflow 等）」などの追加ドキュメントを作成できます。どの項目を詳細化したいか教えてください。