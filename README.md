# KabuSys

日本株向けのデータプラットフォーム & 自動売買／リサーチ用ライブラリです。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダー等を差分取得して DuckDB に保存する ETL
- RSS ベースのニュース収集とニュース→銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリング（ai.news_nlp）
- ETF 等を用いた市場レジーム判定（ai.regime_detector）
- 研究用ファクター計算（momentum / value / volatility 等）
- データ品質チェック、監査（トレース）用スキーマ生成

設計上の重要点：
- ルックアヘッドバイアス防止（内部で date.today() を直接参照しない等）
- DuckDB ベースの冪等保存（ON CONFLICT / UPDATE）
- 外部 API に対するリトライ・バックオフ・レート制御
- セキュリティ考慮（RSS の SSRF 対策、XML の安全パース等）

---

## 機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS → raw_news）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / run_all_checks）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC 計算（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数の自動読み込み（プロジェクトルートの .env/.env.local）
  - settings オブジェクト経由の設定参照

---

## 必要条件（主な依存ライブラリ）

- Python 3.10+
- duckdb
- openai
- defusedxml

（上記はコードから推測しています。実際の pyproject.toml / requirements.txt が存在する場合はそちらを優先してください）

---

## インストール

開発環境での典型的な手順例：

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール
   - pip install -e .
   - または最小依存を直接インストール:
     - pip install duckdb openai defusedxml

※ 実際の依存はプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## 環境変数（主なもの）

config.Settings で参照される主要環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
- OPENAI_API_KEY (必須 for ai.* を使う場合) — OpenAI API キー
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動的にプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数が優先）。  
自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ（DB 初期化等）

監査ログ用の DuckDB を初期化する例：

```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" でインメモリ DB も可
```

DuckDB 接続を他モジュールで使う例：

```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 以降、conn を ETL / scoring に渡して使用
```

---

## 使い方（主要なユースケース）

1) 日次 ETL を実行して J-Quants データを取得・保存する

```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成して ai_scores に書き込む

```
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境で利用
print(f"scored {count} symbols")
```

3) 市場レジーム判定を実行する

```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 市場カレンダーの更新ジョブ（夜間バッチ）

```
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
saved = calendar_update_job(conn)
print(f"saved {saved} calendar records")
```

5) 研究系ファクター計算・IC 等

```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
```

注意:
- ai モジュールは OpenAI API を呼び出します。OPENAI_API_KEY を設定してください。
- J-Quants API 呼び出しには rate limit（120 req/min）が組み込まれています。
- ETL / 保存関数は冪等（重複防止）になるよう設計されています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                       — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                    — ニュースセンチメント（OpenAI）
  - regime_detector.py             — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py              — J-Quants API クライアント（fetch/save）
  - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
  - etl.py                         — ETL 公開インターフェース
  - news_collector.py              — RSS ニュース収集
  - calendar_management.py         — 市場カレンダー管理
  - quality.py                     — データ品質チェック
  - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - audit.py                       — 監査ログスキーマ作成 / init_audit_db
- research/
  - __init__.py
  - factor_research.py             — ファクター計算
  - feature_exploration.py         — 将来リターン / IC / summary
- research/* other modules ...
- その他（strategy / execution / monitoring 等のパッケージは __all__ に含まれる想定）

（README はコードベースから抜粋しています。細かいファイル構成はプロジェクト実際の tree を参照してください）

---

## 注意事項 / 運用メモ

- Look-ahead バイアス防止のため、各モジュールは対象日以前のデータのみを参照する設計です。バックテスト等で内部ロジックをそのまま利用する場合は手順を守ってください。
- OpenAI や J-Quants の API キー・トークンは厳重に管理してください。
- ニュース収集・NLP は外部 API 呼び出しを伴います。コストとレート制限に注意してください。
- config はプロジェクトルートの .env / .env.local を自動読み込みします。テストや CI で自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

質問や追加したいサンプル（例: docker-compose や CI 設定、実運用の runbook 等）があれば教えてください。README に追記して整備します。