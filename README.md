# KabuSys

日本株向け自動売買／データプラットフォームライブラリ。J-Quants からのデータ取得・ETL、ニュースの収集と LLM を使ったニュースセンチメント評価、市場レジーム判定、研究（ファクター計算）や監査ログ（トレーサビリティ）などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（実行日時を直接参照しない等）
- DuckDB を中心としたローカル DB にデータを保存・管理
- API 呼び出しはリトライ／レート制御／フェイルセーフを備える
- ETL/品質チェック/監査ログは冪等（idempotent）設計

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得（ページネーション対応）
  - ETL の差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）
  - ETL の結果を ETLResult オブジェクトで返却

- ニュース収集・NLP
  - RSS からニュース収集（正規化・SSRF対策・サイズ制限）
  - ニュースと銘柄を紐付け raw_news / news_symbols テーブルへ保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）

- 市場レジーム判定
  - ETF 1321 の 200 日 MA とマクロニュースの LLM センチメントを組み合わせて日次で market_regime を作成（score_regime）

- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリーや Z スコア正規化

- データユーティリティ
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - DuckDB 保存ユーティリティ（save_daily_quotes / save_financial_statements 等）
  - 監査ログ（signal_events / order_requests / executions）初期化ユーティリティ（init_audit_schema / init_audit_db）

- 設定管理
  - 環境変数 / .env（.env.local）を自動読み込み（プロジェクトルート検出）
  - KABUSYS_* / JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY 等の環境変数を参照

---

## セットアップ手順

前提：
- Python 3.10+（型ヒントに | を使っているため）
- DuckDB、OpenAI SDK、defusedxml 等が必要

基本手順（例）:

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※プロジェクトに requirements ファイルがあればそれを使用してください。

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に設定）
   - 主な環境変数（下記参照）を設定

5. 自動 .env 読み込みについて
   - パッケージの起動時にパッケージルートを .git または pyproject.toml から検出し、`.env` / `.env.local` を自動で読み込みます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用。引数で上書き可）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知用（必須）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（例: data/monitoring.db）
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視関連
- KABUSYS_ENV — one of development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

---

## 使い方（コード例）

基本は各モジュールの関数をインポートして使用します。以下は代表的な例です。

- DuckDB 接続を作って ETL を実行する例

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ってニューススコアを計算する例（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None => OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化して接続を得る

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- news_collector の RSS 取得（単体）

```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点：
- OpenAI 呼び出しは API キーが必須（関数引数で渡すか環境変数 OPENAI_API_KEY を設定）
- J-Quants は get_id_token を通して id_token を取得するため、JQUANTS_REFRESH_TOKEN を設定してください
- ETL / API 呼び出しはネットワーク・API 制限のため時間がかかることがあります

---

## ディレクトリ構成

主なファイル／モジュール構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / .env 読み込み・設定
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント（score_news）
    - regime_detector.py            -- 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch/save）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - etl.py                        -- ETLResult の再エクスポート
    - news_collector.py             -- RSS 収集
    - quality.py                    -- データ品質チェック
    - stats.py                      -- Zスコア等統計ユーティリティ
    - calendar_management.py        -- 市場カレンダー管理
    - audit.py                      -- 監査ログ（スキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py            -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py        -- 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ を横断するユーティリティや内部関数が各ファイルに存在します

（上記はリポジトリ内の主要モジュールのみ抜粋）

---

## 運用上の注意・ベストプラクティス

- セキュリティ
  - .env に API トークンを置く場合は権限管理と .gitignore を適切に設定してください
  - news_collector は SSRF 対策を備えますが、外部 URL の扱いは注意してください

- ロギング / 実行モード
  - settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）
  - KABUSYS_ENV を切り替えて開発 / paper_trading / live の動作モードを区別

- 冪等性
  - 保存処理は基本的に ON CONFLICT DO UPDATE 等冪等設計です。ETL を複数回実行しても重複登録を抑制します

- テスト
  - OpenAI / HTTP 呼び出し箇所はモックしやすい設計（内部の呼び出しを差し替え可能）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使えば自動 .env 読み込みを無効化できます

---

問題や改善点、使い方の詳細なサンプルが必要であれば、どの機能に対してのサンプルが欲しいか教えてください。README の補足や英訳も対応できます。