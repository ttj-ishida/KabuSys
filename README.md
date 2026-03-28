# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下の関心事を分離しながら一貫したワークフローを提供することを目的としたライブラリです。

- J-Quants API を用いた株価・財務・カレンダーデータの差分取得（レート制御、再試行、トークン自動リフレッシュ対応）
- DuckDB を用いた永続化（冪等保存）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS からのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング（銘柄別 / マクロ）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログテーブル（signal → order_request → execution をトレース）

---

## 主な機能一覧

- data.jquants_client: J-Quants API クライアント（取得・保存・ページネーション・レート制御・再試行）
- data.pipeline: 日次 ETL パイプライン（差分取得・保存・品質チェック）
- data.quality: 品質チェック（欠損・スパイク・重複・日付不整合）
- data.news_collector: RSS 収集・前処理・保存補助（SSRF / GZip / トラッキング除去）
- data.calendar_management: JPX マーケットカレンダーの管理、営業日判定ユーティリティ
- data.audit: 監査ログ（signal_events / order_requests / executions）テーブル初期化ユーティリティ
- ai.news_nlp: ニュース記事を銘柄ごとに LLM でスコアリングし ai_scores に書き込む
- ai.regime_detector: ETF（1321）の 200 日移動平均乖離とマクロセンチメントを合成して市場レジームを判定
- research: ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー、IC 等）
- config: .env / 環境変数の管理、Settings オブジェクト（アプリ設定の一元取得）

---

## 必要条件 / 依存ライブラリ

- Python 3.10 以上（`X | None` の型表記を利用）
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, datetime, json, logging 等）

例（pip）:
pip install duckdb openai defusedxml

※ プロジェクトで requirements.txt がある場合はそれに従ってください。

---

## 環境変数（主なもの）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（優先度: OS 環境変数 > .env.local > .env）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（data.jquants_client で使用）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（発注周り）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV: 開発環境（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト `INFO`
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視用 SQLite パス。デフォルト `data/monitoring.db`
- OPENAI_API_KEY: OpenAI API キー（ai.score系関数に渡すか環境変数で参照）

設定は `kabusys.config.settings` から取得できます（例: `from kabusys.config import settings`）。

---

## セットアップ手順（開発例）

1. リポジトリを取得
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -r requirements.txt
   # requirements.txt がない場合:
   pip install duckdb openai defusedxml

4. 環境変数を設定
   プロジェクトルートに `.env`（あるいは `.env.local`）を作成して以下を設定します（例）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   または環境変数としてエクスポートしてください。`.env.example` を参照して作成してください（プロジェクトに存在する場合）。

5. DuckDB データベース用ディレクトリ作成（必要なら）
   mkdir -p data

---

## 基本的な使い方（コード例）

以下はライブラリを直接インポートして使う簡単な例です。DuckDB 接続には `duckdb.connect(path)` を使用します。

- 日次 ETL を実行する（市場カレンダー取得 → 株価・財務 ETL → 品質チェック）

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースをスコアリングして ai_scores に書き込む

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY 環境変数参照
print(f"scored {count} codes")

- 市場レジームを判定して market_regime テーブルへ保存

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OpenAI API キーは環境変数か引数で指定

- 監査ログ用の DuckDB を初期化する

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルへアクセスできます

- 研究用ファクター計算例（モメンタム）

from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）

---

## 注意点 / 実装上の設計方針（要点）

- ルックアヘッドバイアス対策: モジュール多くが内部で `date.today()` を直接参照せず、明示的に `target_date` を受け取る設計です。バックテスト等では過去日付を明示的に渡してください。
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE 等で冪等に実装されています。
- レート制御・再試行: J-Quants クライアントは 120 req/min のレート制限を固定間隔スロットリングで守ります。HTTP 408/429/5xx に対して指数バックオフでリトライします。401 受信時はトークン自動リフレッシュを試みます。
- LLM 呼び出し: OpenAI 呼び出しには再試行ロジックがあり、API エラーやパースエラーが発生してもフェイルセーフ（スコアを 0 にする等）で継続する設計です。
- ニュース収集の安全対策: SSRF 防止、gzip サイズ上限、defusedxml を用いた安全な XML パース、トラッキングパラメータ除去などを実装しています。
- DuckDB バージョン互換: 一部の実装は DuckDB の executemany の制約などを考慮しています（例: executemany に空リストを渡さない等）。

---

## ディレクトリ構成

以下は主要ファイル / モジュールの抜粋です（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースの銘柄別スコアリング
    - regime_detector.py          — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（取得・保存）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETLResult 再エクスポート
    - news_collector.py           — RSS 収集・前処理
    - calendar_management.py      — マーケットカレンダーの管理・営業日ユーティリティ
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - quality.py                  — データ品質チェック
    - audit.py                    — 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py          — Momentum/Value/Volatility 等
    - feature_exploration.py      — forward returns / IC / factor_summary / rank

---

## ログと環境（運用）

- ログレベルは環境変数 `LOG_LEVEL` で制御します。既定は `INFO`。
- 実稼働（kabu ステーションへの発注など）を行う際は、`KABUSYS_ENV=live` を設定し、設定やパスワード等を厳重に管理してください（本コード内では `settings.is_live` 等で分岐可）。
- OpenAI API の利用には費用が発生します。バッチ設計ではチャンクサイズやリトライポリシーを適切に調節してください。

---

## 追加情報 / テストのためのフック

- テスト時は以下のような差し替えが想定されています:
  - OpenAI 呼び出し関数を unittest.mock.patch でモックする（news_nlp._call_openai_api, regime_detector._call_openai_api など）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして環境読み込みを抑止
- DB の代わりに `duckdb.connect(":memory:")` を使えばメモリ上でテスト可能です。

---

必要であれば、README に含める CLI の使い方や .env.example のテンプレート、具体的な SQL スキーマ（テーブル作成スクリプト）やユースケース（ETL の cron スケジュール例、Slack 通知フロー）なども追加できます。どの情報を優先して追記しましょうか？