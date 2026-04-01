# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ。  
ETL、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム・データプラットフォームの基盤ライブラリです。  
主に以下を実現します。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得・保存（ETL）
- RSS ニュース収集と前処理
- OpenAI を用いたニュースのセンチメントスコアリング（銘柄別／マクロ判定）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 設定管理（.env / 環境変数の自動読み込み）

設計上の特徴：
- Look-ahead bias を避けるため date 引数ベースで処理（date.today() に依存しない）
- DuckDB をデータストアとして活用
- OpenAI（gpt-4o-mini）を JSON Mode で利用する設計（リトライやフォールバックを備える）
- 冪等性を重視（ON CONFLICT 等）

---

## 機能一覧（主要モジュール）

- kabusys.config
  - .env / 環境変数の読み込み・管理、必須設定の検証
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得 / 保存 / レート制御 / リトライ）
  - pipeline: ETL パイプライン（run_daily_etl 等）
  - calendar_management: 市場カレンダー管理・営業日判定
  - news_collector: RSS 収集と正規化・保存ヘルパー
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブル初期化 / DB 作成ユーティリティ
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 とマクロセンチメントを合成して market_regime に保存
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提：
- Python 3.10+（型注釈に | が使われているため 3.10 以上を推奨）
- duckdb, openai, defusedxml 等が必要

1. リポジトリをクローン / パッケージをプロジェクトに配置

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール（requirements.txt がない場合は主要ライブラリを個別に）
   - pip install duckdb openai defusedxml

   開発インストール（package がある場合）:
   - pip install -e .

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（少なくとも下記を設定してください）：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（必要時）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot Token
- SLACK_CHANNEL_ID: Slack 通知先のチャンネル ID
- OPENAI_API_KEY: OpenAI API を利用する機能（ニュース NLP / レジーム判定 等）を使う場合に必要

任意（デフォルト値あり）：
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/...)

例 .env（テンプレート）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
KABU_API_PASSWORD=your_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API と簡単なサンプル）

設定オブジェクト
```python
from kabusys.config import settings
# settings は .env / 環境変数から値を読み込む
print(settings.duckdb_path)
```

DuckDB 接続の作成例
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

ETL（日次パイプライン）実行例
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

ニュース NLP（銘柄別スコアリング）
```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print("書き込み銘柄数:", n_written)
```

市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルへ書き込む
```

監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブル作成 (UTC timezone 設定) を行い接続を返す
```

データ品質チェック（単体呼び出し）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点：
- OpenAI 呼び出しはネットワークや API レートの影響を受けます。score_news / score_regime はリトライやフォールバック（失敗時スコア 0.0）を備えていますが、API キーは必須です。
- ETL / データ保存関数は DuckDB のスキーマ前提（raw_prices, raw_financials 等）に依存します。初期スキーマのセットアップ方法（schema init 等）は別途用意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      -- 環境変数 / .env 読み込みと settings
- ai/
  - __init__.py
  - news_nlp.py                   -- 銘柄別ニュースセンチメント/score_news
  - regime_detector.py            -- 市場レジーム判定/score_regime
- data/
  - __init__.py
  - jquants_client.py             -- J-Quants API クライアント（fetch/save）
  - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
  - etl.py                        -- ETL 公開インターフェース（ETLResult 再エクスポート）
  - calendar_management.py        -- 市場カレンダー / 営業日判定
  - news_collector.py             -- RSS 収集・前処理
  - quality.py                    -- データ品質チェック
  - stats.py                      -- 統計ユーティリティ（zscore_normalize 等）
  - audit.py                      -- 監査ログ用 DDL と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py            -- calc_momentum, calc_volatility, calc_value
  - feature_exploration.py        -- calc_forward_returns, calc_ic, factor_summary, rank

ドキュメント / 設計意図は各モジュールの docstring に記載されています（ETL の差分戦略、API リトライ方針、Look-ahead 回避設計等）。

---

## 注意事項 / 運用上のヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のスキーマ（テーブル定義）は本リポジトリに含まれない可能性があります。ETL を実行する前に必要テーブルを作成してください（audit.init_audit_db は監査テーブルを初期化します）。
- OpenAI API 呼び出しにはコストとレート制限があります。大量のバッチ処理を行う場合は運用上のポリシーを検討してください。
- 監査ログは削除しない前提で設計されています。ストレージ管理（圧縮、バックアップ）を検討してください。

---

もし README に追加したいサンプルコマンドや、テーブルスキーマ / 初期化スクリプトのテンプレートが必要であれば教えてください。