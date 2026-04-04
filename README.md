# KabuSys

日本株向けの自動売買支援ライブラリ / データプラットフォーム。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、ファクター計算、監査ログ（発注・約定トレース）、市場カレンダー管理など、アルゴリズム取引に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能

- データ ETL
  - J-Quants API からの日次株価（OHLCV）・財務データ・JPX カレンダー取得（差分取得・ページネーション対応）
  - DuckDB へ冪等（ON CONFLICT DO UPDATE）で保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL のワンストップ実行（run_daily_etl）

- ニュース NLP（OpenAI）
  - RSS 収集 → raw_news 保存（SSRF 対策・トラッキング除去・ID 決定）
  - 銘柄ごとのニュース集約と LLM によるセンチメント評価（score_news）
  - マクロ記事を用いた市場レジーム判定（ETF 1321 の MA200 乖離 + LLM マクロセンチメント → score_regime）

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン・IC・統計サマリーなどのユーティリティ

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査スキーマを初期化・管理（init_audit_schema, init_audit_db）
  - 発注から約定までのトレーサビリティ（UUID を利用）

- マーケットカレンダー
  - market_calendar の保存・参照、営業日判定・翌営業日/前営業日検索、夜間更新ジョブ（calendar_update_job）

- 設定管理
  - .env / .env.local / 環境変数からの設定読み込み（自動ロード。必要に応じて無効化可能）

---

## 前提（推奨環境）

- Python 3.10+
- ライブラリ（主な依存）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - （その他: 標準ライブラリのみで多くの処理を実装）

必要なパッケージはプロジェクトの requirements.txt を用意している前提で:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
requirements.txt がない場合は最低限:
```bash
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. .env を作成（以下を参照）
4. DuckDB データベースや監査用 DB の初期化（README の「使い方」を参照）

### 環境変数（.env 例）

プロジェクトは .env（および .env.local）を自動ロードします。プロジェクトルートは `.git` または `pyproject.toml` を基準に検出します。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

最低限設定が必要な環境変数（例）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabu ステーション（発注等を行う場合）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行監視など（任意）
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=0

# 環境 / ログ
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

追加の設定:
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知を行う場合）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）

---

## 使い方（主な API と例）

以下は Python REPL やスクリプトから呼ぶ例です。DuckDB 接続は `duckdb.connect(path)` を利用します。

- ETL（日次パイプライン実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI を使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OpenAI API key は環境変数 OPENAI_API_KEY で解決されます
num_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", num_written)
```

- 市場レジーム判定（MA200 とマクロセンチメント）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査専用 DuckDB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- カレンダー夜間更新ジョブ（J-Quants から取得）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- J-Quants の直接利用例（ID トークン取得）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # JQUANTS_REFRESH_TOKEN を参照
```

注意:
- OpenAI を使う関数は API キー（OPENAI_API_KEY）を必須とします。関数引数で明示的に渡すことも可能です。
- DuckDB SQL スキーマ（raw_prices, raw_financials, raw_news など）は ETL ツールや初期化スクリプトで作成する必要があります（プロジェクトにスキーマ定義がある前提）。

---

## よく使うモジュール（要約）

- kabusys.config
  - settings: 環境変数ラッパー（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）
  - 自動 .env ロード機能（.env, .env.local）

- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存機能）
  - pipeline: ETL パイプライン（run_daily_etl など）
  - quality: データ品質チェック
  - calendar_management: マーケットカレンダー管理・営業日判定
  - news_collector: RSS 取得と raw_news 保存
  - audit: 監査スキーマ初期化

- kabusys.ai
  - news_nlp.score_news: 銘柄単位ニュースの LLM スコアリング
  - regime_detector.score_regime: 日次の市場レジーム判定（1321 の MA200 + マクロセンチメント）

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize

---

## ディレクトリ構成

（主要ファイルのみを抜粋）

- src/
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
      - quality.py
      - calendar_management.py
      - news_collector.py
      - audit.py
      - etl.py
      - stats.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - ...
    - research/__init__.py
    - other modules...
- pyproject.toml / setup.cfg / (または別のパッケージ管理ファイル)
- .env.example (プロジェクトルートに置くことを推奨)

---

## 開発メモ / 注意点

- Look-ahead bias 回避の方針に基づき、多くの関数は内部で現在時刻を直接参照しない設計です。API 呼び出しやクエリは target_date を明示して呼んでください。
- OpenAI リクエストは JSON Mode を使って厳密な JSON を期待する実装になっています。レスポンスパース失敗や API エラー時はフェイルセーフで 0.0 を返す等の設計です。
- J-Quants API はレート制限 120 req/min を守るための RateLimiter を組み込んでいます。トークン自動リフレッシュやリトライ（指数バックオフ）にも対応しています。
- news_collector は SSRF 考慮（リダイレクト検査・プライベートホスト拒否）や XML パースの安全化（defusedxml）を行っています。
- DuckDB の executemany に関する互換性（空リスト不可 等）に注意して実装しています。

---

## ライセンス / 責任

この README はコードベースの説明です。実際に運用する場合は自己責任で API キー・認証情報の管理、発注のテスト（紙取引環境での検証）を行ってください。実運用では取引戦略の検証・リスク管理を十分に行ってください。

---

README に不足している点や、特定の機能（例: 発注フロー、kabu ステーション連携、より詳しい DB スキーマ）の記載が必要であれば、その項目を指定してください。必要に応じてサンプルスクリプトや schema DDL も作成します。