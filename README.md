# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ等を提供します。

---

## 概要

KabuSys は、以下を目的とする Python モジュール群です。

- J-Quants API からの差分 ETL（株価日足、財務、JPX カレンダー）
- RSS ニュースの収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI を利用したニュースセンチメント解析（銘柄別、マクロ）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを組合せ）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 取引監査（signal → order_request → execution のトレーサビリティ）
- DuckDB を用いたローカル DB 保存

設計方針として、バックテストでのルックアヘッドバイアス排除、冪等処理、堅牢なエラーハンドリング、外部 API のリトライ／レート制御などに配慮しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS fetch / preprocess / 保存ロジック）
  - 品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date): 銘柄別ニュースセンチメントを ai_scores に書込
  - regime_detector.score_regime(conn, target_date): 市場レジームを market_regime に書込
  - OpenAI 呼び出しは gpt-4o-mini を想定（JSON mode を利用）
- research/
  - calc_momentum / calc_volatility / calc_value（ファクター）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量解析）
- config.Settings: .env や環境変数から設定を読み込む（自動ロード機能あり）

---

## セットアップ手順

前提:
- Python 3.10 以上（`|` 型ヒント、match を利用しないが union 表記に依存）
- DuckDB、OpenAI SDK、defusedxml 等の依存が必要

推奨手順（一般的な例）:

1. 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. パッケージをインストール
   - pyproject.toml / poetry を使っている場合:
     ```bash
     poetry install
     ```
   - pip で開発インストールする場合（リポジトリルートで）:
     ```bash
     pip install -e .
     ```
   - 依存パッケージが分かっている場合:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数を設定
   - ルートに `.env` / `.env.local` を配置すると自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須（利用する機能に応じて設定）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（実行系を使う場合）
   - 任意:
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / 各種閾値、環境（KABUSYS_ENV）等

.env のサンプル（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_PASSWORD=your_password
```

---

## 使い方（簡単なコード例）

以下は基本的な利用例です。いずれの例も DuckDB 接続を渡して実行します。

- DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

# デフォルト path を使用
conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores テーブルへ書込
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数で設定
print("written:", n_written)
```

- 市場レジーム判定（market_regime テーブルに書込）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須
```

- 監査ログ DB の初期化（専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn に対して発注→約定の監査レコードを保存できます
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_value

mom = calc_momentum(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
```

- 設定値の参照
```python
from kabusys.config import settings

print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- AI 系関数は OpenAI の API キーを必要とします。api_key を引数で渡すことも可能です。
- ETL / DB 操作は DuckDB のスキーマ（テーブル）前提です。初期スキーマ作成手順が別途ある場合は先に実行してください（本リポジトリに schema 初期化関数がある場合はそちらを利用）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL の認証に使用）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール）
- KABU_API_PASSWORD — kabu API パスワード（発注等を行うモジュールで使用）
- KABUSYS_ENV — 動作環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）

.env の読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われ、.env → .env.local の順で上書きされます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - etl.py (公開ラッパー)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/__init__.py
- (その他: strategy / execution / monitoring 等のパッケージ公開が __init__ に含まれることを想定)

各モジュールの責務はファイル冒頭の docstring に記載されています。まずは data.pipeline.run_daily_etl、ai.news_nlp.score_news、ai.regime_detector.score_regime、data.jquants_client の順で動作確認するのが一般的です。

---

## 開発・テストのヒント

- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト用で環境を整えてください。
- OpenAI 呼び出しは各モジュールで _call_openai_api を抽象化しており、ユニットテスト時はパッチしてスタブ化できます（unittest.mock.patch）。
- J-Quants API や RSS のネットワーク呼び出しもモック化して単体テストを行うことを推奨します。
- DuckDB 接続は ":memory:" を渡してインメモリ DB でテスト可能です（init_audit_db なども対応）。

---

必要に応じて README を拡張します。セットアップ要件（requirements.txt / pyproject.toml の内容）や初期スキーマ作成コマンドがあれば、その情報を教えてください。README に追加して反映します。