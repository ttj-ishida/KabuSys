# KabuSys

日本株向けのデータプラットフォーム／自動売買基盤のコアライブラリです。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュース収集・NLP（OpenAI）によるセンチメント評価、ファクター計算、監査ログ（発注フローのトレーサビリティ）などを含むモジュール群を提供します。

---

## 主要な機能一覧

- 環境変数 / 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 設定値の検証（例: KABUSYS_ENV, LOG_LEVEL）
- データ ETL（J-Quants API 経由）
  - 株価日足（raw_prices / save_daily_quotes）
  - 財務情報（raw_financials / save_financial_statements）
  - JPX マーケットカレンダー（market_calendar）
  - 差分取得、ページネーション、トークン自動リフレッシュ、レート制御、リトライ
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付整合性チェック
  - QualityIssue で問題を集約
- ニュース収集
  - RSS フィード取得（SSRF・サイズ制限・トラッキングパラメータ除去等の安全対策）
  - raw_news / news_symbols へ冪等保存（設計に沿った処理）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（gpt-4o-mini, JSON Mode）
  - チャンク処理、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定（AI + テクニカル指標）
  - ETF 1321 の 200 日移動平均乖離 + マクロニュースセンチメントの合成
  - market_regime テーブルへ冪等書き込み
- 研究用ファクター計算 / 特徴量解析
  - Momentum、Volatility、Value、将来リターン、IC、サマリー等
  - zscore_normalize 等の統計ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
  - 監査用の DB 初期化関数（init_audit_db, init_audit_schema）

---

## 要件（推奨）

- Python >= 3.10
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

具体的なインストール方法はプロジェクトのパッケージ管理に依存します。例（pip）:

```
pip install duckdb openai defusedxml
# またはプロジェクトルートで
pip install -e .
```

（pyproject.toml / requirements.txt がある場合はそちらを使用してください）

---

## 環境変数（主なもの）

config.Settings で参照される主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot Token
- SLACK_CHANNEL_ID (必須) — 通知先チャネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — development | paper_trading | live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）

自動ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` → `.env.local` の順で自動読み込みを行います。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

README 例の .env（参考）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 取得
2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -r requirements.txt もしくは pip install duckdb openai defusedxml
4. .env を作成して必要な環境変数を設定
   - リポジトリルートに .env / .env.local を置く（settings により自動ロード）
5. DuckDB ファイルや監査 DB の初期化（必要に応じて）
   - Python REPL やスクリプトから init_audit_db 等を実行

---

## 使い方（主要な例）

以下は簡単な利用例（Python スクリプト等から呼び出す想定）。

1) DuckDB 接続を作成して日次 ETL を実行する:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path を使いたい場合:
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))

# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 19))
print(result.to_dict())
```

2) ニュースセンチメント（OpenAI を利用）で ai_scores を作成する:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か引数で指定
count = score_news(conn, target_date=date(2026, 3, 19))
print(f"scored {count} symbols")
```

3) 市場レジーム判定（MA200 + マクロニュース）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 19))
```

4) 監査ログ DB の初期化:

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.sqlite_path ではなく専用 DuckDB ファイルを作ることも可能
conn = init_audit_db(settings.duckdb_path)
# これで監査テーブルが作成されます
```

注記:
- OpenAI 呼び出しは `OPENAI_API_KEY` 環境変数または各関数の `api_key` 引数で指定できます。
- テスト時は各モジュールの内部 API 呼び出し（例: kabusys.ai.news_nlp._call_openai_api, kabusys.data.news_collector._urlopen）をモックして差し替えることが想定されています（README 内のソースコメント参照）。

---

## よく使うモジュール（抜粋）

- kabusys.config
  - settings: 環境変数に基づくアプリケーション設定
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.news_collector
  - fetch_rss, preprocess_text（RSS 収集・正規化）
- kabusys.ai.news_nlp
  - score_news（銘柄ごとのニュースAIスコア）
- kabusys.ai.regime_detector
  - score_regime（市場レジーム判定）
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.audit
  - init_audit_schema, init_audit_db（監査ログ初期化）

---

## ディレクトリ構成

プロジェクト内の主要ファイル・モジュール構成（抜粋）:

- src/kabusys/
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
    - stats.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールはコメントと docstring で設計方針やフェイルセーフ挙動を詳細に記述しています。実運用では DuckDB に永続化したテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）との組み合わせで運用します。

---

## テスト / モックに関するヒント

- OpenAI 呼び出しは内部で _call_openai_api をラップしているため、ユニットテストでは該当関数を patch して返却値を制御できます。
- news_collector のネットワーク部分は _urlopen を差し替え可能で、SSRF や外部通信を行わずにテストできます。
- J-Quants の HTTP 部分は urllib を直接使っているため、network に依存するロジックは HTTPError / URLError を模した例外で動作を確認できます。

---

## 運用上の注意点

- AI（OpenAI）呼び出しや外部 API 呼び出しはコストとレート制限があるため、本番実行前に設定やバッチ処理の頻度を確認してください。
- Look-ahead bias を防ぐため、関数群は target_date を明示して使用する設計です。内部で date.today() を直接参照する実装は原則避けています。
- ETL・品質チェック中に一部処理が失敗しても他処理は継続する設計（問題は ETLResult.errors / quality_issues に集約されます）。ログ監視とアラートを併用することを推奨します。

---

必要であれば、README に含めるサンプル .env.example、より詳細なセットアップ（Docker / CI / DB スキーマ作成手順）や運用プレイブックを追加で作成します。どの情報を優先して追記しましょうか？