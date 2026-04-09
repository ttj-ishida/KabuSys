# KabuSys

日本株のデータプラットフォームと自動売買を支援するライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）など、アルゴリズム取引に必要な基盤処理を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数（主な設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価（OHLCV）・財務データ・マーケットカレンダーの差分 ETL
- RSS ニュース収集と OpenAI を利用したニュースごとのセンチメント（ai_scores）生成
- ETF の移動平均乖離とマクロニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- 研究（ファクター計算、将来リターン、IC 計算、統計ユーティリティ）
- 監査（signal → order → execution）のテーブル定義と初期化
- データ品質チェック（欠損、スパイク、重複、日付不整合）

設計方針として、ルックアヘッドバイアスを防ぐために「target_date を明示する」「内部で datetime.today() を直接参照しない」等が徹底されています。

---

## 機能一覧（主要）

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / id_token 管理 / レート制限・リトライ）
  - カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS fetch, テキスト前処理, SSRF 対策）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログ初期化（init_audit_schema, init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとのセンチメントを ai_scores テーブルへ保存）
  - 市場レジーム判定（score_regime: ETF1321 の MA とマクロニュースを合成）
- research
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, factor summary, rank）
- config
  - 環境変数 / .env 管理（自動ロード機能、必須設定の検証）

---

## セットアップ手順

1. リポジトリをクローン / コピー
   - 例: git clone <リポジトリ>

2. Python 環境
   - Python 3.10+ を推奨（typing の一部構文や型ヒントを利用）
   - 仮想環境の作成を推奨
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml
   - 実運用では logging / sqlite3 など標準ライブラリも利用します

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install -e . 等でインストールしてください。

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env` (必要に応じて `.env.local`) を置くと自動で読み込まれます（config.py の自動読み込み）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データベースパスの確認
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`（settings.duckdb_path）
   - 監視用 SQLite は `data/monitoring.db`（settings.sqlite_path）
   - Paper Trading 用 SQLite は `data/paper_trading.db`（settings.paper_sqlite_path）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants 用リフレッシュトークン（get_id_token に使用）

- KABU_API_PASSWORD
  - kabu ステーション API のパスワード（必要箇所で参照）

任意 / デフォルトあり:
- OPENAI_API_KEY
  - OpenAI API を使う処理（news_nlp.score_news / regime_detector.score_regime）で使用
- KABUSYS_ENV (development | paper_trading | live) → デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) → デフォルト: INFO
- DUCKDB_PATH → デフォルト: data/kabusys.duckdb
- SQLITE_PATH → デフォルト: data/monitoring.db
- PAPER_FILL_MODE → paper trading の fill シミュレーション ("instant" | "partial" | "never" | "reject")
- PAPER_TRADING_SQLITE_PATH → デフォルト: data/paper_trading.db
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

.env の例（最小）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（主要 API の例）

以下はライブラリの典型的な使い方例です。実行前に .env と依存ライブラリを整えてください。

- DuckDB 接続を作成して ETL を実行（日次 ETL）:
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を省略すると今日（settings.env に依存）
print(result.to_dict())
```

- ニュースの NLP スコアリング（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # target_date を明示
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# conn は初期化済みの DuckDB 接続
```

- カレンダーの夜間更新ジョブ実行
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"保存レコード数: {saved}")
```

注意:
- OpenAI を使う機能は OPENAI_API_KEY を渡すか環境変数に設定してください。関数は引数で api_key を上書きできます。
- すべての「日次処理系」関数は Look-ahead バイアスを避けるため target_date を引数に取る設計になっています。バックテストや再現性のために明示的に日付を指定することを推奨します。

---

## ディレクトリ構成（src/kabusys の主なファイル）

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュース NLP スコアリング（score_news）
    - regime_detector.py    # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント（fetch/save/get_id_token）
    - pipeline.py           # ETL パイプライン（run_daily_etl 他）
    - etl.py                # ETLResult の公開
    - calendar_management.py# マーケットカレンダー管理
    - news_collector.py     # RSS ニュース収集（SSRF 対策等）
    - quality.py            # データ品質チェック
    - stats.py              # z-score 等統計ユーティリティ
    - audit.py              # 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py    # Momentum / Value / Volatility の計算
    - feature_exploration.py# forward returns, IC, factor summary, rank
  - research/（その他研究関連ファイル）

各モジュールは duckdb 接続（DuckDBPyConnection）を引数に受け取る設計が中心で、外部副作用（発注 API など）を持たない研究系関数と、ETL/データ取得系の関数が明確に分離されています。

---

## 補足 / 実運用での注意

- API レート制限・リトライ
  - J-Quants クライアントは 120 req/min の制限に従うレートリミッタを実装しています。fetch 系関数はページネーションとリトライ処理を備えています。
  - OpenAI 呼び出しはリトライロジック・レスポンスの堅牢なパースを行いますが、API 依存部分の運用時はログとレート管理に注意してください。

- ロギング
  - 設定値 LOG_LEVEL でログレベルを制御します（デフォルト INFO）。

- テスト/モック
  - OpenAI 呼び出しやネットワークリクエストはテスト時に差し替えられるよう関数内部で分離されています（例: _call_openai_api の差し替え）。

- DB スキーマ
  - save_* 関数は ON CONFLICT ベースで冪等性を確保します。初回は適切なスキーマ作成が必要（プロジェクト側でスキーマ初期化コードを実装してください）。

---

フィードバックや README に追加してほしい具体的な使い方（例: systemd サービス化、Airflow ジョブ設計、バックテストでの使用例など）があれば教えてください。必要に応じてサンプルコマンドやワークフロー図を追加します。