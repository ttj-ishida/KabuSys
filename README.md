# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）のリポジトリ向け README。

この README にはプロジェクト概要、主な機能、セットアップ方法、代表的な使い方（コード例）およびディレクトリ構成を日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質チェック・特徴量計算・ニュース NLP（LLM）評価・市場レジーム判定・監査ログなどを含む、バックテスト／自動売買プラットフォームのコアユーティリティ群です。

主な設計方針:
- Look-ahead バイアスを避ける（内部で現在時刻を直接参照しない処理）
- DuckDB をデータハブとして利用（ローカル & 高速クエリ）
- J-Quants API を用いたデータ取得（株価、財務、カレンダー等）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価（JSON Mode）
- 冪等性・トランザクション・リトライなど堅牢性を重視

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数/.env 管理、主要設定値の取得（J-Quants トークン、OpenAI、Slack、DB パス 等）
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む仕組み

- kabusys.data
  - jquants_client: J-Quants API 呼び出し（取得・保存・認証・リトライ・レート制御）
  - pipeline: 日次 ETL（市場カレンダー・株価・財務）の差分取得と品質チェックの統合
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - news_collector: RSS 取得と raw_news 保存（SSRF 対策、トラッキング除去）
  - audit: 監査ログ（signal_events / order_requests / executions）スキーマの初期化・DB 作成
  - stats: z-score 正規化など汎用統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを LLM で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュース LLM を合成して market_regime を算出・保存

- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー、ランク化ユーティリティ

---

## 必要条件（目安）

- Python >= 3.10（| 型注釈を使用しているため）
- パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt があればそれを利用してください）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
pip install -e .
```

---

## 環境変数（主なもの）

kabusys.config.Settings で参照する主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系で使用）

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — 環境 (development / paper_trading / live)（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで未指定時に参照）

.env の自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意: Settings._require は未設定の必須変数があると ValueError を投げます。

---

## セットアップ手順（簡易）

1. Python 環境作成（3.10+ 推奨）
2. 依存ライブラリのインストール（上記参照）
3. 環境変数設定:
   - .env / .env.local をプロジェクトルートに作成するか、OS 環境に設定
   - 必須変数を設定（JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等）
4. DuckDB 用ディレクトリ作成（設定に応じて自動で作成されますが、念の為確認）
5. 監査 DB 初期化（必要な場合）:
   - init_audit_db を使用して専用 DuckDB を作成しスキーマを作成できます

---

## 使い方（代表的なコード例）

以下は簡単な Python スクリプト例です。各関数は DuckDB 接続を受け取り動作します。

- 日次 ETL（株価・財務・カレンダーの差分取得＋品質チェック）

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（ai_scores テーブルへ書き込み）

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API は OPENAI_API_KEY を参照
print(f"書込み銘柄数: {written}")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。テーブルが作成されています。
```

- 研究用ファクター計算（calc_momentum など）

```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
print(len(records), "銘柄")
```

注意:
- AI 関連関数（score_news, score_regime）は OpenAI API キーを環境変数 OPENAI_API_KEY から取得します。api_key を引数で渡すことも可能です。
- ETL や保存関数は冪等で動作するよう設計されています（ON CONFLICT / UPDATE 等）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要ソースは `src/kabusys` 配下にあります。主なファイル/サブパッケージは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得／保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - quality.py                   — データ品質チェック
    - calendar_management.py       — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py            — RSS ニュース収集
    - audit.py                     — 監査ログスキーマ初期化（signal/order/execution）
    - etl.py                       — ETLResult の公開（再エクスポート）
    - stats.py                     — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/volatility/value）
    - feature_exploration.py       — forward returns / IC / summary / rank
  - data/ の他モジュール（calendar, pipeline 等）は上記参照

各ファイルは docstring に処理概要・設計方針・想定テーブルを明記しています。実運用では DuckDB のスキーマ（テーブル定義）を先に用意してから各 ETL/保存を実行してください。

---

## 注意点 / 運用上のヒント

- OpenAI と J-Quants API の呼び出しではリトライとバックオフ・レート制御が組み込まれていますが、API キーやトークンの管理は慎重に行ってください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から探索します。CI やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードをオフにできます。
- DuckDB への大量バルク挿入は executemany を利用しているため、空のパラメータリストを渡すと DuckDB バージョンによりエラーになる場合があります（コード内でチェック済み）。
- ニュース収集は SSRF 等に配慮した実装（リダイレクト検査・プライベートアドレス回避・受信サイズ制限等）がされています。

---

もし README に追記したい例（起動スクリプト、docker 化手順、CI 設定、実際の DB スキーマ定義など）があれば、必要な内容を教えてください。README を拡張してより具体的な運用手順を追加します。