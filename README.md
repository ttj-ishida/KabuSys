# KabuSys

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買基盤のための Python ライブラリです。J-Quants API や RSS/ニュース、OpenAI（LLM）を利用したニュースセンチメント、ファクター計算、ETL、監査ログなどの機能を備え、DuckDB を中心にデータを永続化・解析します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を直接参照しない設計）
- DuckDB を用いたローカルデータプラットフォーム
- J-Quants API / OpenAI API への堅牢な呼び出し（リトライ・レート制御）
- ETL と品質チェック、監査ログによるトレーサビリティ

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- ディレクトリ構成 / 主要ファイル説明
- 環境変数一覧（必須・任意）
- 開発メモ / 注意点

---

## プロジェクト概要

このライブラリは以下の領域をカバーします：

- データ収集（J-Quants API から株価・財務・市場カレンダーを差分取得）
- ニュース収集（RSS）とニュースの前処理、記事と銘柄の紐付け
- ニュースセンチメント（OpenAI を用いた銘柄ごとのスコアリング / マクロセンチメント）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Zスコア正規化など）
- ETL パイプライン（差分取得・保存・品質チェック）
- 監査ログ（戦略→シグナル→発注→約定をトレースする監査テーブル）
- モジュール化された設定管理（.env / 環境変数）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須変数の検証（Settings クラス）

- データ取得 / 保存
  - J-Quants クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 実行結果を ETLResult で返却
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース
  - RSS 収集（fetch_rss）
  - 前処理（URL 除去、空白正規化、URL 正規化／トラッキング除去）
  - ニュース→銘柄紐付けのための仕組み（news_symbols テーブル想定）

- AI（OpenAI）
  - news_nlp.score_news: 銘柄単位のニュースセンチメント算出・ai_scores 書き込み
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュースを合成して市場レジーム判定

- 研究（Research）
  - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize

- 監査（Audit）
  - init_audit_schema / init_audit_db: signal_events / order_requests / executions などの監査テーブル作成

---

## セットアップ手順

必要条件
- Python 3.10+（typing における | 記法、型ヒントのため）
- 推奨パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml

例（venv を使用）:

1. リポジトリをクローンして仮想環境を準備
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール（プロジェクトに requirements.txt がある想定）
   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # もしくは:
   # pip install -e .
   ```

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるパス）に .env を置くと、自動で読み込まれます（.env.local があれば優先して上書き）。
   - または OS 環境変数で設定してください。

   代表的な必須項目（詳しくは下の「環境変数一覧」参照）:
   - OPENAI_API_KEY（LLM 呼び出し）
   - JQUANTS_REFRESH_TOKEN（J-Quants API）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知が利用される場合）
   - KABU_API_PASSWORD（kabuステーション API を使う場合）

4. DuckDB 初期化（任意）
   - 監査用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL や解析で使用する DB は settings.duckdb_path を参照（デフォルト data/kabusys.duckdb）。

5. テスト実行（簡易）
   - Python REPL から ETL の軽い実行・関数呼び出しを試す（下記 使用例 を参照）。

---

## 使い方（主要 API の例）

以下は簡単な Python 例です。事前に必要な環境変数が設定され、DuckDB への接続パスが準備されていることを想定します。

- ETL の日次実行（run_daily_etl）:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア算出（OpenAI が必要）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# API キーは環境変数 OPENAI_API_KEY で自動取得されます
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/monitoring_audit.duckdb")
# これで signal_events, order_requests, executions 等が作成されます
```

- J-Quants から株価を直接取得（プログラム的に）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes
records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
print(len(records))
```

- RSS を取得してローカル処理:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a['id'], a['title'])
```

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なモジュールと説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境設定の読み込み (.env 自動ロード、Settings クラス)
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースセンチメントの LLM スコア算出（score_news）
    - regime_detector.py
      - マクロ + ETF MA を合成した市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、取得/保存関数
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - etl.py
      - ETLResult の再エクスポート
    - calendar_management.py
      - 市場カレンダー管理（is_trading_day, next_trading_day など）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
    - audit.py
      - 監査テーブル DDL と初期化ユーティリティ
    - news_collector.py
      - RSS 収集・前処理（fetch_rss 等）
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - research/...（その他リサーチ用ユーティリティ）

---

## 環境変数一覧（代表的なもの）

自動ロード対象はプロジェクトルートの .env / .env.local（.env.local が優先）です。必須の環境変数が未設定の場合、Settings のプロパティ呼び出しで ValueError が送出されます。

必須（少なくとも開発・実行で必要となるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector）
- SLACK_BOT_TOKEN: Slack 通知に利用する場合
- SLACK_CHANNEL_ID: Slack 通知対象チャンネル

その他（デフォルト値あり）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必要な場合）
- KABU_API_BASE_URL: kabu API の base URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PID_FILE_PATH: 実行プロセス PID ファイルパス（default: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live（default: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

.env の自動ロードに関する注意:
- プロジェクトルートはこのモジュールの __file__ を起点に .git または pyproject.toml を探索して決定します。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化できます（テスト等で便利）。

---

## 開発メモ / 注意点

- Python バージョンは 3.10 以上を想定（型表記や union | を使用）。
- OpenAI API 呼び出しは gpt-4o-mini を想定し、JSON Mode レスポンスをパースします。API の応答や JSON フォーマットの変化に対するフォールバック処理が入っていますが、正しい API キーとモデルアクセス権が必要です。
- J-Quants API の呼び出しはレート制限を考慮（120 req/min の固定間隔スロットリング）し、401 発生時はリフレッシュトークンで再取得を試みます。
- DuckDB への executemany の挙動（空リスト不可など）に注意し、空パラメータは事前に排除する実装になっています。
- ニュース収集モジュールでは SSRF 対策（ホストがプライベートかどうかのチェック、リダイレクト検査）やコンテンツサイズ制限を実装しています。
- 監査ログは削除しない前提で設計しています（ON DELETE RESTRICT、created_at は UTC）。

---

もし README をプロジェクトのルートに追加する形で Markdown に整形したファイルが欲しい場合や、具体的な .env.example の内容、requirements.txt / pyproject.toml のテンプレート、あるいは実行スクリプト（systemd, cron, Dockerfile など）の雛形が必要であればお知らせください。用途（開発 / 本番 / バックテスト）に合わせて推奨構成を提案します。