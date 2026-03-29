# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター研究、監査ログ（DuckDB）など、自動売買システム構築に必要な主要コンポーネントを含みます。

主な特徴
- J-Quants API を用いた差分 ETL（株価 / 財務 / カレンダー）
- DuckDB ベースのデータ保存・冪等保存ロジック
- ニュース収集（RSS）と OpenAI を利用した銘柄別センチメントスコアリング（gpt-4o-mini, JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と研究ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal, order_request, executions テーブル）と初期化ユーティリティ
- 環境変数／.env の自動ロード（プロジェクトルート探索）

---

## 機能一覧（抜粋）

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（ページネーション・リトライ・レート制御対応）
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
  - ニュース収集: RSS 取得・前処理・raw_news への保存ロジック（SSRF / Gzip / トラッキング除去対応）
  - 品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF 1321 の MA200 とマクロセンチメントを合成して market_regime へ書き込み
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - Settings クラスで環境変数をラップ（settings オブジェクト経由で利用）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型ヒントで Python 3.10+ の構文を使用）
- 主な依存ライブラリ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - その他: 標準ライブラリで実装されている部分も多いですが、実行環境に応じて追加が必要です。

インストール例（仮）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# ここにプロジェクトを editable install する場合:
# pip install -e .
```

（プロジェクト配布時は requirements.txt / pyproject.toml を用意してください）

---

## 環境変数 / .env

KabuSys は .env（および .env.local）から設定を自動ロードします。プロジェクトルートは `.git` または `pyproject.toml` を基準に検出します。環境変数を明示的にセットしている場合は OS 環境変数が優先されます。

自動ロードを無効にする場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL の認証）
- KABU_API_PASSWORD : kabuステーション API のパスワード（発注部分がある場合）
- SLACK_BOT_TOKEN : Slack 通知用 Bot Token
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）

任意・デフォルト
- KABUSYS_ENV : development | paper_trading | live（デフォルト development）
- LOG_LEVEL : DEBUG|INFO|...（デフォルト INFO）
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH / SQLITE_PATH : 各データベースファイルパス（デフォルト data/...）

例: .env.example
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

設定値はコードから次のように参照できます:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live
```

---

## セットアップ手順（簡易）

1. Python 環境を用意（3.10+）
2. 必要パッケージをインストール（duckdb, openai, defusedxml 等）
3. プロジェクトルートに .env を作成し、上記必須変数を設定
4. DuckDB データベース用ディレクトリを作成（必要なら）
5. 監査用 DB を初期化（必要な場合）

例:
```bash
mkdir -p data
# .env を準備する
python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"
```

---

## 使い方（代表的な呼び出し例）

DuckDB 接続の取得例:
```python
import duckdb
conn = duckdb.connect('data/kabusys.duckdb')
```

日次 ETL を実行（市場カレンダー取得 → 株価・財務取得 → 品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュースのセンチメントスコア生成（OpenAI API キーは env または api_key 引数で指定）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# env に OPENAI_API_KEY をセットしていれば api_key は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# あるいは既存接続にスキーマ適用:
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

データ品質チェックを個別に実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

ファクター計算の例:
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

注意:
- OpenAI 呼び出しは外部 API を叩きます。テスト時は内部の _call_openai_api をモックしてください（モジュール内コメントに記載あり）。
- ETL / API 周りはリトライ・レートリミットを考慮していますが、実運用時はポリシーに従ってキーやレート管理を行ってください。

---

## ディレクトリ構成（主要ファイル）

（本リポジトリの src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py            -- ニュース NLP（score_news）
    - regime_detector.py     -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - jquants_client.py      -- J-Quants API クライアント（fetch / save 実装）
    - etl.py                 -- ETLResult の再公開
    - stats.py               -- 統計ユーティリティ（zscore_normalize）
    - quality.py             -- データ品質チェック
    - news_collector.py      -- RSS ニュース収集 / 前処理
    - calendar_management.py -- マーケットカレンダー管理（is_trading_day 等）
    - audit.py               -- 監査ログ（スキーマ定義・初期化）
  - research/
    - __init__.py
    - factor_research.py     -- ファクター計算
    - feature_exploration.py -- IC / forward returns / summary
  - research/ ... (他)

---

## テスト・開発メモ

- OpenAI 呼び出しや外部 HTTP はユニットテストでモックする設計（モジュール内に差し替え可能な関数あり）。
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml で探索します。CI などで環境を固定する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の executemany には空リストを渡せない箇所があるため、内部で空チェックを行っています（互換性対応）。

---

もし README に追加したい具体的な内容（例: 実行するコマンド、docker-compose、CI 設定、API レート制御の詳細、運用手順など）があれば教えてください。必要に応じてサンプル .env.example や起動スクリプトのテンプレートも作成します。