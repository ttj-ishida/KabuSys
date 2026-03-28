# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤の一部を実装した Python パッケージです。  
ETL（J-Quants からのデータ取得・保存）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（オーダー/約定トレース）等のユーティリティを提供します。

---

## 主要な機能

- ETL パイプライン（株価 / 財務 / 市場カレンダーの差分取得・保存・品質チェック）
- J-Quants API クライアント（レート制御・リトライ・トークンリフレッシュ対応）
- ニュース収集（RSS）とニュース NLP（OpenAI を使った銘柄ごとのセンチメント評価）
- 市場レジーム判定（ETF 1321 の MA + マクロニュースの LLM スコアを合成）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量探索ユーティリティ
- カレンダー管理（JPX カレンダーの保持と営業日判定）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）と初期化ユーティリティ
- DuckDB を主な永続化先として想定

---

## 前提条件 / 依存関係

- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発時はパッケージを編集可能モードでインストール:
pip install -e .
```

（実プロジェクトでは requirements.txt / pyproject.toml を使って依存管理してください）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化
2. 依存ライブラリをインストール（上記参照）
3. 環境変数を設定（.env または環境変数）
   - パッケージはプロジェクトルート（.git または pyproject.toml がある場所）から自動で `.env` / `.env.local` を読み込みます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
4. DuckDB ファイルの格納ディレクトリなどを作成（例: `data/`）

.env（例）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス（省略時は data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境 / ログレベル
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

環境変数は `.env` → `.env.local` の順で上書きされ、OS 環境変数が最優先になります。

---

## 使い方（代表的な例）

以下は主要 API の簡単な使用例です。全て DuckDB 接続を受け取る設計になっているため、まず接続を作成してください。

共通: DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path はデフォルトで data/kabusys.duckdb
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# 指定日（省略時は今日）に対する ETL 実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコア（銘柄ごとの AI スコア）を生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY、または api_key 引数で指定可能
written = score_news(conn, target_date=date(2026, 3, 19))
print(f"書き込んだ銘柄数: {written}")
```

3) 市場レジーム判定を行う
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 19))
# market_regime テーブルに結果を書き込みます
```

4) 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これにより監査用テーブル群とインデックスが作成されます
```

5) 研究ユーティリティの利用例（モメンタムやボラティリティ）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_volatility

target = date(2026, 3, 19)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
```

注意点:
- LLM 呼び出しに関するテストは、各モジュールで `_call_openai_api` をモックすることで実行できます（ユニットテスト向けフックが用意されています）。
- 各関数はルックアヘッドバイアスを避ける設計になっており、内部で datetime.today() を参照しない実装です（target_date を明示してください）。
- OpenAI の呼び出しは `openai.OpenAI` クライアントを使用します。API キーは環境変数 `OPENAI_API_KEY` で指定するか、関数引数で渡してください。

---

## 主要モジュールと API（抜粋）

- kabusys.config
  - settings: 環境変数から各種設定を取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token（自動リフレッシュとリトライ対応）
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（実行結果のデータクラス）
- kabusys.data.quality
  - run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.news_collector
  - fetch_rss / preprocess_text / （RSS → raw_news 保存ロジックを呼ぶユーティリティ）
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.audit
  - init_audit_schema / init_audit_db

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須 for J-Quants)
- KABU_API_PASSWORD (必須 for kabu API)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必須 for LLM 関連)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

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
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: schema 初期化等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research, monitoring, execution, strategy 等（パッケージ公開のための __all__ で参照）

※ 上記は本リポジトリに含まれる主要モジュールの抜粋です。

---

## 運用上の注意

- DuckDB を永続化する場合、ファイルのバックアップや権限管理に注意してください。
- LLM（OpenAI）の呼び出しはコストとレイテンシが発生します。バッチサイズやリトライ設定を業務要件に合わせて調整してください。
- ETL は J-Quants API レート制限に合わせた実装（120 req/min）とリトライを備えていますが、API 側の仕様変更には注意してください。
- 監査テーブルは削除を想定しない仕様です（監査目的）。スキーマ変更は互換性に注意して行ってください。

---

## テスト / モック

- LLM 呼び出しやネットワーク呼び出しは、各モジュールで外部呼び出しをラップしているため、ユニットテストではこれらの内部関数（例: kabusys.ai.news_nlp._call_openai_api、kabusys.data.news_collector._urlopen など）をモックすることで高速・再現性のあるテストが可能です。
- DuckDB を ":memory:" で接続してテスト用のインメモリ DB を作成できます（例: duckdb.connect(":memory:")）。

---

この README はコードベースの主要点をまとめたものです。詳細な使用法や追加のユーティリティは各モジュール（docstring）をご参照ください。必要であれば使用例やデプロイ手順、CI/CD、より詳しい設定例を追加します。