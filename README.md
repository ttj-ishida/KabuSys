# KabuSys

日本株向けの自動売買 / データプラットフォーム コンポーネント群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のような機能を持つモジュール群です。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL（rate-limit / retry / id_token 自動更新対応）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄別）およびマクロセンチメントと MA を合成した市場レジーム判定
- 研究向けファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 環境設定管理（.env の自動ロード / 保護）

設計方針としては「ルックアヘッドバイアス防止」「冪等性（idempotency）」「外部 API 呼び出しの堅牢化（リトライ / バックオフ）」を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / id token リフレッシュ・レート制御）
  - market_calendar 管理（営業日判定、next/prev trading day）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - audit テーブル初期化（監査ログスキーマ & index）
  - ニュース収集（RSS → raw_news, news_symbols 連携）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date[, api_key]) — ニュースセンチメントを ai_scores へ書き込み
  - regime_detector.score_regime(conn, target_date[, api_key]) — MA とマクロセンチメントを合成し market_regime を更新
- research/
  - factor 計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）
  - 環境変数アクセス用 settings オブジェクト（必須値は取得時にエラー）

---

## 必要要件（概略）

- Python 3.10+
- 主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリで対応しているが、環境に応じて追加パッケージが必要になる場合があります

※ 実行環境に合わせて requirements.txt を整備してください。

---

## セットアップ手順

1. リポジトリをクローン／展開する。

2. 仮想環境を作成して有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）:
   - pip install duckdb openai defusedxml

4. 環境変数設定:
   - プロジェクトルートに `.env` と `.env.local`（任意）を置けます。
   - 自動ロード: config.py はプロジェクトルート（.git または pyproject.toml）から `.env` → `.env.local` の順で自動ロードします。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

5. 必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - （任意）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite モニタリング DB パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

6. データベースディレクトリの準備（必要に応じて）:
   - settings.duckdb_path の親ディレクトリを作成してください（init 関数は親ディレクトリを自動作成する箇所もありますが、環境により注意）。

---

## 使い方（簡易例）

下記はモジュール API を直接使う簡単な例です。実運用ではログ設定や例外処理・ジョブスケジューラ等を組み合わせてください。

- DuckDB 接続と ETL 実行（日次 ETL）:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（settings.duckdb_path は Path オブジェクト）
conn = duckdb.connect(str(settings.duckdb_path))

# ETL 実行（target_date を省略すると今日が使われます）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーが環境変数に設定されていること）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査専用 DB を作る場合）:

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.sqlite_path など別 DB を指定しても可
conn = init_audit_db(settings.duckdb_path)  # ":memory:" も指定可能
```

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス対策:
  - internal code は datetime.today() / date.today() を安易に参照しない設計（関数は target_date を明示的に受け取る）。
  - ETL やスコアリングは target_date に対して過去データだけを参照するように実装されています。

- 冪等性:
  - J-Quants から取得したデータは DuckDB へ ON CONFLICT DO UPDATE で保存されます（save_* 関数）。
  - ETL は差分更新を基本とし、backfill 日数で直近の修正を取り込みます。

- API 呼び出しの堅牢化:
  - J-Quants クライアントはレートリミット（120 req/min）と指数バックオフ・401 リフレッシュを実装。
  - OpenAI 呼び出しはリトライとフォールバック（失敗時は 0.0 のスコア等）を行う設計。

- セキュリティ / 安全対策:
  - RSS フィード取得は SSRF 対策（リダイレクト検査、プライベート IP 除外）、受信サイズ制限、defusedxml を使用。
  - .env の自動ロードはプロジェクトルート検出に基づきます。テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を利用。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー / 営業日判定 / calendar_update_job
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - jquants_client.py — J-Quants API クライアント（fetch/save/get_id_token）
    - news_collector.py — RSS 収集・前処理
    - quality.py — データ品質チェック
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- OPENAI_API_KEY（score_news / score_regime 実行時に必要）

任意（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO

自動 .env 読み込みを無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 開発 / テストに関するヒント

- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使い、テスト用の環境変数注入を明示的に行うと安定します。
- OpenAI や J-Quants 呼び出しは外部依存のため、unit tests ではモック（unittest.mock.patch）する設計を想定しています（実装内に差し替えポイントがあります）。
- DuckDB の executemany は空リストを受け付けないケースがあるため、コード内で空チェックがされています。テストでもこの特性を意識してください。

---

もし README に追記したい実行例（systemd / cron ジョブ例、CI ワークフロー、より詳細な .env.example、requirements.txt など）があればお知らせください。README を用途に合わせて拡張します。