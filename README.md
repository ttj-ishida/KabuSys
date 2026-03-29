# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、ファクター計算、監査ログ（発注・約定トレーサビリティ）などの機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避けた時刻／データ扱い（バックテスト互換）
- DuckDB を用いたローカルデータプラットフォーム
- OpenAI や J-Quants API 呼び出しはリトライ・バックオフ・レート制限を考慮
- 冪等性（ON CONFLICT / idempotent 操作）とフェイルセーフ設計

---

## 機能一覧
- データ取得 / ETL
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得（paging 対応）
  - 差分更新・バックフィル・品質チェックを備えた日次 ETL パイプライン
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存、news_symbols との紐付け
  - SSRF / Gzip bomb / トラッキングパラメータ除去等のセキュリティ対策
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini 等）を用いた銘柄別センチメント（ai_scores）算出（JSON mode / バッチ処理 / リトライ）
  - マクロニュース + ETF（1321）200 日 MA 乖離を用いた市場レジーム判定（bull / neutral / bear）
- 研究用ユーティリティ
  - モメンタム / バリュー / ボラティリティ 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計
  - Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査スキーマ・初期化ユーティリティ
  - UUID ベースのトレーサビリティ、created_at / updated_at 管理
- 設定管理
  - .env / 環境変数読み込み（プロジェクトルート自動検出、.env.local 上書き等）
  - 必須環境変数チェックとユーティリティ

---

## 要件（主な依存）
- Python 3.9+
- duckdb
- openai (OpenAI の公式クライアント)
- defusedxml
- 標準ライブラリ（urllib 等）ほか

※ 実行環境に合わせて仮想環境を作成することを推奨します。

---

## インストール手順（開発時）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発環境なら）pip install -e .

3. 環境変数ファイル (.env) を作成
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

サンプル .env:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: 必須の環境変数は実行時に Settings でチェックされます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。

---

## 設定（settings）
kabusys.config.Settings を通じて環境変数にアクセスできます。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。

主なキー:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- OPENAI_API_KEY（OpenAI 呼び出し時に明示的に渡すことも可能）

例:
from kabusys.config import settings
print(settings.duckdb_path)

---

## クイックスタート（主要な使い方の例）

前提: DuckDB 接続を作成し、settings で指定された DB パスを利用する例。

1) 日次 ETL 実行
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースセンチメントの算出（OpenAI API キーが環境変数にあるか api_key に指定）
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print(f"書き込み銘柄数: {written}")

3) 市場レジーム判定
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) 監査 DB 初期化
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます

5) 研究用ファクター計算例
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, date(2026,3,20))
v = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
# 返り値は [{"date":..., "code": "...", "mom_1m":..., ...}, ...]

---

## API の挙動に関する注意点 / 設計ノート
- Look-ahead バイアス防止:
  - モジュール内で datetime.today() / date.today() の直接参照を避け、明示的な target_date を引数に取る設計が中心です。
  - DB クエリは target_date より前のデータのみを参照するよう実装されています。
- 冪等性:
  - J-Quants データ保存は ON CONFLICT DO UPDATE を用い、再実行してもデータが重複しないようにしています。
  - News の記事 ID は正規化 URL の SHA-256 の先頭を利用して冪等性を確保します。
- セキュリティ / フェイルセーフ:
  - News RSS 取得では SSRF 対策、レスポンスサイズ制限、defusedxml を使用した XML パースを行います。
  - OpenAI / HTTP API 呼び出しはリトライ（指数バックオフ）、429/タイムアウト/5xx に対応し、致命的でない場合はフォールバックして継続します。
- レート制御:
  - J-Quants API のレート制限（120 req/min）を守るため固定間隔スロットリングを用いて制御します。
- ロギング:
  - settings.log_level によってログレベルを制御できます。各モジュールは適切なレベルでログ出力します。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py                        — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                     — ニュースセンチメント算出（OpenAI）
  - regime_detector.py              — マクロ + MA200 を合成した市場レジーム判定
- data/
  - __init__.py
  - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
  - etl.py                          — ETLResult の公開
  - jquants_client.py               — J-Quants API client + 保存関数
  - news_collector.py               — RSS 収集 / 正規化 / 保存
  - calendar_management.py          — 取引日判定・calendar バッチ更新
  - stats.py                        — 共通統計ユーティリティ
  - quality.py                      — データ品質チェック
  - audit.py                        — 監査ログスキーマ / 初期化
- research/
  - __init__.py
  - factor_research.py              — Momentum / Value / Volatility 計算
  - feature_exploration.py          — 将来リターン, IC, 統計サマリー

その他: ルートに .env / .env.local / pyproject.toml 等を想定

---

## 開発上のヒント
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは api_key を関数引数で明示的に渡せます（テスト容易性のため）。
- DuckDB の executemany は空リストを受け付けないバージョンの違いに注意（実装内でチェック済み）。
- ETL 実行はトランザクション単位で各ステップが独立しているため、部分エラーがあっても可能な限り処理を継続し、結果にエラー情報を残します（ETLResult）。

---

この README はコードベースの主要な機能と使い方の概要をまとめたものです。詳細な API 仕様やスキーマ定義、運用のベストプラクティスは各モジュールの docstring と実装を参照してください。必要ならサンプルスクリプトや追加のセットアップ手順（CI/CD、Systemd ジョブ、Dockerfile など）も作成できます。