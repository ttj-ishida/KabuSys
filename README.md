# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants などの外部データソースと連携してデータ収集（ETL）・品質チェック・特徴量算出・AI ベースのニュースセンチメント評価・市場レジーム判定・監査ログ管理を行うことを目的としています。

主な想定用途:
- データプラットフォーム（株価・財務・カレンダーの差分ETL）
- 研究（ファクター計算・将来リターン・IC・統計サマリー）
- ニュースセンチメント（OpenAI を用いた銘柄別スコアリング）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定読み込みと検証（`.env`, `.env.local`, OS 環境変数）
  - 自動ロードはプロジェクトルート（`.git` または `pyproject.toml`）を基準に行う
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能
- Data:
  - J-Quants API クライアント（取得・ページネーション・リトライ・レート制限）
  - 日次 ETL（株価、財務、JPX カレンダー）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - ニュース収集（RSS、SSRF 対策、前処理、冪等保存）
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
  - DuckDB 向けの保存ロジック（冪等）
- Research:
  - ファクター計算（Momentum / Volatility / Value / Liquidity 等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- AI:
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別）
  - マクロニュース + ETF MA を組合せた市場レジーム判定
  - 冪等・フェイルセーフ・リトライ実装（API障害時はスコアを中立にフォールバック）
- ユーティリティ:
  - 時刻・タイムゾーン設計（UTC 保存、Look-ahead 回避）
  - SSL/HTTP/URL 正規化・トラッキングパラメータ除去

---

## 前提条件

- Python 3.10 以上（型注釈に union 型や typing 機能を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

依存パッケージはプロジェクトの requirements.txt / pyproject.toml にまとめている想定です。なければ以下のように手動でインストールしてください（例）:

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / 取得
   - プロジェクトルートに `pyproject.toml` または `.git` があることを想定

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存のインストール
   - pip install -r requirements.txt
   - または個別に: pip install duckdb openai defusedxml

4. インストール（開発モード）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成
   - 自動読み込みはデフォルトで有効（`.env` → `.env.local`、OS 環境変数が優先）
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

例: .env（必要最小限）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
OPENAI_API_KEY=your_openai_api_key   # AI 機能を使う場合

設定関連は `kabusys.config.settings` 経由で取得されます。必須の環境変数が未設定だと ValueError が発生します。

デフォルト DB パス（settings）:
- DuckDB: data/kabusys.duckdb
- SQLite (監視用): data/monitoring.db
- PID ファイル: data/execution.pid

---

## 使い方（主要なユースケース例）

以下はライブラリを直接インポートして利用するサンプルです。すべて DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を渡して操作します。

- 日次 ETL を実行する（株価 / 財務 / カレンダー + 品質チェック）:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメントをスコアリングして ai_scores に保存する:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
print(f"書き込み銘柄数: {written}")

- 市場レジームを判定して market_regime に保存する:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

- 監査ログ（監査DB）を初期化する:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成して接続を返す

- 研究用ファクター計算・IC・統計:

from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary

conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
factors = calc_momentum(conn, target_date=date(2026,3,20))
forwards = calc_forward_returns(conn, target_date=date(2026,3,20))
ic = calc_ic(factors, forwards, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(factors, ["mom_1m", "ma200_dev"])

注意点:
- AI 機能を使う場合は OpenAI API キーの指定が必要（引数 or 環境変数 OPENAI_API_KEY）。
- すべての関数は look-ahead bias を避ける設計（target_date 以下のデータのみ使用）です。
- DuckDB 側のテーブル構成（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）が前提になります。ETL で初期整備してください。

---

## .env の動作と挙動

- 自動ロード順序:
  1. OS 環境変数（最優先）
  2. .env.local（存在すれば上書き）
  3. .env（未設定キーのみセット）
- 自動ロードを無効化する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- `.env` のパースはシェル風に `KEY=VAL`、`export KEY=VAL`、引用符・エスケープ・コメントをサポートします。
- 必須キーは `kabusys.config.Settings` のプロパティ参照時に検査され、未設定時は ValueError を送出します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                       : 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                    : ニュースセンチメント（銘柄別）
  - regime_detector.py             : 市場レジーム判定（ETF MA + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py              : J-Quants API クライアント（取得/保存）
  - pipeline.py                    : ETL パイプライン（run_daily_etl 等）
  - etl.py                         : ETL 結果の公開（ETLResult）
  - stats.py                       : 統計ユーティリティ（zscore_normalize）
  - quality.py                     : データ品質チェック
  - calendar_management.py         : マーケットカレンダー管理（営業日判定）
  - news_collector.py              : RSS ニュース収集・保存
  - audit.py                       : 監査ログスキーマ初期化 / DB 初期化
- research/
  - __init__.py
  - factor_research.py             : ファクター計算（Momentum / Value / Volatility 等）
  - feature_exploration.py         : 将来リターン / IC / 統計サマリー
- research 層は data.stats を利用
- （パッケージには monitoring / execution 等の名前が __all__ に含まれる場合がありますが、本リポジトリの該当ファイルは利用箇所に応じて存在します）

---

## 開発・貢献

- テスト: 各モジュールは外部依存（HTTP や OpenAI）呼び出しを分離しており、ユニットテストではモックが容易です。
  - 例: news_nlp._call_openai_api や regime_detector._call_openai_api を patch してテスト可能
- コード品質: SQL はパラメータバインド（?）を使い、SQLインジェクションを低減しています。
- ログ出力: 各モジュールは logger を使用しており、環境変数 LOG_LEVEL で制御できます（DEBUG/INFO/...）。

---

## よくある質問 / トラブルシュート

- DuckDB にテーブルがない:
  - ETL を実行することで必要なテーブルが作成される想定（あるいはマイグレーションスクリプトを用意してください）。
- OpenAI レスポンスが不正 JSON の場合:
  - news_nlp/regime_detector はパース失敗時に中立スコア（0.0）へフォールバックします。ログを確認してください。
- J-Quants API のレート/401 エラー:
  - jquants_client はレート制限とトークン自動リフレッシュ/リトライを実装しています。設定トークンを確認してください。

---

README はここまでです。必要なら以下を提供できます:
- pyproject.toml / requirements.txt の例
- 初期スキーマ作成 SQL（テーブル作成スクリプト）
- 実行用サンプル CLI スクリプト（run_etl.py / score_news.py / score_regime.py）