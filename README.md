# KabuSys

日本株のデータプラットフォーム & 自動売買補助ライブラリ。  
J-Quants / kabu ステーションなどからデータを収集・保存し、AI（OpenAI）を用いたニュースセンチメントや市場レジーム判定、リサーチ用ファクター計算、品質チェック、監査ログ機能などを提供します。

主な対象用途
- 日次 ETL（株価・財務・カレンダー）の自動化
- ニュースの NLP（LLM）スコアリング（銘柄別 / マクロ）
- 市場レジーム判定（ETF MA と マクロセンチメントの合成）
- ファクター計算・特徴量解析（リサーチ向け）
- データ品質チェック
- 発注〜約定に関する監査ログ（DuckDB ベース）

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local を自動読み込み（無効化環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - 必須設定の取得と検証
- データ ETL（kabusys.data.pipeline）
  - J-Quants API からの差分取得・保存（raw_prices / raw_financials / market_calendar 等）
  - 日次 ETL 実行エントリ（run_daily_etl）
  - Rate limiting / リトライ / トークンリフレッシュに対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理・raw_news 保存補助
  - SSRF 保護、gzipサイズ制限、トラッキングパラメータ除去等の堅牢化
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマを提供
  - DuckDB への冪等な初期化ユーティリティ（init_audit_db / init_audit_schema）
- リサーチ・ファクター（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - forward returns / IC（Spearman） / ランク関数 / 統計サマリ
  - z-score 正規化ユーティリティ（kabusys.data.stats）
- AI モジュール（kabusys.ai）
  - ニュース NLP（score_news）：銘柄ごとに LLM でセンチメントを付与し ai_scores に書き込み
  - レジーム検出（score_regime）：ETF（1321）の MA200乖離 + マクロセンチメントを合成して market_regime に書き込み
  - OpenAI 呼び出しはリトライ・フォールバックを備え、失敗時は安全に継続

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法等を使用）
- DuckDB を利用するためローカル環境に Python バインディングが必要

1. リポジトリをチェックアウト
   - git clone ... などで取得

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください）
   - pip install -e .

4. 環境変数（.env）を設定
   - プロジェクトルートの .env または .env.local に以下を設定します（例）:

     .env.example:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

   - 注意:
     - 自動読み込みはデフォルトで有効。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
     - 必須環境変数が不足していると Settings プロパティで ValueError が発生します。

---

## 使い方（主要な関数・例）

以下はいくつかの主要なユースケースの簡単なサンプルです。実行は Python スクリプトや REPL から行ってください。

1) DuckDB 接続を使って日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース NLP（ai スコア）の実行
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か api_key 引数で指定
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成して初期化
```

5) リサーチ用ファクター計算の例
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意点
- AI 呼び出し（OpenAI）は API キーが必要です。環境変数 OPENAI_API_KEY を設定するか、関数の api_key 引数で渡してください。
- テスト時は内部の _call_openai_api を unittest.mock.patch で差し替え可能です（モジュール設計上、テストフレンドリーに実装されています）。
- ETL / データ保存は DuckDB のスキーマに依存します。事前にスキーマ準備（migration／DDL）を行ってください。

---

## 環境変数一覧（主要）

必須
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector 使用時）

任意（デフォルトあり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ定義と公開サブパッケージ
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — 銘柄別ニュース NLP（score_news）
    - regime_detector.py — マクロ + ETF MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — 日次 ETL パイプライン & 個別 ETL ジョブ
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集・前処理ロジック（SSRF 対策等含む）
    - quality.py — データ品質チェック（欠損 / スパイク / 重複 / 日付整合性）
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - stats.py — z-score 等の統計ユーティリティ
    - audit.py — 監査ログテーブルの DDL / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等
    - feature_exploration.py — forward returns / IC / rank / summary
  - monitoring/ (存在を想定：監視系モジュールや DB 操作用モジュールを想定)

（上記はコードベースの主要モジュールを抜粋した構成です）

---

## 実装上の注意・設計方針（抜粋）

- Look-ahead bias を避けるため、内部処理は target_date に対して「対象日未満／以前のデータのみ」を利用するよう設計されています（datetime.today() を直接参照しない）。
- OpenAI 呼び出しは JSON Mode を利用し、厳密な JSON レスポンスを期待する実装です。API の失敗はフォールバック（0.0 等）して処理継続する箇所が多く設けられています。
- news_collector は SSRF 対策、受信サイズ制限、トラッキング除去、XML 解析の安全化（defusedxml）などを行っています。
- J-Quants クライアントはレートリミット（120req/min）とリトライ、401 時のトークンリフレッシュを備えています。
- DuckDB への保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用しています。

---

## テスト／開発ヒント

- OpenAI への実際の呼び出しを避けるには、kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替えてください。
- ETL の単体テストは DuckDB の in-memory 接続（":memory:"）で行うと便利です（init_audit_db なども ":memory:" をサポート）。
- .env の自動読み込みを無効にしたいテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

もし README に追加してほしい内容（例：フル API リファレンス、例の .env.example ファイル、CI / デプロイ手順、スキーマ定義の SQL ダンプなど）があれば教えてください。必要に応じて追記・整形します。