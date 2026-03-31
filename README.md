# KabuSys

日本株向け自動売買 / データプラットフォーム コンポーネント群

---

## プロジェクト概要

KabuSys は日本株向けのデータ収集・品質管理・リサーチ・AI ベースのニュースセンチメント解析、
市場レジーム判定、監査ログ（トレーサビリティ）などを提供するライブラリ群です。
DuckDB をデータストアとして利用し、J-Quants API / RSS / OpenAI（gpt-4o-mini）等と連携することを想定しています。

主な用途:
- 日次 ETL（株価・財務・カレンダー）の差分取得と保存
- ニュースの NLP スコアリング（銘柄別センチメント）
- マクロニュースと ETF MA に基づく市場レジーム判定
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）
- データ品質チェックと監査ログ（監査テーブルの初期化）
- ニュース収集（RSS）と前処理

---

## 機能一覧

- 環境設定管理（.env 自動ロード、Settings オブジェクト）
- J-Quants API クライアント（レート制御・リトライ・ページネーション・保存関数）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS、安全対策付き、トラッキングパラメータ削除）
- ニュース NLP（gpt-4o-mini を用いた銘柄別センチメント score_news）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成して score_regime）
- リサーチ用ユーティリティ（ファクター計算、IC、将来リターン、Zスコア正規化）
- 監査ログ（signal_events / order_requests / executions）スキーマ作成と初期化

---

## 必要な依存パッケージ（主要）

このリポジトリに requirements.txt は含まれていませんが、本コードで想定されている主要パッケージは次のとおりです。

- Python 3.10+（型アノテーションに Union| 使用などを考慮）
- duckdb
- openai
- defusedxml

インストール例:
pip install duckdb openai defusedxml

（プロジェクト配布時は pyproject.toml / requirements.txt を参照してください）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: (監視用) SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 対象環境 ("development" / "paper_trading" / "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  OS環境変数 > .env.local > .env の順で読み込みます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトをパッケージとして利用する場合は、パッケージのインストール方法に従ってください。）

3. 環境変数を設定
   - 上記の必須環境変数を .env または環境に設定します。

4. DuckDB 用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要な API と実行例）

以下は最小限のコード例です。各関数は duckdb 接続および日付を受け取ります。

共通準備:
from datetime import date
import duckdb
from kabusys.config import settings

# DuckDB に接続（ファイルまたは :memory:）
conn = duckdb.connect(str(settings.duckdb_path))

### 1) 日次 ETL の実行
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

### 2) ニュースセンチメントスコア (銘柄別)
from kabusys.ai.news_nlp import score_news

# OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored stocks: {n}")

関数シグネチャ:
- score_news(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: str | None = None) -> int

### 3) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime

r = score_regime(conn, target_date=date(2026, 3, 20))
# returns 1 on success, writes market_regime テーブル

関数シグネチャ:
- score_regime(conn: duckdb.DuckDBPyConnection, target_date: date, api_key: str | None = None) -> int

### 4) 監査ログ（Audit DB）初期化
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可能
# これで signal_events / order_requests / executions 等のテーブルが作成される

### 5) カレンダー補助
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_open = is_trading_day(conn, date(2026, 3, 20))
next_day = next_trading_day(conn, date(2026, 3, 20))

### 6) 研究用ユーティリティ
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))

forward = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")

---

## 実行上の注意点・設計方針（簡潔）

- ルックアヘッドバイアス回避:
  - 多くの処理は内部で datetime.today() を直接参照せず、呼び出し側が target_date を渡す設計です。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）呼び出しが失敗した場合でも処理を中断せずフォールバックする実装が多くあります（例: マクロセンチメントが取得できないときは 0.0）。
- 冪等性:
  - J-Quants 保存処理は ON CONFLICT DO UPDATE を用いた冪等保存を行います。
  - ETL の更新は差分取得・バックフィルにより後出し修正を吸収します。
- テスト用フック:
  - OpenAI 呼び出しや RSS の _urlopen など、一部の内部関数はテスト用にモック差替えがしやすい設計です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                        — 環境設定/Settings
- ai/
  - __init__.py
  - news_nlp.py                    — ニュース NLP（score_news）
  - regime_detector.py             — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py         — 市場カレンダー管理
  - pipeline.py                    — ETL パイプライン / run_daily_etl
  - etl.py                         — ETLResult 再エクスポート
  - jquants_client.py              — J-Quants API クライアント & 保存関数
  - news_collector.py              — RSS ニュース収集
  - quality.py                     — データ品質チェック
  - stats.py                       — 統計ユーティリティ（zscore_normalize）
  - audit.py                       — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py             — ファクター計算（momentum/value/volatility）
  - feature_exploration.py         — 将来リターン、IC、統計サマリー
- research/...（その他ユーティリティ）

（上記はコードベースの主要モジュール一覧です。実際の配布時は pyproject.toml / setup.cfg / requirements.txt 等を参照してください）

---

## 開発・貢献

- Pull Request / Issue を歓迎します。設計方針に沿った変更（テスト、型、安全性、冪等性など）を重視してください。
- 外部 API キーや機密情報は .env で管理し、リポジトリに直接コミットしないでください。

---

この README はコードベースの公開インターフェースと主要な使い方をまとめたものです。より詳しい仕様（DataPlatform.md, StrategyModel.md 等）が付属する場合はそちらを参照してください。