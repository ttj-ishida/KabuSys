# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants API からのデータ取得）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（発注 → 約定のトレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群から構成されています。

- データ取得・ETL（J-Quants API 経由で株価・財務・マーケットカレンダー取得）
- ニュース収集・NLP（RSS 収集・OpenAI を使った銘柄別センチメント）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計）
- データ品質チェック
- 監査ログ（signal → order_request → execution の追跡）
- 環境設定管理（.env 自動読み込み等）

設計方針として「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API 不調時はスキップして継続）」等が採用されています。

---

## 主な機能一覧

- ETL:
  - run_daily_etl: 市場カレンダー・日足・財務データの差分取得・保存・品質チェックの実行
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL ジョブ
  - jquants_client: API 呼び出し（認証トークン自動リフレッシュ、レートリミット、リトライ、DuckDB へ冪等保存）

- ニュース / NLP:
  - news_collector: RSS 収集、前処理、raw_news への冪等保存
  - score_news: OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント生成・ai_scores への保存
  - 安全対策（SSRF 防止、受信サイズ制限、defusedxml）

- 市場レジーム:
  - regime_detector.score_regime: ETF 1321 の 200 日 MA 乖離と LLM マクロセンチメントを合成して market_regime へ保存

- 研究（research）:
  - calc_momentum / calc_volatility / calc_value：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize：特徴量解析・統計

- データ管理:
  - calendar_management: 営業日判定・next/prev trading day・カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - audit: 監査テーブル定義・初期化（init_audit_schema / init_audit_db）

- 設定:
  - config.Settings: 環境変数ベースの設定取得（.env の自動読み込みを実装）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（コード内で型ヒントに union 型 `X | Y` 等を使用）
- system に duckdb, openai, defusedxml 等のパッケージをインストールしてください。

例: pipenv/venv を使う場合
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発用に他パッケージがある場合はそれらも追加
```

環境変数 / .env:
- プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を基に自動で `.env` / `.env.local` を読み込みます。
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主要な環境変数（必須/推奨）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- OPENAI_API_KEY (LLM を利用する場合必須) — OpenAI API キー
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、通知に使用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE（paper trading 用の模擬約定挙動: instant|partial|never|reject）

推奨ディレクトリ作成:
```bash
mkdir -p data
```

---

## 使い方（簡易サンプル）

※ 各操作は Python スクリプトやスケジューラ（cron, systemd timer, Airflow 等）で呼び出して利用してください。

共通: settings の利用
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

DuckDB 接続作成:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

ETL（日次実行例）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())
```

ニューススコアリング（OpenAI API 必須）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str("/path/to/your.db"))
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {written} ai scores")
```

市場レジーム判定（OpenAI API 必須）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str("/path/to/your.db"))
score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログDB初期化
```python
from kabusys.data.audit import init_audit_db
# 監査用 DB ファイルを指定（:memory: も可）
audit_conn = init_audit_db("data/monitoring_audit.duckdb")
```

研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト
```

データ品質チェック
```python
from kabusys.data.quality import run_all_checks
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

テストやスクリプトから .env 自動ロードを抑止したい場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY（LLM 利用時必須）
- KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_FILL_MODE（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視関連）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV（development | paper_trading | live、デフォルト development）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）

config.Settings 経由でアクセスできます。必須項目が未設定の場合は ValueError が発生します。

---

## ディレクトリ構成

主要ファイル / モジュールの一覧（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / .env 読み込み・Settings
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP スコアリング（score_news）
    - regime_detector.py         — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（fetch / save）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult の再エクスポート
    - calendar_management.py     — 市場カレンダー管理（is_trading_day, get_trading_days 等）
    - news_collector.py          — RSS 収集・前処理・保存
    - quality.py                 — データ品質チェック
    - stats.py                   — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                   — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum, value, volatility）
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー / rank
  - ai, data, research のそれぞれが公開する関数群を持ち、上位モジュールから統合的に利用可能です。

---

## 注意事項 / 運用上のヒント

- LLM（OpenAI）を呼ぶ箇所は API 失敗時にフェイルセーフ（0.0 等）を返す設計ですが、API キーは必ず安全に管理してください。API 呼び出しは課金対象になります。
- jquants_client はレート制限（120 req/min）とリトライロジックを実装しています。大量のページネーション呼び出しを行う場合は実行時間やレートを考慮してください。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあり、実装内で空チェックがされています。アップデート時は互換性に注意してください。
- 監査テーブルは削除しない前提で設計されています（トレースの完全性を確保）。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動読み込みを無効にすることで環境差分を制御できます。
- ルックアヘッドバイアス防止のため、内部実装は target_date 指定や DB の date < target_date のような排他条件を積極的に使っています。バックテスト等でデータ取得のタイミングに注意してください。

---

もし README に追加したい「.env.example のテンプレート」や「運用用 systemd / cron のサンプル」などがあれば、要望に合わせて追記します。