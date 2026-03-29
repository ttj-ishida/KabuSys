# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants → DuckDB）、ニュース収集・NLP（OpenAI）、リサーチ（ファクター計算）、監査ログ（発注トレーサビリティ）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集して raw_news に保存し、銘柄ごとに OpenAI でニュースセンチメントを算出して ai_scores に格納
- ETF とマクロニュースの組合せで市場レジーム（bull/neutral/bear）を判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化・操作ユーティリティ

設計方針の一例:
- ルックアヘッドバイアスを避けるため、基本的に datetime.today()/date.today() を内部処理で参照しない。
- DuckDB を用いた SQL ベースの処理（外部 heavy ライブラリに依存しない実装）。
- OpenAI / J-Quants に対する堅牢なリトライやフェイルセーフ処理を実装。

---

## 機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数、認証・レート制御・リトライ）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（fetch_rss、URL 正規化、SSRF 対策、前処理）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - news_nlp.score_news: ニュースを OpenAI でセンチメント化して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）200日MA乖離 + マクロニュースセンチメントを合成して market_regime に保存
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config
  - 環境変数管理（.env 自動ロード、Settings クラス）
- audit / monitoring / strategy / execution（パッケージ公開インターフェースとして __all__ に含める設計）

---

## 必要な依存関係（主なもの）

- Python 3.10+
- duckdb
- openai (OpenAI の公式 SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

インストール例（プロジェクトルートで）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# またはパッケージの setup/pyproject があれば:
# pip install -e .
```

---

## 環境変数 / .env

パッケージはプロジェクトルート（pyproject.toml または .git のある親ディレクトリ）を探索して `.env` / `.env.local` を自動ロードします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。  
必須な環境変数（Settings から参照）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news, regime_detector 使用時）
- DUCKDB_PATH — デフォルト "data/kabusys.duckdb"（任意）
- SQLITE_PATH — 監視用 SQLite パス（任意）
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト development）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

例 (.env.example 的な内容):
```env
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースはシェル風の simple parser に対応しています（export プレフィックス・クォート・コメント等の扱いに注意）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境の作成と有効化
3. 必要パッケージのインストール（上記参照）
4. `.env` を作成して必要なキーを設定
5. DuckDB データベースおよび監査DBの初期化（任意）

監査DB初期化例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 既存 conn を渡して init_audit_schema(conn) することも可能
```

ETL 用の DuckDB コネクション例:
```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

---

## 使い方（主要ユーティリティの例）

- 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）スコアリング
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定（ETF 1321 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- カレンダー判定・ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- ニュースの収集（RSS を直接取得）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

注意点:
- OpenAI 呼び出しは JSON mode（厳密な JSON を期待）で行われます。API の失敗やパースエラーはログに出て 0.0 等の安全側値にフォールバックします。
- J-Quants クライアントは rate limit（120 req/min）を守る実装になっています。ID トークンの自動リフレッシュやリトライロジックあり。

---

## ディレクトリ構成（抜粋）

提供されているファイルに基づく主要構成:

- src/
  - kabusys/
    - __init__.py
    - config.py                     -- 環境変数と Settings
    - ai/
      - __init__.py
      - news_nlp.py                 -- ニュースセンチメント & score_news
      - regime_detector.py          -- 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py           -- J-Quants API クライアント（fetch/save）
      - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
      - etl.py                      -- ETL の公開型（ETLResult）
      - calendar_management.py      -- マーケットカレンダー管理
      - news_collector.py           -- RSS 収集・前処理（SSRF 対策等）
      - quality.py                  -- データ品質チェック
      - stats.py                    -- 統計ユーティリティ（zscore_normalize）
      - audit.py                    -- 監査ログスキーマ初期化（init_audit_schema）
    - research/
      - __init__.py
      - factor_research.py          -- calc_momentum / calc_value / calc_volatility
      - feature_exploration.py      -- calc_forward_returns / calc_ic / factor_summary / rank
    - ai/, data/, research/ の他に
      - (strategy/, execution/, monitoring/ などのサブパッケージが __all__ としてエクスポートされる設計)

上記は主要なモジュールとその責務を示しています。各モジュールの docstring に詳細な設計方針と例が記載されています。

---

## ログ・エラー処理

- ログレベルは環境変数 LOG_LEVEL（デフォルト INFO）で制御します。
- 多くの外部 API 呼び出しはリトライ・フェイルセーフ（API失敗時は処理続行や安全値へフォールバック）を実装しています。重大な DB 書込み失敗などは例外を伝播します。

---

## テスト／開発上のヒント

- 自動 .env ロードを無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に利用）。
- OpenAI 呼び出しをモックする箇所:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
- J-Quants の HTTP 呼び出しは urllib を用いた同期実装です。単体テストでは _request / _urlopen 等をモックするのが容易です。

---

## 免責・補足

- 本ライブラリは自動売買システムの一部を構成するユーティリティ群です。実際の発注（ブローカー連携）や資金管理ロジックは別モジュール（execution / strategy 等）で実装する想定です。
- 金融データや API の利用に関する認証情報の扱いは十分に注意してください。特に本番環境（KABUSYS_ENV=live）では権限管理・ログの取り扱いに注意する必要があります。

---

必要であれば、README に含めるサンプルコードや .env.example、docker-compose / systemd の起動例、CI 用のテストコマンドなどを追加で作成できます。どの情報を追加しますか？