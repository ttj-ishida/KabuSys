# KabuSys — 日本株自動売買基盤（README）

このリポジトリは日本株のデータ基盤・研究・AI評価・監査・ETL を含む
自動売買支援ライブラリ「KabuSys」のコードベースです。DuckDB をデータ層に使用し、
J-Quants / JPY マーケットデータ、RSS ニュース収集、OpenAI を使ったニュースセンチメント、
ファクター計算、ETL／品質チェック／監査ログなどの機能を備えています。

注意: 本 README はソースツリー内の docstring とコードから機能および使い方を
まとめたものです。実運用前に十分なレビューとテストを行ってください。

目次
- プロジェクト概要
- 主な機能一覧
- 必要環境・依存関係
- セットアップ手順
- 環境変数（.env）例
- 使い方（基本的なコード例）
  - DuckDB 接続の作成
  - 日次 ETL 実行
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
  - 監査ログスキーマ初期化
- 自動 .env ロードの挙動
- ディレクトリ構成（主要ファイルの説明）
- 補足・設計上の注意

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）・ニュース収集（RSS）・
AI（OpenAI）を使ったニュース解析・研究（ファクター計算・IC）・
ETL（差分更新・品質チェック）・監査ログ（トレーサビリティ）を提供する
Python ライブラリです。バックテストや自動売買システムの基盤として利用できます。

設計上の特徴（抜粋）
- DuckDB をローカル DB として使用（高速な列指向クエリ）
- Look-ahead バイアス対策（datetime.now()/today への依存を厳格に制御）
- API 呼び出しに対するリトライ・レートリミット・フェイルセーフ（部分失敗許容）
- ETL は冪等（ON CONFLICT / DELETE→INSERT 等）で設計
- ニュース収集時の SSRF / XML 攻撃対策（URL 正規化・defusedxml・受信サイズ制限）

---

## 主な機能一覧

- 環境設定管理: kabusys.config（.env 自動読み込み / 必須環境変数取得）
- Data / ETL:
  - J-Quants API クライアント（fetch / save 系）: kabusys.data.jquants_client
  - 日次 ETL パイプライン: kabusys.data.pipeline.run_daily_etl
  - カレンダー管理（JPX）: kabusys.data.calendar_management
  - データ品質チェック: kabusys.data.quality
  - ニュース収集（RSS）: kabusys.data.news_collector
  - 監査ログスキーマ・初期化: kabusys.data.audit
  - 汎用統計ユーティリティ: kabusys.data.stats
- AI:
  - ニュースセンチメント分析（銘柄ごと）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（MA200 + マクロニュース）: kabusys.ai.regime_detector.score_regime
- Research:
  - ファクター計算（モメンタム/バリュー/ボラティリティなど）: kabusys.research
  - 特徴量探索・IC、将来リターン計算など
- 監視 / 実行（execution）・戦略（strategy）・モニタリング（monitoring）用の名前空間（パッケージ公開）

---

## 必要環境・依存関係（代表）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ: urllib, json, logging, datetime など）

※ requirements.txt は本コードベースに含まれていないため、上記を pip でインストールしてください。

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトを editable install する場合）
   - pip install -e .

   ※ 実際の運用用には追加の依存（Slack クライアント等）が必要になる場合があります。

3. 環境変数 (.env) を作成
   - 本 README の「環境変数（.env）例」を参照して .env をプロジェクトルートに置く。

4. DuckDB ファイルを準備（省略可能）
   - デフォルトでは settings.duckdb_path = data/kabusys.duckdb
   - 初期化やスキーマ作成は個別の初期化スクリプトで行ってください（例: audit.init_audit_db など）。

---

## 環境変数（.env）例

必須（このコード内で _require() しているもの）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...

推奨 / 任意:
- OPENAI_API_KEY=...       # AI モジュール利用時に必要
- KABUSYS_ENV=development|paper_trading|live
- LOG_LEVEL=INFO|DEBUG|...
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動 .env ロードを無効化したい場合
- KABUSYS_API_BASE_URL (コードでは KABU_API_BASE_URL のデフォルトが設定されています)
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: パスワードや API キーは秘匿情報です。リポジトリに含めないでください。

