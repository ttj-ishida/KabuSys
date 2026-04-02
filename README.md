# KabuSys

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買基盤のためのライブラリ群です。J-Quants からのデータ ETL、ニュース収集、OpenAI を用いたニュース NLP、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）などを含みます。

---

## プロジェクト概要

本プロジェクトは以下の目的を持ちます。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分取得と DuckDB への永続化（ETL）。
- RSS を使ったニュース収集と raw_news テーブルへの蓄積。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントの算出（銘柄別 ai_score）およびマクロセンチメントを組み合わせた市場レジーム判定（bull/neutral/bear）。
- ファクター計算、特徴量探索、IC 計算等のリサーチ用ユーティリティ。
- 発注・約定を追跡するための監査ログスキーマ（audit）と初期化ユーティリティ。
- データ品質チェック（欠損・スパイク・重複・日付不整合）モジュール。

設計上の重要点：
- ルックアヘッドバイアスを避ける実装（内部で date.today() を不用意に参照しない等）。
- API 呼び出しはリトライ・バックオフとレート制御を実装。
- DuckDB への保存は冪等（ON CONFLICT）を意識した実装。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, calendar_update_job）
  - ニュース収集（fetch_rss, preprocess_text 等）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュースセンチメントスコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み / Settings（.env 自動読み込み、必須設定のバリデーション）

---

## 必要条件（目安）

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他: logging, requests 等は標準ライブラリで代用可能な箇所あり）

実際の requirements.txt がある場合はそれを使ってください。

インストール例（仮）:
```
python -m pip install duckdb openai defusedxml
```

---

## 環境変数 / .env

config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注等を行う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack のチャネル ID
- OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合）

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を自動読み込みします。
- テスト等で自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（例）

1. Python 環境を作成（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

3. プロジェクトルートに `.env` を作成し必要な環境変数を設定。

4. DuckDB ファイルや出力ディレクトリが必要な場合は作成:
   ```
   mkdir -p data
   ```

---

## 使い方（主要な利用例）

以下はモジュールを直接インポートして使う例です。各関数は基本的に DuckDB 接続（duckdb.connect(...) の戻り値）と日付オブジェクトを受け取ります。

- DuckDB 接続例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- ETL（1日分の差分 ETL）実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 単体 ETL（株価 / 財務 / カレンダー）:
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
run_calendar_etl(conn, target_date=date.today())
run_prices_etl(conn, target_date=date.today())
run_financials_etl(conn, target_date=date.today())
```

- 監査ログ DB 初期化（監査テーブルを DuckDB に作成）:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests / signal_events / executions テーブルが生成される
```

- ニュースセンチメント（銘柄別 ai_scores）算出:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を env に設定済みであること
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {written} codes")
```

- マーケットレジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を env に設定済みであること
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算 / 研究用ユーティリティ:
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- RSS フィード取得（ニュース収集の一部）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

---

## 注意事項 / 運用上のポイント

- OpenAI を利用する処理（score_news, score_regime）は API キー（OPENAI_API_KEY）が必要です。API 呼び出しはリトライ・タイムアウト・JSON パースを堅牢に扱っていますが、API 不通時のフォールバック挙動（macro_sentiment=0 等）に留意してください。
- J-Quants API はレート制限があります（モジュール内で管理されています）。JQUANTS_REFRESH_TOKEN は必須です。
- データ保存は基本的に冪等（ON CONFLICT）を想定していますが、外部からの直接操作やスキーマ変更時に注意が必要です。
- production / live 運用では KABUSYS_ENV を `live` に設定し、ログレベルや閾値の設定を見直してください。
- 自動で .env を読み込む仕組みがあります。必要に応じて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- news_collector では SSRF・XML Bomb・巨大レスポンスを防ぐ対策が入っていますが、外部 URL の扱いは慎重に行ってください。

---

## ディレクトリ構成（抜粋）

以下はソースの主要ファイル／モジュール構成（src/kabusys 以下）です。

- kabusys/
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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult の定義など)
    - audit.py (監査スキーマ定義)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## テスト / 開発

- モジュールは外部 API 呼び出し部分を明確に分離しており、テスト時にモック可能です（例: OpenAI 呼び出し関数や HTTP レイヤの差し替え）。
- config モジュールは自動で .env を読み込みます。ユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境の影響を排除してください。

---

## ライセンス / 貢献

この README はソースコードの説明に基づいた概要です。実運用や公開時には README にライセンス条項・貢献ガイドライン・詳細なインストール手順（requirements.txt / Dockerfile / systemd ユニット等）を追記してください。

---

質問や追加してほしい利用例（例: Docker 化手順、systemd サービス定義、Slack 通知例、監査ログのクエリ例など）があれば教えてください。README を拡張して具体的なスニペットや運用手順を追加します。