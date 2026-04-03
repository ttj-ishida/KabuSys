# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL、ニュース収集・NLP スコアリング、リサーチ用ファクター計算、監査ログ、J-Quants / kabu API クライアントなどを含むモジュール群です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）設定
- 使い方（簡単な利用例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株のデータプラットフォームおよび自動売買基盤向けユーティリティを集めた Python パッケージです。主に以下を提供します。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（DuckDB に保存）
- RSS ベースのニュース収集およびニュースの前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄・マクロ）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- 研究（ファクター計算、将来リターン、IC、統計サマリー）
- 監査ログテーブル（シグナルから約定までのトレーサビリティ）初期化ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上、バックテストでのルックアヘッドバイアスを避けるよう注意して実装されています（target_date を明示する設計など）。

---

## 主な機能（モジュール別）

- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 設定オブジェクト `settings`（J-Quants, kabu, DB パス, 監視閾値など）

- kabusys.data
  - jquants_client: J-Quants API (差分取得、保存、認証・レート制御)
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector: RSS フィード取得・正規化・raw_news への保存
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定
  - audit: 監査ログテーブルの初期化 / 専用 DB 作成ユーティリティ
  - stats: zscore_normalize 等の汎用統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄ごとのニュースセンチメント（ai_scores）を生成
  - regime_detector.score_regime(conn, target_date, api_key=None): 市場レジーム判定（market_regime に書込）

- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

1. Python 環境（推奨: 3.9+）を用意します。

2. リポジトリをクローンし、パッケージをインストール（開発時）:
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m pip install -e .
   ```

3. 必要な依存パッケージ（例）
   - duckdb
   - openai (openai SDK)
   - defusedxml
   - その他標準ライブラリのみで多くが実装されていますが、実行には上記ライブラリが必要です。
   インストールは通常 setup.cfg / pyproject.toml に記載される想定ですが、ない場合は手動で:
   ```
   python -m pip install duckdb openai defusedxml
   ```

4. .env を準備します（下記参照）。環境変数は OS 環境 > .env.local > .env の優先順位で読み込まれます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（.env）と設定例

自動的に .env（および .env.local）をプロジェクトルートから読み込みます（.git または pyproject.toml をルートの手掛かりに探索）。

主に使用される環境変数:
- JQUANTS_REFRESH_TOKEN (必須)  
  - J-Quants のリフレッシュトークン。`jquants_client.get_id_token()` で ID トークン取得に使用。
- KABU_API_PASSWORD (必須)  
  - kabu ステーション API のパスワード（注文実行等で利用）。
- OPENAI_API_KEY (必要な場合)  
  - OpenAI API 呼び出しに使用。`ai.news_nlp` / `ai.regime_detector` で必要。
- KABU_API_BASE_URL (任意)  
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)  
  - 通知用。
- DUCKDB_PATH (任意)  
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)  
  - 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視・運用に関する設定
- KABUSYS_ENV (development | paper_trading | live)  
  - 実行環境。`settings.env` で検証されます。
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

.env ファイルパーサは次の点に対応:
- export KEY=val 形式に対応
- シングル/ダブルクォート、エスケープ、コメントの扱いに対応

例 (.env):
```
JQUANTS_REFRESH_TOKEN="xxxxx"
KABU_API_PASSWORD="your_password"
OPENAI_API_KEY="sk-..."
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な利用例）

以下は Python REPL / スクリプトからの利用例です。DuckDB 接続は本パッケージ内関数に直接渡します（ルックアヘッドバイアス対策のため target_date を明示することが推奨されます）。

- DuckDB 接続例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア付け（ai_scores への書き込み）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OpenAI キーを環境変数に設定しているか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（market_regime へ書き込み）:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算 / リサーチ:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

moms = calc_momentum(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))

fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
ic = calc_ic(moms, fwd, "mom_1m", "fwd_1d")
```

- 監査ログ DB 初期化（監査専用 DB を作成）:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は自動で呼ばれます
```

- ニュース収集（RSS）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
# raw_news に保存するロジックは別にあり、通常は収集→保存のワークフローを実行します
```

注意: OpenAI 呼び出しは外部 API を使用するため、API キーや利用料金に留意してください。API エラー時はフェイルセーフでゼロスコアにフォールバックする処理が多く組み込まれています。

---

## 運用上のポイント

- ルックアヘッドバイアス防止
  - 多くの関数は datetime.today() を参照せず、必ず target_date を指定して動作するよう作られています。バックテストや日次バッチでは target_date を明示してください。

- .env 自動読み込み
  - プロジェクトルートを .git または pyproject.toml で検出して .env/.env.local を自動読み込みします。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

- J-Quants API のレート制御・リトライ
  - jquants_client はレート制限（120 req/min）に合わせた固定間隔スロットリングと指数バックオフを組み合わせています。401 の場合はトークン自動リフレッシュを試みます。

- ニュース収集のセキュリティ
  - RSS 取得は SSRF を意識したリダイレクト検査、プライベート IP ブロック、最大受信バイト数制限、XML パースの安全化（defusedxml）などが組み込まれています。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 配下）:

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
  - quality.py
  - calendar_management.py
  - stats.py
  - audit.py
  - audit に関連する DDL / init 関数
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

README に含まれていない細かいユーティリティや実装は各モジュールの docstring を参照してください。各関数には入力（DuckDB 接続など）・出力・副作用（DB 書き込み）についての説明が付けられています。

---

もし README に追記したい内容（運用手順の詳細、例環境 .env.example、CI / デプロイ手順、テスト戦略など）があれば教えてください。必要に応じてサンプル .env.example を作成します。