---

## 使い方（基本例）

以下は Python REPL やスクリプト内での利用例です。実行前に必要な環境変数を設定してください。

1) DuckDB 接続の作成（settings を利用）
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行（株価・財務・カレンダーの差分更新 + 品質チェック）
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())  # ETL 実行結果の詳細

run_daily_etl は内部で jquants_client を使ってデータを取得し、保存・品質チェックを行います。

3) ニュースセンチメントを取得して ai_scores に書き込む
from kabusys.ai.news_nlp import score_news
from datetime import date
# score_news は OpenAI API key を環境変数 OPENAI_API_KEY または api_key 引数で受け取る
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込銘柄数: {n}")

4) 市場レジーム判定（ma200 に基づく + マクロニュース）
from kabusys.ai.regime_detector import score_regime
from datetime import date
r = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime:", r)

5) 監査ログ用 DB の初期化（監査専用 DB を生成）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_db はスキーマを作成し、UTC タイムゾーンを設定します

6) RSS フィードの取得（ニュース収集補助関数）
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["title"], a["datetime"])

---

## 自動 .env ロードの挙動

kabusys.config モジュールはパッケージインポート時にプロジェクトルート（.git または pyproject.toml）を探索し、
プロジェクトルート/.env と .env.local を自動で読み込みます（OS 環境変数を上書きしない設定で .env を読み込み .env.local は上書き可）。
自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py
  - パッケージのバージョンと公開サブパッケージを定義
- config.py
  - 環境変数 / .env 読み込み・設定取得（settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュース記事をまとめて OpenAI に送り銘柄ごとのセンチメントを ai_scores に書き込む
    - calc_news_window, score_news 等を提供
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュースの LLM 評価を合成して市場レジームを判定
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API の fetch/save 実装（レート制御・リトライ・認証）
  - pipeline.py
    - 日次 ETL のエントリポイント（run_daily_etl）、個別 ETL ジョブ
    - ETLResult データクラス
  - etl.py
    - ETLResult の再エクスポート
  - news_collector.py
    - RSS フィード取得、テキスト前処理、SSRF 防止、raw_news への保存用ユーティリティ
  - calendar_management.py
    - market_calendar の読み書き、営業日判定ロジック、calendar_update_job
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）のスキーマ定義と初期化
- research/
  - __init__.py
  - factor_research.py
    - Momentum / Value / Volatility 等のファクター計算（prices_daily, raw_financials を参照）
  - feature_exploration.py
    - 将来リターン計算、IC（Spearman）や統計サマリー等
- research/*, ai/* は研究用途・AI 評価用途に分離された設計

（注）一部のモジュールは別途テーブルスキーマ（raw_prices / raw_financials / raw_news / ai_scores / market_calendar 等）が
事前に存在することを前提としています。スキーマ定義・初期化は運用側で行ってください。

---

## 補足・設計上の注意

- セキュリティ: .env に含まれるシークレットは厳重に管理してください。
- Look-ahead バイアス: 多くの AI / 研究モジュールは内部で date パラメータに厳密に依存し、
  datetime.today() を直接参照しない設計です。バックテスト用途では target_date の扱いに注意してください。
- エラー処理: API 呼び出しはリトライやフォールバック（スコア 0.0 返却等）を行って継続性を重視する設計です。
- DuckDB の互換性: 一部の executemany() 呼び出しでは空リストを避ける実装上の配慮があります（DuckDB バージョン差分対策）。
- 実運用（ライブ注文）に接続する前に、戦略・リスク管理・監査ログの動作を十分に検証してください。

---

もし README に追記したい「実行用 CLI」「テーブルスキーマ定義」「CI / テスト手順」「追加サンプル」などがあれば、元となるスクリプトや要件を教えてください。README をそれに合わせて拡張します。