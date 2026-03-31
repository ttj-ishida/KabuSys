# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼研究・自動売買支援ライブラリです。  
J-Quants API からのデータ取得、DuckDB を用いた ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクタ計算、監査ログ（トレーサビリティ）などを提供します。

主な設計方針は「Look-ahead bias を避ける」「DuckDB による局所データ管理」「API 呼び出しの冪等性と耐障害性」です。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得・保存（pagination / rate limit / retry 対応）
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質管理
  - 欠損検出、スパイク検出、重複チェック、日付整合性チェック（quality モジュール）
- ニュース収集・前処理
  - RSS フィード収集、URL 正規化、SSRF 対策、Gzip / サイズチェック（news_collector）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメントスコア生成（gpt-4o-mini, JSON モード、バッチ/リトライ対応）
  - マクロニュースを使った市場センチメント（regime_detector）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research パッケージ）
  - 将来リターンや IC（Information Coefficient）計算、Zスコア正規化（data.stats, research.feature_exploration）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（data.audit）
- 設定管理
  - .env / .env.local / 環境変数に対応する自動ロード（kabusys.config）

---

## 必要な環境・依存ライブラリ

主な依存（代表例）
- Python 3.10+
- duckdb
- openai
- defusedxml

※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。ここでは最低限必要なパッケージを挙げています。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発インストール（パッケージ化済みの場合）
pip install -e .
```

---

## 環境変数（主なもの）

kabusys は環境変数または .env ファイルから設定を読み込みます（プロジェクトルートに .git または pyproject.toml がある場合に自動読み込み）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（発注等）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 実行時に必要）

オプション／デフォルト:
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite(Monitoring) パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）

自動 .env ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作る
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # またはプロジェクトのセットアップ方法に従う (pip install -e .)
   ```

3. 必要な環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定してください。
   - 例は上記の .env セクション参照。

4. DuckDB の初期スキーマ（監査ログ等）を作成する（任意）
   - Python REPL やスクリプトで init を実行（下記参照）。

---

## 使い方（代表的な API）

下記は簡単な Python からの呼び出し例です。事前に必要な環境変数（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY など）を設定してください。

- DuckDB 接続の作成:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL の実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定するか、None（今日）を指定
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュース NLP スコアリング（news_nlp.score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されていること
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", n_written)
```

- 市場レジーム判定（regime_detector.score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（独立した監査用 DB を作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を用いて signal/order/execution を記録できます
```

- 設定参照（kabusys.config）
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live, settings.log_level)
```

注意点:
- AI 関連関数（score_news, score_regime）は OPENAI_API_KEY を参照します。引数 api_key で明示的に渡すことも可能です。
- ETL / 保存関数は冪等性を保つ設計ですが、初回実行時は DB スキーマ（raw_prices, raw_financials, market_calendar 等）を用意する必要があります（通常は ETL スクリプトが自動で作成するか別のスキーマ初期化処理を用意してください）。
- テスト時は環境変数の自動読み込みを無効化できます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

---

## よく使う関数一覧（モジュール別）

- kabusys.config
  - settings — 環境設定の取得（プロパティベース）

- kabusys.data
  - pipeline.run_daily_etl — 日次 ETL 実行
  - pipeline.run_prices_etl / run_financials_etl / run_calendar_etl — 個別 ETL
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar — API 呼び出し
  - jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar — DuckDB 保存
  - news_collector.fetch_rss — RSS 取得（記事前処理含む）
  - audit.init_audit_db / init_audit_schema — 監査用 DB 初期化
  - quality.run_all_checks — 品質チェックの一括実行
  - calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days — 営業日管理

- kabusys.ai
  - news_nlp.score_news — 銘柄ニュースのセンチメントスコア算出・保存
  - regime_detector.score_regime — 市場レジーム判定（MA + マクロセンチメント合成）

- kabusys.research
  - calc_momentum / calc_volatility / calc_value — ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank — 研究用統計関数
  - data.stats.zscore_normalize — Zスコア正規化

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内 `src/kabusys` を基準）

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
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py (ETLResult re-export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター計算・探索用ユーティリティ群）

各モジュールは README 内の「よく使う関数一覧」を参照してください。ソース内ドキュメント（docstring）に各関数の挙動・前提が詳述されています。

---

## 注意事項 / ベストプラクティス

- Look-ahead bias を防ぐ設計が随所に施されています。バックテストや研究で利用する場合は、対象期間に対して事前に取り込んだデータだけを使用するなど注意してください（fetch 関数の注釈参照）。
- OpenAI の呼び出しはコストとレート制限の対象になります。バッチ・リトライロジックはありますが、実運用ではコスト管理を行ってください。
- ETL の初回実行、スキーマ初期化、監査テーブルの初期化は適切な権限とバックアップのもとで実行してください。
- テスト時は環境を汚さないように KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、必要な値はテスト側で注入してください。

---

README はここまでです。具体的な導入（スキーマ初期化スクリプト / requirements.txt / CI 設定等）を追加したい場合は、使用している環境や配布方法（pip / poetry / dev Docker など）を教えてください。必要に応じて実行スクリプトやサンプル SQL（スキーマ定義）も作成します。