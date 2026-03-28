# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J‑Quants からのデータ ETL、ニュース収集・NLP、研究用ファクター計算、監査ログ（トレース）等を含むコンポーネント群を提供します。

主な設計方針:
- ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を直接参照しない等）
- ETL / 保存処理は冪等（idempotent）に実装（ON CONFLICT / DELETE→INSERT等）
- 外部 API 呼び出しはリトライ／バックオフやレート制御を実装
- セキュリティ配慮（RSS の SSRF 防止、defusedxml 使用等）

---

## 機能一覧

- データ取得 / ETL
  - J‑Quants API クライアント（prices, financials, market calendar）: rate limit とリトライを備えた取得 & DuckDB への保存（kabusys.data.jquants_client）
  - 日次 ETL パイプライン（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェックの一括処理（kabusys.data.pipeline）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day 等）

- ニュース収集・NLP
  - RSS 収集（SSRF 回避、前処理、raw_news 保存）: kabusys.data.news_collector
  - ニュースセンチメント（銘柄毎）: OpenAI を用いたバッチ評価（kabusys.ai.news_nlp）
  - マクロセンチメント + ETF MA200 を合成した市場レジーム判定（kabusys.ai.regime_detector）

- 研究・因子
  - Momentum / Volatility / Value 等のファクター計算（kabusys.research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等（kabusys.research.feature_exploration）
  - Zスコア正規化ユーティリティ（kabusys.data.stats）

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合のチェック（kabusys.data.quality）

- 監査ログ（トレーサビリティ）
  - シグナル → 発注要求 → 約定までの監査テーブルと初期化ユーティリティ（kabusys.data.audit）

- 設定管理
  - .env / 環境変数読み込み（自動ロード機能あり）と Settings オブジェクト（kabusys.config）

---

## 要件（主要依存パッケージ）

- Python 3.10+
- duckdb
- openai（OpenAI の v1 SDK を想定）
- defusedxml
- （標準ライブラリ: urllib, json, datetime など）

インストールはプロジェクトごとの setup に応じて行ってください（例: poetry / pip）。開発環境では以下を最低限インストールします:

pip install duckdb openai defusedxml

---

## 環境変数 / .env

kabusys.config.Settings が参照する主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime のデフォルト）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（例: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env 読み込み:
- パッケージ内の config.py はプロジェクトルート（.git または pyproject.toml）を探索し、.env → .env.local の順で読み込みます。
- 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン、プロジェクトルートへ移動
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 必須パッケージをインストール
   - pip install duckdb openai defusedxml
   - その他プロジェクトで管理している場合は pyproject.toml / requirements.txt に従う
4. .env を作成して必要な環境変数を設定（上記参照）
   - .env.local はローカル上書き用
5. DuckDB ファイルの親ディレクトリを作成（自動で作られる処理もあるが手動で用意しておくと安心）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は Python スクリプトからの呼び出し例です。必要に応じて環境変数で OpenAI / J‑Quants の鍵を設定してください。

- DuckDB 接続の作成:

from datetime import date
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する:

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメントをスコアリング（OpenAI API Key を env または引数で指定）:

from kabusys.ai.news_nlp import score_news
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None で env の OPENAI_API_KEY を使用
print(f"scored {count} codes")

- 市場レジーム判定を実行:

from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査 DB を初期化（監査専用 DB を作る）:

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可

- RSS フィードを取得（news_collector を直接使う）:

from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])

注意点:
- OpenAI を呼ぶ関数（score_news, score_regime）は api_key を引数で上書きできます。None の場合は環境変数 OPENAI_API_KEY を参照します。キーが未設定だと ValueError を送出します。
- ETL / 保存処理はトランザクション管理を行いますが、各関数は例外を投げる場合があります。ログを確認してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール一覧（本 README に含まれるファイルを抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（銘柄別スコア）
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J‑Quants API client + DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl など）
    - etl.py                         — ETL 公開インターフェース（ETLResult エクスポート）
    - news_collector.py              — RSS 収集（SSRF 対策、前処理）
    - calendar_management.py         — マーケットカレンダー管理
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility 等
    - feature_exploration.py         — 将来リターン / IC / summary / rank

各モジュールは README の「機能一覧」にある責務ごとに分割されています。詳細は各モジュールの docstring を参照してください。

---

## 実装上の重要な注意点 / 設計意図

- Look-ahead バイアス防止:
  - 日次処理は target_date を明示して呼ぶ設計で、内部で現在時刻を参照しない関数が多くあります（バックテストで利用可能）。
- 冪等性:
  - ETL の保存は ON CONFLICT / DELETE→INSERT 等により再実行可能です。
- 外部 API の堅牢性:
  - J‑Quants クライアントはレート制御（120 req/min）、リトライ、401 のトークンリフレッシュを実装。
  - OpenAI 呼び出しはリトライ戦略を持ち、失敗時は安全側（0.0 など）でフォールバックして処理を継続。
- セキュリティ:
  - RSS 収集は URL 正規化、トラッキングパラメータ除去、SSRF 防止（プライベート IP 拒否）を行っています。
  - defusedxml を用いて XML 関連の攻撃を軽減しています。

---

## ロギング / デバッグ

- 環境変数 LOG_LEVEL でレベルを設定できます（DEBUG/INFO/…）。
- 各モジュールは標準的な logging を利用しています。必要に応じてハンドラやフォーマッタをアプリ側で設定してください。

---

## サポート / 貢献

この README はコードベースの公的ドキュメントの概要です。各モジュールの docstring に詳細な設計メモが記載されています。バグ報告や機能提案はリポジトリの Issue にて行ってください。

---

以上。必要であれば「実行例の詳細」「.env.example ファイル」「Docker / CI の設定例」などを追加で作成します。どの部分を優先して補足しますか？