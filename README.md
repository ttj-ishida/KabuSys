# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買を想定したライブラリ群です。J-Quants からのデータ取得（ETL）、ニュース収集、AI によるニュースセンチメント評価、ファクター計算、監査ログ（オーダー→約定トレーサビリティ）、マーケットカレンダー管理などを提供します。

主なモジュール:
- kabusys.data: ETL / J-Quants クライアント、ニュース収集、カレンダー、品質チェック、監査スキーマ
- kabusys.ai: ニュースNLP（センチメント）・市場レジーム判定（OpenAI を使用）
- kabusys.research: ファクター計算・特徴量探索・統計ユーティリティ
- kabusys.config: 環境変数 / 設定管理

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）
- 使い方（クイックスタート）
- ディレクトリ構成
- 補足 / 注意点

---

## プロジェクト概要

KabuSys は「データ取得（ETL） → 品質チェック → 特徴量計算 → AI によるセンチメント/レジーム判定 → 監査可能な発注トレース」というワークフローを想定した日本株用のフレームワークです。バックテストやポートフォリオ構築、実取引（kabuステーション 経由）を行うための基盤要素を提供します。

設計上の特徴:
- DuckDB を用いたローカル DB にデータを保存（デフォルト: data/kabusys.duckdb）
- J-Quants API との差分 ETL（ページネーション・レート制御・再取得）
- ニュースの収集と前処理（RSS）、記事→銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（JSON Mode）
- レジーム判定（ETF 1321 の MA とマクロニュースを合成）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）テーブルの初期化ユーティリティ

---

## 機能一覧

- データ取得 / ETL
  - run_daily_etl（市場カレンダー / 株価 / 財務データの差分取得・保存・品質チェック）
  - J-Quants クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - 差分取得・保存は冪等（ON CONFLICT DO UPDATE）で実装

- ニュース
  - RSS フィードの安全な取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - 前処理（URL 除去・空白正規化）
  - raw_news / news_symbols への保存（冪等）

- AI（OpenAI を使用）
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF 1321 の MA とマクロニュースセンチメントで市場レジームを判定し market_regime に保存

- リサーチ
  - calc_momentum / calc_value / calc_volatility: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: 特徴量探索ツール
  - zscore_normalize: クロスセクション正規化ユーティリティ

- データ品質・カレンダー
  - market_calendar の管理（夜間バッチ更新）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - get_trading_days / next_trading_day / prev_trading_day / is_sq_day

- 監査（Audit / トレーサビリティ）
  - init_audit_schema / init_audit_db: signal / order / execution の監査テーブルを初期化

- 設定管理
  - .env (プロジェクトルート) 自動読み込み（CWD 依存しない探索）
  - 環境に応じたフラグ（development / paper_trading / live）

---

## 必要条件

- Python 3.10+
- 主要依存（抜粋）
  - duckdb
  - openai
  - defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。ここに挙げたものはソースから推測した主な依存です。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （実プロジェクトでは pyproject.toml または requirements.txt を使ってください:
    pip install -r requirements.txt や pip install -e .）

4. 環境変数設定
   - プロジェクトルートに .env（および .env.local）を作成してください。
   - 自動読み込みはデフォルトで有効です。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. データベースディレクトリ等の準備
   - デフォルトの DuckDB パスは data/kabusys.duckdb、監視用 SQLite パスは data/monitoring.db です。必要に応じてディレクトリを作成してください。

---

## 環境変数（.env の例）

必須:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- OPENAI_API_KEY=sk-...

オプション（デフォルトがあるもの）:
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development  # development | paper_trading | live
- LOG_LEVEL=INFO

（README に示したキーを .env.example として保存するとよいです）

設定の自動読み込み:
- kabusys.config モジュールは .env/.env.local をプロジェクトルートから探索して自動読み込みします。
- 自動ロードを無効化する: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（クイックスタート）

以下はライブラリをインポートして主要処理を実行する最小例です。実行前に必要な環境変数（特に J-Quants token / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を開いて日次 ETL を走らせる例:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

# デフォルトのパスを使う場合:
# from kabusys.config import settings
# db_path = settings.duckdb_path

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント評価（OpenAI API キーが必要）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB を初期化（別 DB を使う例）:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以降、order/signals/executions の操作にこの conn を使用
```

- ファクター計算（research）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要なファイル構成（src/kabusys 以下）です。機能別にディレクトリ分けされています。

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
    - etl.py (ETLResult エクスポート)
    - calendar_management.py
    - news_collector.py
    - stats.py
    - quality.py
    - audit.py
    - pipeline.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（など他モジュール）
  - researchパッケージ内で zscore_normalize を data.stats から利用

（実際のリポジトリではさらに補助スクリプトや tests、CI 設定が含まれる可能性があります）

---

## 補足 / 注意点

- OpenAI 利用
  - news_nlp と regime_detector は OpenAI の Chat Completions（gpt-4o-mini など）を使います。API キーが必要です（OPENAI_API_KEY 環境変数か関数引数で指定）。
  - API 失敗時のフェイルセーフ実装があり、多くのケースでスコアは 0.0 にフォールバックしますが、使用時はレートやコストに注意してください。

- J-Quants API
  - get_id_token はリフレッシュトークンから ID トークンを取得します。J-Quants の利用規約・レート制限に従ってください。
  - jquants_client はリトライ・レート制御を備えています。

- DB（DuckDB）
  - ETL / 保存処理は基本的に冪等（ON CONFLICT DO UPDATE）で設計されています。バックフィルや再取得のパラメータにより過去データの上書きを行います。
  - 実行前にスキーマ（raw_prices, raw_financials, market_calendar, raw_news 等）を作成しておく必要があります（通常は別の schema 初期化モジュールで生成される想定）。

- セキュリティ
  - news_collector は SSRF 対策、XML の安全なパース（defusedxml）などを実装していますが、運用時はさらにネットワーク制限や監査を行ってください。

---

問題が発生したり、README に追加してほしい利用例・コマンドがあれば教えてください。README を実際の環境（pyproject / requirements）に合わせて調整できます。