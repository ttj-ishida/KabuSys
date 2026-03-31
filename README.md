# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（発注・約定トレース）などを含むモジュール群を提供します。

---
目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（主要 API と実行例）
- 環境変数（.env）/ 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株アルゴリズム運用に必要なデータ基盤・研究ツール群をまとめたパッケージです。設計上の共通方針として：

- Look-ahead バイアスを避ける（内部で date.today() を不用意に使わない）
- ETL / DB 操作は DuckDB を使用
- 外部 API 呼び出し（J-Quants / OpenAI）はフェイルセーフなリトライやバックオフを備える
- 冪等性（ON CONFLICT / idempotent 保存）を重視
- ニュース収集では SSRF 対策・サイズ制限・トラッキング除去などの安全策を実装

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（fetch_rss, preprocess_text）・news_symbols / raw_news の取扱い
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログ（init_audit_schema / init_audit_db）: signal / order_request / execution の DDL・インデックス
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP による銘柄センチメントスコアリング（score_news）
  - 市場レジーム判定（score_regime） — ETF 1321 の MA200 とマクロニュースの LLM 評価を合成
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量確認 / IC 計算 / 前方リターン計算（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み・管理（Settings オブジェクト）

---

## セットアップ手順

前提: Python 3.10+（typing の Union 省略表記等に合わせてください）。実行環境に合わせてバージョンを調整してください。

1. リポジトリをクローン（またはパッケージを配置）
2. 必要パッケージをインストール（例）

   pip を使う例:
   ```
   python -m pip install duckdb openai defusedxml
   ```
   - その他、標準ライブラリやプロジェクト依存のパッケージがあれば requirements.txt に従ってください。

3. 環境変数を設定
   - 開発時はプロジェクトルートに `.env` / `.env.local` を置くことで自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すれば自動ロードを無効化できます）。
   - 必須環境変数の例は次節を参照。

4. DuckDB ファイルや監査 DB 用ディレクトリを作る
   - デフォルトの DuckDB パスは `data/kabusys.duckdb`（Settings.duckdb_path）
   - 監査用 DB は `data/monitoring.db` など（Settings.sqlite_path は監視用 SQLite のパスを示唆する設定があるが、監査は DuckDB に init する helper を提供）

---

## 環境変数（主なもの）

config.Settings クラスで参照する代表的な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に渡せる）
- KABU_API_PASSWORD — kabuステーション API のパスワード（使用箇所に応じて）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite 等のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して `.env` / `.env.local` を読み込みます。
- 読み込み優先: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます（テスト用途など）。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な API と実行例）

以下は主要ユースケースの呼び出し例です。実際にはロガー設定やエラーハンドリングを付けてください。

- DuckDB 接続を開く例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API が必要）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("scored codes:", n_written)
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

res = score_regime(conn, target_date=date(2026,3,20), api_key=None)
# 1 が返れば成功（market_regime テーブルへ書き込まれる）
```

- 監査ログ用 DuckDB を初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.db")
# これで監査用テーブル(signal_events, order_requests, executions) が作成される
```

- 研究用ファクター計算:
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, target_date=date(2026,3,20))
value = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- ニュース取得（個別 RSS フェッチ）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しは retry/backoff を内包していますが、API キーのレート制限や料金に注意してください。
- ETL / save 系は DuckDB に対して冪等保存を行います。`ON CONFLICT` による上書き挙動を理解しておいてください。
- news_collector.fetch_rss は SSRF 対策とサイズ制限を実装しています。外部 URL の扱いに注意してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールと責務の概観です（省略あり）。パッケージは __init__.py でサブモジュールをエクスポートします。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP スコアリング（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch / save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult 再エクスポート
    - calendar_management.py         — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py              — RSS 取得・正規化・保存用ユーティリティ
    - quality.py                     — データ品質チェック
    - stats.py                       — zscore_normalize 等
    - audit.py                       — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py             — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py         — calc_forward_returns, calc_ic, factor_summary, rank

---

## 開発・テスト時のヒント

- 環境変数自動読み込みはプロジェクトルートを .git / pyproject.toml で判定します。CI やユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して制御してください。
- OpenAI 呼び出しなど外部 API は unittest.mock.patch で _call_openai_api（モジュール内）を差し替えることで簡単にモックできます（news_nlp, regime_detector それぞれで独立実装）。
- DuckDB はファイルパスに該当ディレクトリが無ければ作成するコードを一部持っています（init_audit_db 等）。テスト用に ":memory:" を渡すとインメモリ DB を使用できます。
- news_collector 内の HTTP 処理は SSRF 対策や最大レスポンスサイズ制限があるため、外部 RSS を利用する場合は十分にテストしてください。

---

必要であれば README に以下を追加できます:
- 詳細な schema 定義（raw_prices, raw_financials, ai_scores 等のカラム）
- CI / テスト実行方法（pytest など）
- 実運用での運用手順（cron / Airflow ジョブ例、Slack 通知連携例）

追加で欲しいセクションがあれば指示してください。