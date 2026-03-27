# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注・約定トレーサビリティ）などを提供します。

主な設計方針:
- ルックアヘッドバイアス回避（内部で datetime.today()/date.today() を参照しない箇所が多くあります）
- DuckDB を用いたローカルデータ格納
- 外部 API（J-Quants / OpenAI / kabuステーション）との堅牢な通信・リトライ・レート制御
- テスト容易性（API 呼び出し箇所の差し替えが可能）

---

## 機能一覧

- 環境設定・自動 .env ロード（settings）
- J-Quants クライアント
  - 株価日足（OHLCV）取得 & DuckDB へ保存（差分 / ページネーション対応）
  - 財務データ取得 & 保存
  - 市場カレンダー取得 & 保存
- ETL パイプライン（run_daily_etl を中心に市場カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS）と前処理（SSRF 対策、トラッキング除去、サイズ制限）
- ニュース NLP（OpenAI）による銘柄別センチメント算出（ai.score_news）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースセンチメントの合成、ai.score_regime）
- 研究用ユーティリティ（ファクター算出・将来リターン・IC 計算・Z スコア正規化）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## 要件

- Python 3.10+
- 推奨パッケージ（プロジェクトの requirements.txt がない場合、最低限次をインストールしてください）:
  - duckdb
  - openai
  - defusedxml

例:
```bash
python -m pip install "duckdb" "openai" "defusedxml"
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境を作成して依存をインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e .           # パッケージが setup されている場合
   pip install duckdb openai defusedxml
   ```
3. 環境変数を用意（.env / .env.local をプロジェクトルートに作成すると自動ロードされます）
   - 必須（実行する機能に応じて必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — 同上
     - KABU_API_PASSWORD — kabuステーション API を使う場合
     - OPENAI_API_KEY — OpenAI を使うモジュール（news_nlp, regime_detector）で必要
   - 任意 / デフォルトあり:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...
     - KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
   - 自動ロードを無効化する:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます（テスト時など）。

.env の例（.env.example を参照してください）:
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
```

---

## 使い方（代表例）

以下は最小限のコードスニペット例です。実行前に環境変数を設定してください。

- DuckDB 接続を作って日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP で銘柄ごとの ai_scores を計算（score_news）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print(f"scored: {n_written} codes")
```

- 市場レジームを判定して market_regime に書き込む:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DB を作る）:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions が作成されます
```

- ニュース RSS をフェッチする（news_collector.fetch_rss の単体利用例）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
print(len(articles))
```

注:
- OpenAI を使う関数は api_key 引数を受け取ります。None を渡すと環境変数 OPENAI_API_KEY を参照します。
- J-Quants API 呼び出しは settings.jquants_refresh_token を必要とします（環境変数で設定してください）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須: J-Quants を使う場合）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector などで必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う場合）
- KABU_API_BASE_URL: kabuステーション の base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を行う場合に使用
- DUCKDB_PATH: DuckDB のデフォルトパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

設定は .env / .env.local をプロジェクトルートに置くことで自動読み込みされます（プロジェクトルートは .git または pyproject.toml を基準に検出されます）。テスト時は自動ロードを無効にしてください。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースセンチメント算出（OpenAI）
    - regime_detector.py  -- 市場レジーム判定（ETF 1321 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント（fetch / save）
    - pipeline.py         -- ETL 実行（run_daily_etl など）
    - etl.py              -- ETLResult の再エクスポート
    - news_collector.py   -- RSS 収集・前処理
    - quality.py          -- データ品質チェック
    - calendar_management.py -- マーケットカレンダー管理（営業日判定等）
    - stats.py            -- zscore_normalize 等の統計ユーティリティ
    - audit.py            -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py  -- Momentum / Value / Volatility / Liquidity の算出
    - feature_exploration.py -- 将来リターン, IC, rank, factor_summary 等

各モジュールは README のコメントや docstring に設計方針・制約が記載されています。実運用時は各関数の docstring を参照してください。

---

## 運用上の注意

- DuckDB のバージョン依存に注意（一部 executemany の挙動や型バインドに制約があります）。
- OpenAI 呼び出しはレート・費用に注意。news_nlp と regime_detector はリトライ・フォールバックを備えていますが、API キーとコスト管理は運用側で行ってください。
- J-Quants API はレート制限（120 req/min）を守るため内部でスロットリングがあります。大量取得時のスケジューリングにご注意ください。
- ニュース収集は外部 URL を扱うため SSRF 対策を施していますが、運用環境のネットワークポリシーも確認してください。
- 監査ログは削除しない設計のため、ディスクサイズ・バックアップ方針を検討してください。

---

## 開発 / テスト

- テストを書く際は環境変数の自動ロード (KABUSYS_DISABLE_AUTO_ENV_LOAD) を無効化すると良いです。
- 外部 API 呼び出しはモック可能な設計になっています（関数をパッチして差し替えられます）。
- DuckDB のインメモリ接続（":memory:"）を使用して単体テストを行うと簡単です。

---

以上がプロジェクトの概要と基本的な使い方です。詳細は各モジュールの docstring を参照してください。必要であれば README を英語版や運用手順（cron / Airflow など）の例に拡張します。