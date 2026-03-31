# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants からのデータ取得、DuckDB ベースの ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを含むモジュール群を提供します。

## 主要機能
- データ取得 / ETL
  - J-Quants API からの株価日足、財務データ、JPXマーケットカレンダーの差分取得（ページネーション・レート制御・リトライ付き）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（quality モジュール）
- ニュース収集 / NLP
  - RSS からのニュース収集（SSRF / XML 攻撃対策、トラッキングパラメータ除去）
  - OpenAI を使った銘柄別センチメントスコアリング（news_nlp.score_news）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定（regime_detector.score_regime）
- リサーチ支援
  - モメンタム / ボラティリティ / バリューなどのファクター計算（research モジュール）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査スキーマの初期化と専用 DB 初期化ユーティリティ
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）と Settings クラスによる環境変数アクセス

## 必要環境
- Python 3.10 以上（Union 型記法や型注釈の使用に依存）
- 必要なパッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- そのほか標準ライブラリ（urllib, logging, datetime 等）

requirements.txt を用意する場合の例:
```
duckdb
openai
defusedxml
```

## セットアップ手順（推奨）
1. Python 仮想環境を作る
```
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

2. 必要パッケージをインストール
```
pip install -r requirements.txt
```
あるいは個別インストール:
```
pip install duckdb openai defusedxml
```

3. 環境変数を準備
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を配置すると、起動時に自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化可能）。

推奨される最低限の環境変数（例 .env）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API（もし使用する場合）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack（通知等を使う場合）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境（development / paper_trading / live）
KABUSYS_ENV=development

# ログレベル（DEBUG/INFO/...）
LOG_LEVEL=INFO
```

4. （任意）監査ログ用 DB の初期化
Python REPL またはスクリプトから:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

## 使い方（主要な例）

- DuckDB 接続を取得して日次 ETL を実行する例:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("scored:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（研究用途）:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- 市場カレンダー / 営業日ユーティリティ:
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

## 環境変数一覧（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 if using kabu API) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で参照）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（data/monitoring.db）
- KABUSYS_ENV — 実行環境 ("development", "paper_trading", "live")
- LOG_LEVEL — ログレベル（"DEBUG", "INFO", ...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合は 1 をセット

設定が必須（未設定だと ValueError を投げる）となるプロパティ:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.slack_bot_token
- settings.slack_channel_id

## ディレクトリ構成（抜粋）
プロジェクトは src/kabusys 配下のパッケージで構成されています。代表的なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP スコアリング（score_news）
    - regime_detector.py      — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント / 保存ユーティリティ
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL の公開インターフェース（ETLResult）
    - news_collector.py       — RSS -> raw_news 収集
    - calendar_management.py  — 市場カレンダー管理（is_trading_day 等）
    - quality.py              — データ品質チェック
    - stats.py                — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査ログスキーマ初期化（init_audit_db / init_audit_schema）
  - research/
    - __init__.py
    - factor_research.py      — momentum/value/volatility 等
    - feature_exploration.py  — 将来リターン / IC / 統計サマリ
  - ai, research, data の各モジュールに多数のヘルパー・実装があります（README は概略です）。

## 開発・テストに関する注意
- 自動環境変数ロードはプロジェクトルートの .env / .env.local を自動的に読み込みます。テストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分は外部 API を叩くため単体テストではモック化することを推奨します。コード内でもモック対象にしやすいように _call_openai_api 等のラッパー関数が用意されています。
- DuckDB への大量書き込みは executemany を使用しています。DuckDB のバージョン差異に注意してください（コメントに互換性注意あり）。

## ライセンス / 貢献
（ライセンスや貢献方法がある場合はここに記載してください）

---

不明点や追加したい例、README のフォーマット（英語版や簡潔版など）があれば教えてください。