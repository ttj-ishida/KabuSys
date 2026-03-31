# KabuSys

日本株向けのデータプラットフォーム / 研究・自動売買基盤のライブラリ群です。ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットカレンダー管理、ファクター計算、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアスを防止するため、内部処理は explicit な target_date を受け取り、datetime.today()/date.today() を直接参照しない箇所が多くあります。
- DuckDB をデータ層に用い、SQL と Python を組み合わせて高効率に処理します。
- 外部 API 呼び出し（J-Quants, OpenAI 等）はリトライ・レート制御・フェイルセーフを備えています。
- 冪等性（ON CONFLICT / idempotent 保存）を重視しています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（.env）と自動読み込み
- 使い方（主要な API の例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータ収集・保管・品質管理・特徴量生成・ニュース NLP・市場レジーム判定・監査ログ作成までをカバーするモジュール群です。バックテスト・研究用途および実運用（paper/live）を想定して設計されています。

主な利用ケース
- J-Quants API を用いた株価・財務・マーケットカレンダーの ETL
- raw_news（RSS）収集と OpenAI を用いたニュースセンチメント付与 (ai_scores)
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と探索的解析（IC, forward returns）
- 市場レジーム（bull/neutral/bear）判定（ETF + マクロニュース + LLM）
- 監査用テーブル（signal / order_request / executions）生成・初期化
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 機能一覧

- config
  - 環境変数読み込み（.env / .env.local を自動読み込み、無効化フラグあり）
  - 設定のラッパー（settings）

- data
  - jquants_client: J-Quants API クライアント（取得 + DuckDB への冪等保存）
  - pipeline: 日次 ETL 実行（run_daily_etl など）と ETL 結果クラス
  - calendar_management: 市場カレンダー管理・営業日判定等
  - news_collector: RSS 取得・前処理・raw_news 保存用ユーティリティ（SSRF 対策、サイズ制限）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログスキーマ作成・初期化（監査用 DuckDB DB の init）
  - stats: 汎用統計（zscore_normalize）

- ai
  - news_nlp.score_news: ニュースを銘柄別に集約して OpenAI でスコアリングし ai_scores に保存
  - regime_detector.score_regime: ETF とマクロニュース（LLM）を合成して market_regime に書き込み

- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型合成などで | を使用）
- ネットワークアクセス（J-Quants / OpenAI を使用する場合）

推奨パッケージ例（requirements.txt の一例）
- duckdb
- openai
- defusedxml

インストール例（仮想環境推奨）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 開発時はパッケージとしてインストール（プロジェクトルートに pyproject.toml がある想定）
pip install -e .
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（jquants_client.get_id_token が使用）
- KABU_API_PASSWORD：kabuステーション API パスワード（注文実行周りで使用想定）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：通知先チャネル ID

任意 / デフォルトあり
- KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
- LOG_LEVEL：DEBUG/INFO/...
- KABU_API_BASE_URL：kabuAPI のベース URL（デフォルトローカル）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト data/monitoring.db）
- OPENAI_API_KEY：OpenAI API キー（ai.score_* 関数で未指定時に参照）

プロジェクト内で .env / .env.local がある場合、config モジュールがプロジェクトルート（.git または pyproject.toml を検出）を基に自動読み込みします。自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env（最低限の例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方

以下は代表的な使い方のサンプルです。実際はログ・例外処理・ID トークンの管理などを適宜実装してください。

1) DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの NLP スコアリング（OpenAI を使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると OPENAI_API_KEY を使用
print(f"scored {count} symbols")
```

3) 市場レジーム判定を実行（ETF 1321 の MA + マクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用の DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # ディレクトリは自動生成されます
```

5) J-Quants データを単体で取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.config import settings
import duckdb
from datetime import date

records = fetch_daily_quotes(date_from=date(2026, 3, 1), date_to=date(2026, 3, 20))
conn = duckdb.connect(str(settings.duckdb_path))
saved = save_daily_quotes(conn, records)
```

6) ファクター計算・研究用機能
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect(str(settings.duckdb_path))
mom = calc_momentum(conn, date(2026, 3, 20))
fwd = calc_forward_returns(conn, date(2026, 3, 20))
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

注意点
- OpenAI 呼び出しは gpt-4o-mini（JSON Mode）を利用する想定です。API コール回数は有料かつレート制限があります。
- ETL / API 呼び出し系はリトライとレート制御を行いますが、キー・トークンの管理は利用者側で行ってください。
- DuckDB の executemany に空リストを与えると動作しないバージョンの考慮がコード内にあります。空リストを書き込まない実装になっています。

---

## ディレクトリ構成

以下は主要なファイルとディレクトリの一覧（src/kabusys 配下）。実際のリポジトリには pyproject.toml / README.md / tests 等が含まれる想定です。

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py (ETLResult 再エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/（他補助モジュール）
  - ai/（ニュース NLP / レジーム判定）
  - data/（ETL・クライアント・品質チェック・監査）

（上記は本リポジトリに含まれている主なモジュールのサマリです）

---

## 補足 / トラブルシューティング

- .env 自動読み込み
  - プロジェクトルート判定は src/kabusys/config.py の _find_project_root() が .git または pyproject.toml を親ディレクトリから探索して決定します。
  - 自動読込を無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- OpenAI キー
  - score_news / score_regime の api_key 引数を指定しない場合は環境変数 OPENAI_API_KEY が参照されます。未設定の場合は ValueError が送出されます。

- J-Quants 認証
  - get_id_token() は settings.jquants_refresh_token を利用して ID トークンを取得します。リフレッシュトークンを .env に設定してください。

- ログ
  - settings.log_level でログレベルを制御できます（例: LOG_LEVEL=DEBUG）。

---

もし README に追加したい例（CLI の使い方、docker-compose、CI 設定、サンプル .env.example の具体的内容など）があれば、用途に合わせて追記します。