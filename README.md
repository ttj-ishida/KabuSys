# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、データ品質チェック、ニュース収集・NLP（OpenAI）によるセンチメント、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主に以下を提供します。

- J-Quants API を用いたデータ ETL（株価・財務・マーケットカレンダー）
- DuckDB を用いた永続化／保存処理（冪等保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント（銘柄別 ai_score）および市場レジーム判定
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 発注〜約定までをトレース可能にする監査ログスキーマ（DuckDB）

設計上、バックテストでのルックアヘッドバイアスを避けるために、内部実装は「target_date を明示的に渡す」「datetime.today()/date.today() を不用意に参照しない」方針を採用しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系関数、トークン自動リフレッシュ、レートリミット管理）
  - カレンダー管理（営業日判定、次/前営業日検索、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、raw_news への冪等保存）
  - 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI により算出して ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースセンチメントを合成して市場レジーム判定
- research/
  - calc_momentum / calc_value / calc_volatility: ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank: 特徴量探索・評価ユーティリティ
- config:
  - 環境変数読み込み (.env/.env.local 自動読み込み) と settings オブジェクト

---

## 前提・依存

- Python 3.10 以上（typing の構文に依存）
- 主なライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API / 各 RSS フィード / OpenAI API

必要なパッケージはプロジェクトの requirements.txt を参照するか、手動でインストールしてください。例:

pip install duckdb openai defusedxml

---

## 環境変数（必須・任意）

config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注機能を利用する場合）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）

自動 .env 読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local を自動で読み込みます。
- 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成・有効化（推奨）

python -m venv .venv
source .venv/bin/activate  # Unix
.venv\Scripts\activate.bat  # Windows

3. 必要パッケージをインストール

pip install -e .               # パッケージがセットアップ済みであれば
# または最低限:
pip install duckdb openai defusedxml

4. 環境変数を設定
- プロジェクトルートに `.env`（または `.env.local`）を作成し、上記の必須キーを設定してください（.env.example を参考に）。
- 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...

5. DuckDB データベースファイルの配置先ディレクトリを作成（必要な場合）

mkdir -p data

---

## 使い方（基本例）

以下は Python スクリプトまたは REPL での基本的な利用例です。

- settings を使う（環境変数の参照）

from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)

- DuckDB 接続を作成して日次 ETL を実行（J-Quants から差分取得 → 保存 → 品質チェック）

import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメント（OpenAI）を計算して ai_scores に書き込む

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込んだ銘柄数:", written)

- 市場レジーム判定（MA + マクロセンチメント）

from kabusys.ai.regime_detector import score_regime
from datetime import date
written = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime returned:", written)

- 監査ログ DB を初期化

from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions) が作成されます

- J-Quants クライアント（直接使う例）

from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って自動で取得
quotes = jq.fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
print(len(quotes))

---

## 実用上の注意点 / 設計方針ハイライト

- ルックアヘッドバイアス回避:
  - AI / ETL / リサーチ関数は内部で現在日時を直接参照せず、必ず target_date を引数で受け取るように設計されています。
- 冪等性:
  - J-Quants からの保存処理は ON CONFLICT DO UPDATE を使って冪等に行われます。
- フェイルセーフ:
  - AI の API 呼び出しや外部 API の失敗時は、可能な限りスキップして継続し、致命的な失敗を避ける設計です（ログを残します）。
- セキュリティ:
  - RSS 取得時は SSRF 対策、応答サイズ制限、XML 脆弱性対策（defusedxml）を行っています。
- レート制御:
  - J-Quants クライアントはレートリミット（120 req/min）に合わせた固定間隔スロットリングを実装しています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定管理（settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py            — ニュース NLP（score_news）
  - regime_detector.py     — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py      — J-Quants API クライアント（fetch/save 等）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - news_collector.py      — RSS ニュース収集・前処理
  - quality.py             — データ品質チェック
  - stats.py               — 統計ユーティリティ（zscore_normalize）
  - audit.py               — 監査ログ（テーブル定義・初期化）
  - etl.py                 — ETL の公開インターフェース（ETLResult エクスポート）
- research/
  - __init__.py
  - factor_research.py     — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン・IC・統計サマリー 等
- research/..., ai/..., data/... にさらに詳細な実装ファイルが含まれます

---

## 開発・テスト

- 自動 .env 読み込みはデフォルトで有効です。テスト時に .env の自動読み込みを無効にしたい場合は環境変数を設定してください:

export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- AI 呼び出しや外部ネットワーク呼び出しを含む関数はモックしやすいように設計されています（テスト時はモックして単体テストを行ってください）。

---

## 追加情報 / 今後の拡張

- 発注実行（ブローカー連携）やポジション管理モジュールは別モジュールとして実装可能です（現状は監査ログスキーマを提供）。
- バックテスト用インターフェース（market data snapshot / 過去用 API）を整備予定。

---

作業上のご質問や README の拡張（例: 各テーブルスキーマの詳細、サンプル .env.example の追加、CI / デプロイ手順）などが必要であれば教えてください。