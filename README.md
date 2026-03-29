# KabuSys

日本株向けの自動売買 / データパイプラインライブラリです。  
市場データのETL、ニュースの収集・NLPによるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）、および市場レジーム判定などを一貫して提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの差分 ETL（株価日足、財務データ、JPX カレンダー）
- ニュース収集（RSS）と LLM を使った銘柄単位のニュースセンチメント算出
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック、マーケットカレンダー管理
- 監査ログ / トレーサビリティ（signal → order_request → execution の保存）
- 冪等性・リトライ・レート制御等の実運用向け実装

主要なデータ保管は DuckDB を想定しており、ETL 処理は冪等（ON CONFLICT）で設計されています。OpenAI（gpt-4o-mini）を使用した NLP（JSON Mode）を組み込んでいます。

---

## 主な機能一覧

- data/
  - ETL パイプライン: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch_*, save_*（差分取得・保存、トークン自動リフレッシュ、レート制御）
  - ニュース収集: RSS フィード収集・前処理・raw_news への保存（SSRF 対策、トラッキング除去）
  - カレンダー管理: is_trading_day, next_trading_day, get_trading_days, calendar_update_job
  - データ品質チェック: missing_data, duplicates, spike, date_consistency, run_all_checks
  - 監査ログ初期化: init_audit_schema, init_audit_db

- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに集約し LLM に投げて ai_scores を書き込み
  - regime_detector.score_regime: ETF(1321)のMA200乖離とマクロニュースセンチメントの合成による日次レジーム判定

- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats.zscore_normalize（共通統計ユーティリティ）

- 設定管理:
  - kabusys.config.settings: .env/.env.local の自動読み込み（プロジェクトルート検出）、必須環境変数チェック、環境切替（development / paper_trading / live）

---

## セットアップ手順

前提:
- Python 3.9+（typing|annotations の利用を鑑みて想定）
- DuckDB（Python パッケージで使用）
- OpenAI API キー（ニュース/NLP 系機能を使う場合）
- J-Quants のリフレッシュトークン（ETL を使う場合）

1. リポジトリを取得
   - git clone ...（省略）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（macOS/Linux）
   - .venv\Scripts\activate（Windows）

3. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を作成すると自動読み込みされます（.env.local は上書き）。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   代表的な .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易例）

以下はライブラリを直接利用する際の簡単な使用例です。実行は Python スクリプト内で行います。

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を利用するのが推奨
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（OpenAI API キー必須）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- 市場レジーム判定（1321 を用いた MA200 とマクロニュース合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

conn = init_audit_db(Path("data/audit.duckdb"))
# conn は初期化済みの DuckDB 接続
```

- J-Quants トークン取得（デバッグ）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

注記:
- ai モジュール（score_news, score_regime）は OpenAI API を呼び出します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- settings（kabusys.config）では KABUSYS_ENV, LOG_LEVEL, 各種パスや API トークンなどを管理します。必須キーが未設定の場合は ValueError が投げられます。

---

## 設定（settings / 環境変数）

主要な環境変数（必須・デフォルト含む）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news/score_regime）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（任意）

.env のパースは .env/.env.local をサポートし、.env.local は上書きされます。自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）を検出して行います。

---

## ディレクトリ構成

（主要ファイル・モジュールの要約）

- src/kabusys/
  - __init__.py — パッケージ定義、version
  - config.py — 環境変数・設定管理（.env 自動読み込み・Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄ごとに集約して LLM でスコア化（score_news）
    - regime_detector.py — ETF(1321)のMA200乖離 + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー管理 / 営業日判定 / calendar_update_job
    - etl.py — ETL 結果型の再エクスポート
    - pipeline.py — 日次 ETL パイプラインおよび個別 ETL ジョブ
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py — 監査ログテーブル定義と初期化（init_audit_schema / init_audit_db）
    - jquants_client.py — J-Quants API クライアント（fetch/save/get_id_token）
    - news_collector.py — RSS 収集・正規化・raw_news 保存（SSRF/サイズ制限対策）
  - research/
    - __init__.py — 研究用ユーティリティのエクスポート
    - factor_research.py — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — calc_forward_returns / calc_ic / factor_summary / rank

各モジュールはドキュメンテーション文字列とログ出力を備え、実運用での堅牢性（リトライ、タイムアウト、パラメータバインド、冪等性）を重視して実装されています。

---

## 運用上の注意

- OpenAI 呼び出しはコストとレート制限があるため、バッチサイズや API キーの扱いに注意してください。score_news はバッチ（最大 20 銘柄）単位で送信します。
- J-Quants の API レート制限（120 req/min）に合わせた RateLimiter を実装しています。頻繁なループ呼び出しは避けてください。
- ETL は冪等設計ですが、運用上はバックアップ・監視（Slack 通知等）を組み合わせてください。
- settings.is_live の判定等を用いて発注や実際のブローカー連携を制御してください（本リポジトリは発注実行のための high-level ロジックを含む可能性がありますが、実行環境の安全性を最優先にしてください）。

---

## テスト / 開発

- 単体テストを追加する際は、外部 API 呼び出し（OpenAI, J-Quants, HTTP）をモックしてください。本コードは内部で _call_openai_api や _urlopen など差し替え可能なヘルパーを持ち、単体テストでの差し替えを想定しています。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化でき、テストの環境分離に便利です。

---

必要であれば、README に以下を追加できます:
- requirements.txt / pyproject.toml の推奨内容
- 実運用向けのデプロイ手順（システムd / cron / Airflow）
- より詳細な API リファレンス（各関数の引数と返り値の例）
- サンプル .env.example

要望があれば追記します。