# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、監査ログなどを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（内部で datetime.today()/date.today() を不用意に参照しない）
- DuckDB を中心としたローカルデータプラットフォーム
- J-Quants API / OpenAI 呼び出しにはリトライ・レート制御・フェイルセーフを実装
- 冪等性を重視した DB 書き込み（ON CONFLICT / DELETE→INSERT パターン等）

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価日足・財務データ・マーケットカレンダーを差分取得（fetch / save）
  - run_daily_etl による日次 ETL パイプライン（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損（OHLC）、スパイク（急落/急騰）、重複、日付整合性チェック
- ニュース収集・NLP
  - RSS 取得（SSRF 防止、サイズ制限、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメントスコアリング
- 市場レジーム判定
  - ETF (1321) の MA200 乖離 + マクロニュースの LLM センチメントを合成して日次レジーム判定
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
- ユーティリティ
  - 統計ユーティリティ（z-score 正規化 等）
  - マーケットカレンダー管理（営業日判定、next/prev/get_trading_days 等）

---

## 前提・依存関係

- Python 3.10+
  - 型注釈に `X | None` などを利用しているため 3.10 以上を推奨
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging などを利用

インストール例（仮のセット）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# あるいはパッケージが整備されていれば:
# pip install -e .
```

---

## 環境変数 / .env

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます（自動ロード）。  
自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須となる代表的な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）

任意／デフォルト値:
- KABU_API_BASE_URL: "http://localhost:18080/kabusapi"
- DUCKDB_PATH: "data/kabusys.duckdb"
- SQLITE_PATH: "data/monitoring.db"
- PID_FILE_PATH: "data/execution.pid"
- CPU_THRESHOLD_PCT: 90.0
- MEMORY_THRESHOLD_PCT: 85.0
- DISK_THRESHOLD_PCT: 90.0
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

例: `.env`（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 仮想環境を用意
3. 依存パッケージをインストール（例: duckdb / openai / defusedxml）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. 初期DBや監査テーブルの初期化（必要に応じて）

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 環境変数設定（.env 作成）
```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトからの利用例です。詳細は各モジュールの docstring を参照してください。

設定と DB 接続の準備:
```python
from kabusys.config import settings
import duckdb

# DuckDB に接続（ファイルパスは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))
```

日次 ETL の実行:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# today を指定（None なら date.today() を使う）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースセンチメントスコアの算出（OpenAI API キーが環境変数 OPENAI_API_KEY に設定されている前提）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026,3,20))
print(f"scored {n} codes")
```

市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20))
```

監査DBの初期化（監査テーブルを作る）:
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を監査用 DB に使う（必要に応じて別 DB を指定）
audit_conn = init_audit_db(settings.duckdb_path)
```

マーケットカレンダー関連のユーティリティ:
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date

d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

RSS フィード取得（ニュース収集の一部）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意：
- OpenAI を利用する関数は OPENAI_API_KEY を環境変数に設定するか、関数引数で api_key を渡してください。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN を必要とします（settings.jquants_refresh_token）。

---

## よく使うモジュール（抜粋）

- kabusys.config
  - settings: 環境変数ベースのアプリ設定
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult データクラス
- kabusys.data.jquants_client
  - fetch_* / save_* 関数、get_id_token
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.news_collector
  - fetch_rss（RSS の安全な取得／パース）
- kabusys.ai.news_nlp
  - score_news（銘柄ごとのニュース AI スコアリング）
- kabusys.ai.regime_detector
  - score_regime（市場レジーム判定）
- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査ログ初期化）
- kabusys.research
  - ファクター計算 / 特徴量解析ユーティリティ（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic 等）
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成

（主要ファイル・モジュールのツリー）
```
src/kabusys/
├── __init__.py
├── config.py
├── ai/
│   ├── __init__.py
│   ├── news_nlp.py
│   └── regime_detector.py
├── data/
│   ├── __init__.py
│   ├── audit.py
│   ├── calendar_management.py
│   ├── etl.py
│   ├── jquants_client.py
│   ├── news_collector.py
│   ├── pipeline.py
│   ├── quality.py
│   └── stats.py
├── research/
│   ├── __init__.py
│   ├── factor_research.py
│   └── feature_exploration.py
└── research/ (補助モジュール)
```

---

## 運用上の注意 / ベストプラクティス

- 本番運用（live）では KABUSYS_ENV を `live` に設定し、ログレベルや閾値を見直してください。
- ETL は定期バッチ（夜間）で走らせ、calendar (JPX) → prices → financials の順に取得するのが想定フローです。
- OpenAI 呼び出しはコストとレイテンシが発生するため、バッチでまとめて呼ぶか、料金ポリシーに留意してください。API 呼び出しはリトライ・フォールバック（0.0）を実装していますが、大量呼び出しには注意。
- RSS フィードは SSRF 対策やサイズ制限を組み込んでいますが、外部入力を扱う際はさらに監査／監視を行ってください。
- DuckDB の executemany に空リストを与えると問題になるバージョンがある旨をコード内で考慮しています。アップデート時は互換性を確認してください。

---

## テスト / 開発

- 自動環境ロードをテストで無効化する: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- OpenAI / J-Quants 呼び出し部分はモジュール内部で分離されており、単体テストではモック化しやすく設計されています（例: news_nlp._call_openai_api のパッチ等）。
- DuckDB を ":memory:" で初期化してユニットテストを行えます（init_audit_db(":memory:") など）。

---

README はモジュールの docstring と実装に基づいて作成しています。詳細な API 仕様や運用ドキュメントは各モジュールの docstring を参照してください。必要であれば、セットアップ用のスクリプト例や systemd / cron の起動例、さらに CI 向けのテスト手順などの追補を作成します。必要な内容を教えてください。