# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のライブラリ実装（モジュール群のみ）。  
このリポジトリはデータ取得（J-Quants）、ニュース収集・NLP（OpenAI）、研究用ファクター計算、ETL、監査ログ等の機能を提供します。

---

## 概要

KabuSys は日本株の自動売買・リサーチプラットフォームを構成する Python モジュール群です。主な役割は以下の通りです。

- J-Quants API を利用した株価・財務・カレンダー等の差分取得（ETL）
- RSS ベースのニュース収集と前処理（news_collector）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ニュースNLP）および市場レジーム判定
- DuckDB を用いたデータ保存・監査ログ（監査テーブル初期化・管理）
- 研究用ファクター計算・特徴量解析（momentum / value / volatility 等）
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計方針として、ルックアヘッドバイアス回避（内部で date.today()/datetime.today() を直接参照しない等）、冪等性（DB書き込みは ON CONFLICT で処理）、フェイルセーフ（外部API失敗時に処理継続）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（差分取得・保存・認証・リトライ・レートリミット）
  - pipeline: 日次 ETL 実行（価格・財務・カレンダーの差分取得保存 + 品質チェック）
  - news_collector: RSS 収集・前処理・raw_news 保存（SSRF 対策・サイズ制限）
  - calendar_management: JPX カレンダー管理・営業日ヘルパー（next/prev/is_trading_day 等）
  - audit: 監査ログ（signal / order_request / executions）スキーマ初期化ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp: ニュースを銘柄ごとに集約して OpenAI に投げ、ai_scores を更新
  - regime_detector: 1321（ETF）200日MA乖離とマクロニュースセンチメントを合成して市場レジーム判定
- research/
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリ

---

## 要件（推奨）

- Python 3.10 以上（typing の `|` 演算子を使用）
- ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで完結する部分も多いですが、OpenAI や DuckDB を利用する機能は上記が必要です。

requirements.txt がない場合は以下のようにインストールしてください（例）:

pip install duckdb openai defusedxml

---

## 環境変数 / 設定

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD に依存しない探索：.git または pyproject.toml による）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャネル ID

任意 / デフォルト（Settings でデフォルト値あり）:
- KABUSYS_ENV           : development | paper_trading | live （default: development）
- LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL （default: INFO）
- KABU_API_BASE_URL     : kabu API の base URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（default: data/monitoring.db）
- OPENAI_API_KEY        : OpenAI API キー（ai モジュールを利用する場合）

例 .env（テンプレート）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに `pyproject.toml` / requirements.txt があればそれに従ってください）

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接エクスポートしてください。

4. DuckDB などの初期化（監査DBなど）
   - Python REPL やスクリプトから init_audit_db を呼び出して監査 DB を初期化できます（下記使用例参照）。

---

## 使い方（サンプルコード）

※ 以下はライブラリ API の呼び出し例です。実行環境に応じてパスや DB 接続は調整してください。

- 日次 ETL を実行する（DuckDB 接続を渡す）:

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースセンチメント（ai.news_nlp.score_news）:

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} ai scores")

- 市場レジーム判定（ai.regime_detector.score_regime）:

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB 初期化:

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests などを書き込めます

- カレンダー/営業日関連ユーティリティ:

from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))

---

## 注意事項 / 実運用に関するヒント

- OpenAI を利用する機能（news_nlp / regime_detector）は API コストが発生します。API キーの管理と rate/コスト制御を行ってください。
- J-Quants API はレート制限があるため jquants_client ではレート制御・リトライを実装していますが、並列化する場合は注意してください。
- データ品質チェック（quality.run_all_checks）は ETL 後に適用し、結果に応じてアラートや ETL の中止判断を行うことを推奨します。
- DuckDB のバージョンによる互換性（executemany の仕様など）に注意してください。README 内のコードは DuckDB 0.10 系を前提とした記載が含まれます。
- 自動で .env を読み込む仕組みがありますが、テスト時などでそれを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/kabusys/
- __init__.py
- config.py                 — 環境変数 / 設定読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP（AI スコアの集約・書き込み）
  - regime_detector.py      — 市場レジーム判定ロジック
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（fetch/save 等）
  - pipeline.py             — 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector.py       — RSS 収集 & 前処理
  - calendar_management.py  — 市場カレンダー管理・営業日ユーティリティ
  - quality.py              — データ品質チェック群
  - stats.py                — 汎用統計（zscore_normalize 等）
  - audit.py                — 監査ログテーブル定義・初期化
  - etl.py                  — ETLResult のエクスポート
- research/
  - __init__.py
  - factor_research.py      — momentum, value, volatility
  - feature_exploration.py  — forward returns, IC, summary

その他:
- data/ (デフォルト DB 保存先)
- .env, .env.local (プロジェクトルートに配置して設定を管理)

---

## ライセンス / コントリビューション

この README はコードベースの概要説明を目的としています。実運用・本番展開や外部 API の利用に際しては、該当 API の利用規約・料金体系・組織内の運用ルールに従ってください。コントリビューションやバグ報告はリポジトリの ISSUE / PR フローに従って行ってください。

---

必要であれば、README に含めるサンプル .env.example、requirements.txt、あるいは具体的な初期化スクリプト（DB スキーマの作成や cron / ワーカーの起動例）も作成します。どの追加情報が必要か教えてください。