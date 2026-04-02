# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント分析）、研究用ファクター計算、マーケットカレンダー管理、監査ログ（オーダー・約定トレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は次の目的を持ったモジュール群です。

- J-Quants API を使った株価／財務／カレンダーの差分取得と DuckDB への冪等保存（ETL）
- RSS からのニュース収集と銘柄紐付け（news_collector）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント（ai/news_nlp）および市場レジーム判定（ai/regime_detector）
- 研究用ファクター計算（research/*.py）と汎用統計ユーティリティ（data/stats.py）
- データ品質チェック（data/quality.py）
- 監査ログ用スキーマの初期化・管理（data/audit.py）
- 市場カレンダー管理（data/calendar_management.py）

設計上の特徴：
- ルックアヘッドバイアス対策（関数内で date.today() を直接参照しない設計が多い）
- DuckDB を主な永続層として使用、冪等保存（ON CONFLICT / DO UPDATE）
- 外部 API 呼び出しはリトライやレート制御、フェイルセーフ処理を備える

---

## 主な機能一覧

- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・保存・品質チェック）
- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token（refresh token から id token 取得）
- ニュース収集
  - fetch_rss（RSS 取得・正規化・SSRF 対策等）
- ニュース NLP / AI
  - score_news（銘柄毎のニュースセンチメントを ai_scores に保存）
  - score_regime（ETF 1321 の MA とマクロニュースを統合して市場レジーム判定）
- 研究用機能
  - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索）
  - zscore_normalize（標準化ユーティリティ）
- 市場カレンダー
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（J-Quants からの差分更新）
- データ品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 監査ログ（オーダー/約定）
  - init_audit_schema, init_audit_db（監査用テーブル・インデックス作成）

---

## 必要環境 / 依存

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

推奨: 仮想環境 (venv / pyenv) を利用してください。

例: requirements.txt（プロジェクトに合わせて調整してください）
- duckdb
- openai
- defusedxml

---

## 環境変数

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須（Settings で _require されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（本システムの一部で使用）
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意／デフォルト値あり:
- KABU_API_BASE_URL — kabu API の base URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（default: data/monitoring.db）
- PID_FILE_PATH — 実行プロセス監視の PID ファイル（default: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — システム監視用閾値（%）
- KABUSYS_ENV — 環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — =1 で自動 .env ロード無効化

.env.example を参照して .env を作成してください。

---

## セットアップ手順

1. リポジトリをクローン
   - プロジェクトルートに .git または pyproject.toml があると自動 .env ロードが有効になります。

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存ライブラリインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上記の主要依存を個別にインストール）

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定します。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...

5. DuckDB 用ディレクトリ作成（必要なら）
   - mkdir -p data

---

## 使い方（主要な例）

以下は Python から直接呼び出す簡単な例です。DuckDB 接続は duckdb.connect() を使います。

共通インポート例:
```python
import duckdb
from kabusys.config import settings
```

1) ETL（日次パイプライン）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成（AI）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら OPENAI_API_KEY を使う
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続を返す
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url, source="yahoo_finance")
for a in articles:
    print(a["datetime"], a["title"])
```

6) 研究用ファクター計算（例：モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとの dict のリスト
```

---

## よくある運用注意点

- OpenAI 呼び出しは外部APIのため、APIキーの管理、レート・コスト管理に注意してください。AI 関連関数はリトライや失敗時のフォールバック（0.0）を持っていますが、APIキーが未設定だと明示的エラーになります。
- J-Quants API 呼び出しはレートリミット（120 req/min）に合わせた内部レート制御を行います。ID トークンは自動リフレッシュされます。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、関数内で空チェックを行っています。
- ETL と品質チェックは独立して例外処理され、ある処理の失敗が全体を止めないようになっています。結果は ETLResult に収集されます。

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（OpenAI）
    - regime_detector.py            -- 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント + DuckDB 保存
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult 再エクスポート
    - news_collector.py             -- RSS 収集（SSRF 対策等）
    - calendar_management.py        -- マーケットカレンダー管理
    - stats.py                      -- 汎用統計ユーティリティ（zscore 等）
    - quality.py                    -- データ品質チェック
    - audit.py                      -- 監査ログスキーマ初期化・DB 初期化
  - research/
    - __init__.py
    - factor_research.py            -- Momentum/Value/Volatility 計算
    - feature_exploration.py        -- 将来リターン / IC / summary
  - monitoring/ (存在を README に明示。詳細実装は別モジュールに含まれる可能性あり)
  - strategy/, execution/  (戦略・発注周りは本コードベース設計に依存)

この README はコードの主要な利用ポイントと設計方針をまとめたものです。実運用や追加の外部設定（Slack 通知、kabuステーション 連携、監視デーモン等）は個別実装が必要です。

---

もし README に追記してほしい点（例: setup の OS 固有手順、CI の設定例、より多くの使用例、API レスポンスのスキーマ等）があれば教えてください。必要に応じてサンプル .env.example や requirements.txt のテンプレートも作成します。