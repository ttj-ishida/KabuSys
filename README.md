# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、ファクター研究、監査ログ（発注→約定トレーサビリティ）、市場レジーム判定など、トレーディングシステムの基盤機能を提供します。

## 主な特徴
- データ取得（J-Quants）と DuckDB への冪等保存（差分取得・バックフィル対応）
- ニュース収集（RSS）と OpenAI を用いた銘柄別センチメントスコアリング（JSON mode）
- 市場レジーム判定（ETF 1321 のMA乖離とマクロニュースの LLM センチメントを合成）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 環境変数／.env 自動読み込み（プロジェクトルート基準。無効化フラグあり）

---

## 機能一覧（モジュール概観）
- kabusys.config
  - 環境変数の管理・自動ロード（`.env`, `.env.local`）
  - 必須設定取得ヘルパー（settings オブジェクト）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存・トークン管理・レート制御）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得と前処理、raw_news への保存ロジック
  - quality: データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - calendar_management: 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: 共通統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュースから銘柄別センチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースで市場レジーム判定を行い market_regime に書き込む
- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## セットアップ手順

前提:
- Python 3.10+（Type hints と新しい構文を利用）
- DuckDB を利用（ローカルファイル / :memory:）

1. リポジトリをクローンして開発パッケージとしてインストール（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 依存パッケージ（プロジェクトに応じて追加インストール）
   - 最低限必要なパッケージ（例）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実行に応じて他パッケージ（urllib は標準ライブラリ）を追加してください。

3. 環境変数を設定
   - プロジェクトルート（`.git` または `pyproject.toml` のあるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

   主要な環境変数例（必須）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL / jquants_client で使用）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注関連）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite ファイルパス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: 環境 (development | paper_trading | live)
   - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

   サンプル `.env`（一部）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本的な例）

以下は Python REPL／スクリプトでの利用例です。DuckDB への接続は `duckdb.connect()` を使用します。

- 日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース（AI）スコアリングを実行（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数か引数で渡す
print(f"scored {count} symbols")
```

- 市場レジーム判定を実行（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数か引数で渡す
```

- 監査ログ DB を初期化して接続を取得
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB の接続オブジェクト
```

- 環境設定の読み取り
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env)          # development | paper_trading | live
```

注意点：
- AI 関連関数は OPENAI_API_KEY を参照します。引数で api_key を渡すことも可能です。
- ETL / データ取得は J-Quants の認証トークンを内部でリフレッシュします（JQUANTS_REFRESH_TOKEN が必要）。
- news_collector の RSS 取得は SSRF・圧縮バッファ・XML セキュリティ対策を備えています。

---

## よく使う API（主要関数）
- run_daily_etl(conn, target_date, id_token=None, ...)
- run_prices_etl(conn, target_date, ...)
- run_financials_etl(conn, target_date, ...)
- run_calendar_etl(conn, target_date, ...)
- score_news(conn, target_date, api_key=None)
- score_regime(conn, target_date, api_key=None)
- init_audit_db(path) / init_audit_schema(conn)
- jquants_client.fetch_daily_quotes / save_daily_quotes 等
- data.quality.run_all_checks(conn, target_date)

---

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主なファイルとディレクトリの概観です（src/kabusys 以下）。

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
  - stats.py
  - calendar_management.py
  - audit.py
  - audit 用 db 初期化ユーティリティなど
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記は主要モジュールを抜粋したもので、実際のツリーにはさらに細かい関数や補助モジュールが含まれます。）

---

## 運用上の注意 / 設計方針の要約
- Look-ahead bias を避ける設計
  - 各モジュールは target_date を外部から受け取り、datetime.today()/date.today() を直接参照しない設計が基本です。
- 冪等性
  - DuckDB への保存は ON CONFLICT（更新）や個別DELETE→INSERT のアプローチで冪等性を確保します。
- フェイルセーフ
  - 外部 API（OpenAI、J-Quants）失敗時も処理を継続する設計（失敗時のフォールバック、スキップ、ログ出力）。
- セキュリティ
  - news_collector は SSRF 対策、XML パーサの安全化、受信サイズ上限などを実装。
- レート制御とリトライ
  - J-Quants クライアントはレート制御と指数バックオフ、401 の自動リフレッシュを実装。

---

## 問題報告 / 貢献
バグや改善要望があれば Issue を立ててください。設計に関する議論や実装提案は PR で送っていただければレビューします。

---

必要であれば README に「実行例のより詳しい手順」や「開発用の Docker / CI 設定」「requirements.txt の推奨内容」などの追記を作成します。どの情報を優先して追加しますか？