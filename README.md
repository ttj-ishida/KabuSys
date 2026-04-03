# KabuSys

KabuSys は日本株のデータ収集・品質管理・ファクター研究・AI を用いたニュースセンチメント解析・市場レジーム判定・監査ログなどを備えた自動売買／リサーチ基盤のライブラリ群です。本リポジトリは主に以下を提供します：

- J-Quants API を用いた差分ETL（株価・財務・市場カレンダー）
- DuckDB を用いたローカルデータストアと冪等保存
- ニュース収集（RSS）とニュースの前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースNLP（銘柄別センチメント）と市場レジーム判定
- ファクター計算（Momentum / Value / Volatility 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- JPX カレンダー管理（営業日判定、更新ジョブ）
- kabuステーション等への実際の発注ロジックは本コードベースの一部として設計されている想定

以下に利用方法・セットアップ手順・モジュール説明・ディレクトリ構成を示します。

---

## 機能一覧（主要コンポーネント）

- data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークンリフレッシュ・DuckDB への保存関数）
  - pipeline: 日次 ETL（run_daily_etl）/ 個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - news_collector: RSS 収集と前処理（SSRF 対策、トラッキングパラメータ除去、記事IDのハッシュ生成）
  - calendar_management: JPX カレンダー管理・営業日ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - audit: 監査ログテーブル初期化/監査用 DB 初期化（init_audit_schema, init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して市場レジームを書き込む
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス: 環境変数の読み込み（.env 自動ロード・必須チェック・デフォルト値管理）

---

## 必要条件（主な依存関係）

- Python 3.10+
- duckdb
- openai
- defusedxml
- その他標準ライブラリ（urllib, json, logging など）

（実行環境・追加機能に応じてさらに依存が必要になる場合があります。パッケージ管理ファイル（requirements.txt 等）があればそれを利用してください。）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install --upgrade pip
# 依存パッケージをインストール（requirements.txt があれば利用）
pip install duckdb openai defusedxml
```

2. 環境変数を設定する（.env ファイル作成）

プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（読み込みは config.py により .git または pyproject.toml を基準に探索）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例: `.env`（最低限必要な設定）

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password   # 必要に応じて
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

- 必須:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（config.Settings.jquants_refresh_token で必須）
  - OPENAI_API_KEY: AI 機能を使う場合に必要（news_nlp/regime_detector で使用）
- オプション・デフォルトあり:
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH, CPU/MEMORY/DISK 閾値 等

3. データディレクトリ作成（必要なら）

```
mkdir -p data
```

4. 監査用 DuckDB を初期化（任意）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って必要に応じた操作を行えます
```

---

## 使い方（例）

以下は代表的な Python API の例です。プロジェクト内で実行するスクリプトや cron / ジョブランナーから呼び出して使います。

1. 日次 ETL を実行する（J-Quants からデータ取得 → DuckDB に保存 → 品質チェック）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースセンチメントをスコア化して ai_scores に保存する

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で環境変数参照
print(f"written: {written}")
```

3. 市場レジームを判定して market_regime テーブルへ保存する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4. ファクター計算（例：モメンタム）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
# records は各銘柄ごとの辞書リスト
```

5. カレンダーの夜間更新ジョブを実行（JPX カレンダー取得）

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

6. RSS フィードを取得（news_collector.fetch_rss を利用）

```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## よく使う設定（環境変数の一覧・説明）

- JQUANTS_REFRESH_TOKEN - 必須。J-Quants のリフレッシュトークン。
- OPENAI_API_KEY - OpenAI API キー（news_nlp / regime_detector が利用）。
- KABU_API_PASSWORD - kabuステーション API のパスワード（発注等で使用）。
- KABU_API_BASE_URL - kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）。
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID - LINE 通知を使う場合のトークン / 宛先ID。
- DUCKDB_PATH - デフォルト DB パス（data/kabusys.duckdb）。
- SQLITE_PATH - 監視用 SQLite DB（data/monitoring.db）。
- PID_FILE_PATH / KILL_FLAG_PATH - 実行監視に使うファイルパス。
- KILL_FLAG_CLEAR_ON_START - 起動時に kill フラグをクリアするか（"1" / "0"）。
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT - 監視閾値（%）。
- KABUSYS_ENV - 環境 ("development" / "paper_trading" / "live")（デフォルト development）
- LOG_LEVEL - ログレベル（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"）

設定は .env (または .env.local) に書くか環境変数で与えてください。config.Settings は自動で .env をロードします（ただしプロジェクトルートが特定できない場合はスキップされます）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を想定）

- kabusys/
  - __init__.py               -- パッケージ初期化（バージョン・公開 API 等）
  - config.py                 -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             -- ニュースセンチメントスコア（OpenAI 連携）
    - regime_detector.py      -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py       -- J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
    - quality.py              -- データ品質チェック
    - news_collector.py       -- RSS 収集と前処理
    - calendar_management.py  -- 市場カレンダー管理
    - audit.py                -- 監査ログ（テーブルDDL／初期化）
    - etl.py                  -- ETLResult 再エクスポート
    - stats.py                -- zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py      -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py  -- forward returns, IC, factor summary, rank

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ることを前提に設計されており、バックテスト環境でもルックアヘッドバイアスを避けるように日付の扱いに注意が払われています。

---

## 開発・テストに関する注意

- AI モジュール（news_nlp, regime_detector）は OpenAI API を呼び出します。テスト時は _call_openai_api 等をモックすると良いです（モジュール内で差し替え可能に設計されています）。
- jquants_client の HTTP 呼び出しはネットワーク依存・レート制御等があるため、ユニットテストでは外部 API をモックしてください。
- DuckDB の executemany に空リストを渡さない等、実運用での DuckDB の仕様差異を考慮した実装があります。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト環境で自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ライセンス・貢献

（プロジェクトに合わせてライセンス情報・貢献方法を追記してください）

---

以上が本コードベースの README.md です。必要であれば、README にサンプル .env.example、requirements.txt、簡単な CLI スクリプト例（cron / systemd 用の起動スクリプト）や初期スキーマ作成スクリプトの追記も作成します。どの情報を優先して追加しますか？