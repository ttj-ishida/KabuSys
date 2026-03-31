# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、監査ログ（約定トレーサビリティ）などを含むモジュール群を提供します。

主な用途
- 日次ETLパイプラインで株価・財務・市場カレンダーを取得して DuckDB に保存
- ニュース記事の収集・前処理・LLM による銘柄センチメント評価（ai_scores）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）初期化ユーティリティ

バージョン: 0.1.0

---

## 機能一覧

- 環境変数/設定管理（自動 .env ロード、Settings オブジェクト）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化
- J-Quants API クライアント（レートリミット・再試行・トークン自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB へ冪等保存（ON CONFLICT）
- ETL パイプライン
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - ETLResult により処理結果を集約
- データ品質チェック（quality.run_all_checks 等）
- ニュース収集（RSS）
  - SSRF 対策、トラッキングパラメータ除去、前処理（URL 除去・空白正規化）
- ニュース NLP（OpenAI）
  - score_news: 銘柄ごとのセンチメントを ai_scores テーブルへ書き込み
  - LLM 呼び出しは再試行・レスポンス検証を実施
- 市場レジーム判定
  - score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM を合成して regime_label を market_regime に保存
- 研究用ユーティリティ
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（クロスセクション正規化）
- 監査ログ初期化
  - init_audit_schema / init_audit_db（DuckDB に監査テーブル群を作成）

---

## 動作環境・依存

- Python 3.10 以上（型注釈に `|` を利用）
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
- その他：標準ライブラリ（urllib, json, logging, datetime, typing 等）

実際のインストール時は requirements.txt / pyproject.toml に依存関係が記載されている前提でインストールしてください。例:
```
python -m venv .venv
source .venv/bin/activate
pip install -e .
# または
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存関係インストール
   - pip install -r requirements.txt もしくは pip install duckdb openai defusedxml
4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（と必要なら `.env.local`）を置くと自動で読み込まれます。
   - 必須環境変数
     - JQUANTS_REFRESH_TOKEN
     - OPENAI_API_KEY （score_news / score_regime 実行時に引数で渡すことも可能）
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション（デフォルトあり）
     - KABUSYS_ENV: development / paper_trading / live（既定: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）
     - DUCKDB_PATH（既定: data/kabusys.duckdb）
     - SQLITE_PATH（既定: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT 等の監視設定
5. 自動 .env ロードを無効化したい場合
   - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## 使い方（基本的な例）

以下はライブラリをインポートして主要機能を呼ぶための簡単な例です。実行前に上記の環境変数を設定してください。

- DuckDB 接続と日次 ETL 実行:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- 個別 ETL（株価のみ）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
```

- ニュース NLP（OpenAI を使って銘柄ごとのスコア生成）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY が必要
```

- 監査DB 初期化（監査ログ用の専用 DuckDB を作る）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降、order_requests 等の監査テーブルが作成されている
```

- 設定参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)         # Path
print(settings.is_paper)            # bool
token = settings.jquants_refresh_token  # 必須なら ValueError が出る
```

---

## 注意点 / 実装上のポイント

- Look-ahead バイアス防止:
  - 多くの関数は内部で datetime.today() や date.today() を参照しない設計（target_date を外から渡す）。
  - データ取得・解析は "その日までに利用可能だった情報" を尊重するよう注意が払われています。
- 自動 .env ロード:
  - プロジェクトルート（.git/pyproject.toml を探索）にある .env/.env.local を自動ロードします。`.env.local` は優先的に上書きします。
- セキュリティ:
  - news_collector は SSRF 対策、トラッキングパラメータ除去、受信サイズ制限などを実装しています。
- OpenAI 呼び出し:
  - gpt-4o-mini（モデル文字列）に JSON Mode を用いる設計。API 失敗時のフォールバックやリトライが組み込まれています。
  - score_news / score_regime は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を使います。
- J-Quants クライアント:
  - レートリミッタ（120 req/min）、指数バックオフ、401 の場合の自動トークンリフレッシュを備えています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化（version 等）
- config.py — 環境変数 / Settings（.env 自動ロードロジック含む）
- ai/
  - __init__.py
  - news_nlp.py — ニュースを LLM でスコアリングする主要ロジック
  - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - pipeline.py — ETL パイプライン（run_daily_etl など）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログ（テーブル DDL / 初期化）
  - news_collector.py — RSS 取得・前処理・保存ユーティリティ
- research/
  - __init__.py
  - factor_research.py — モメンタム・ボラティリティ・バリュー等の計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー等

---

## 開発・テストについて（補足）

- モジュール内のプライベートな外部API呼び出しはテスト可能なように、呼び出し関数を差し替えやすく実装されています（例: _call_openai_api を unittest.mock.patch でモック）。
- DuckDB をインメモリ（":memory:"）で用いることで単体テストが容易です。
- 自動 .env ロードはテストで干渉する場合があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

---

もし README に追加してほしい内容（例: CI 設定、具体的な .env.example、実行用スクリプトや systemd ユニット例、テスト実行方法、API の詳細仕様など）があれば教えてください。必要に応じて追記・整形します。