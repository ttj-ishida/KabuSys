# KabuSys

日本株向けの自動売買 / データプラットフォーム基盤ライブラリ。  
J-Quants からのデータ収集（株価・財務・市場カレンダー）、ニュース収集・LLM によるニュースセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

主な設計方針：
- Look-ahead バイアス対策（内部で datetime.today() を不用意に参照しない設計）
- DuckDB を中核にしたローカルデータレイヤ
- 冪等性（ON CONFLICT / idempotent な保存）
- API 呼び出しに対する堅牢なリトライ・レート制御

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得（ページネーション対応）
  - ETL パイプライン（run_daily_etl）でカレンダー→株価→財務→品質チェックを順次実行
- データ品質チェック
  - 欠損、主キー重複、株価スパイク、日付不整合チェック（QualityIssue を返す）
- ニュース収集
  - RSS フィード取得（SSRF 対策・gzip/サイズ制限・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメントを LLM でスコアリング（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ → score_regime）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン、IC（スピアマン）、統計サマリ、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義・初期化関数
  - audit DB 初期化ユーティリティ（init_audit_db）
- 設定管理
  - .env ファイルと環境変数の読み込み（自動ロード。無効化可能）

---

## 必要条件・依存ライブラリ

最低限の依存（実行する機能により追加ライブラリが必要）:

- Python 3.9+
- duckdb
- openai（OpenAI の公式 SDK：LLM 呼び出し）
- defusedxml（RSS XML パース安全化）
- 標準ライブラリ（urllib, json, logging 等）

インストール例（プロジェクトルートで仮想環境を作る想定）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# またはパッケージを editable install する場合
pip install -e .
```

（本 README はパッケージ配布用の requirements.txt / pyproject.toml があることを前提とします）

---

## セットアップ手順

1. リポジトリをクローン

   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. 仮想環境を作成して依存をインストール（上記参照）

3. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（config モジュールによる自動ロード）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（主なもの）:

- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- KABU_API_PASSWORD
  - kabu ステーション API のパスワード（注文連携等を行う場合）。
- SLACK_BOT_TOKEN
  - Slack 通知を行う場合に必要。
- SLACK_CHANNEL_ID
  - Slack の通知先チャンネル ID。
- OPENAI_API_KEY
  - LLM 呼び出し（score_news, score_regime 等）に必要。

オプション（デフォルト値あり）:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視・モニタリング用 SQLite（デフォルト: data/monitoring.db）

config.Settings により環境変数未設定時は ValueError が投げられます（必須変数）。

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL から直接使うときの例です。

- DuckDB 接続を作成して ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーが必要）

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DuckDB 初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.kabusdb")
# conn は監査テーブルが初期化された DuckDB 接続
```

- 設定読み込み・参照

```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)  # KABUSYS_ENV == "live" かどうか
```

注意点:
- 上記関数は多くが DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。接続は `duckdb.connect(path)` で作成してください。
- LLM を使う関数は OPENAI_API_KEY（または api_key 引数）を必要とします。
- J-Quants 呼び出しを行う関数は JQUANTS_REFRESH_TOKEN を必要とします。

---

## 主要 API の説明（抜粋）

- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
  - デイリー ETL（カレンダー・株価・財務・品質チェック）を順に実行。ETLResult を返す。

- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - J-Quants API からの生データ取得（ページネーション対応）

- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュース記事を銘柄ごとに集約し LLM にてセンチメント評価。ai_scores テーブルへ保存。

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースの LLM スコアを組み合わせて market_regime に保存。

- kabusys.data.quality.run_all_checks(conn, ...)
  - 品質チェック（欠損・重複・スパイク・日付不整合）をまとめて実行。

- kabusys.data.audit.init_audit_db(path)
  - 監査ログ用 DB を初期化して接続を返す。

---

## ディレクトリ構成

（パッケージルートは src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env 自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約・OpenAI でのバッチスコアリング（score_news）
    - regime_detector.py
      - ETF MA200 とマクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - etl.py
      - ETLResult の公開エントリ
    - news_collector.py
      - RSS 取得・記事正規化・raw_news 保存
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・バッチ更新ジョブ
    - quality.py
      - データ品質チェック（QualityIssue）
    - stats.py
      - 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py
      - 監査テーブル DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン・IC・統計サマリ・rank 等

---

## 注意事項 / 実運用向けメモ

- OpenAI: 各 API 呼び出しはリトライや JSON バリデーションを行いますが、API 使用時は利用料やレート制限に注意してください。
- J-Quants: レート制限（120 req/min）に合わせた内部レートリミッタを実装しています。ID トークンの自動リフレッシュ対応あり。
- 自動 .env ロード:
  - プロジェクトルート（__file__ の親）から .git または pyproject.toml を探索して .env/.env.local を読み込みます。
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利）。
- Look-ahead バイアス回避:
  - モジュール設計上、内部処理は基本的に target_date を明示して実行する方針です。backtest 等で使用する際は適切なデータスコープ管理を行ってください。
- DuckDB の executemany はバージョン差異があるため、pipeline 内で空リストを渡さない等の注意が払われています。
- RSS の取得では SSRF 対策（リダイレクト検査 / プライベート IP の排除 / 最大バイト数制限 / defusedxml）を行っています。

---

必要であれば、サンプル .env.example のテンプレートや典型的な運用スクリプト（cron / Airflow / systemd 用）も追加で作成できます。どの範囲を優先して欲しいか教えてください。