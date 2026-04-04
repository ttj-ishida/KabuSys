# KabuSys

日本株向けのデータプラットフォーム & 自動売買支援ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、ファクター算出、監査ログ（発注/約定トレーサビリティ）等を含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（date や datetime.now() を安易に参照しない）
- DuckDB を中心としたローカル DB 管理（冪等保存 / ON CONFLICT）
- 外部 API（J-Quants / OpenAI）呼び出しはリトライ・レートリミット対応
- フェイルセーフ：API 失敗時は継続できる設計（例: LLM 呼び出し失敗でスコアを 0 にフォールバック）

---

目次
- プロジェクト概要
- 機能一覧
- 必要条件 / 依存関係
- セットアップ手順
- 環境変数 (.env) の設定
- 使い方（簡単なコード例）
- ディレクトリ構成（主要ファイル一覧）
- 補足（自動 .env ロードなど）

---

## プロジェクト概要

KabuSys は日本株データの取得・品質チェック・特徴量作成・ニュース NLP・市場レジーム判定・監査ログ設計などを行うための内部用ライブラリ群です。ETL とデータ品質検査を行い、研究用途（ファクター探索）や自動売買戦略の支援に使えるユーティリティをまとめています。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得（pagination 対応、レート制御・リトライ内蔵）
  - run_daily_etl による日次 ETL パイプライン（カレンダー取得 → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェック
- ニュース収集
  - RSS 取得（SSRF 対策、URL 正規化、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存ロジック
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメントスコアを ai_scores に書き込む（score_news）
  - マクロニュース + ETF（1321）の 200 日 MA 乖離を組み合わせた市場レジーム判定（score_regime）
  - LLM 呼び出しは JSON mode を想定、再試行ロジックを実装
- 研究（research）
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Z スコア正規化
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを用いたトレーサビリティ設計
  - init_audit_db / init_audit_schema によるテーブル初期化
- その他ユーティリティ
  - カレンダー管理（営業日判定 / next/prev trading day など）
  - DuckDB 保存・読み出しユーティリティ
  - 環境変数読み込み（.env, .env.local 自動ロード機能）

---

## 必要条件 / 依存関係

- Python 3.10+
  - 型ヒントで `X | None` を用いているため Python 3.10 以上を推奨
- 主な Python パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで多くの処理を行いますが、上記ライブラリは必須です。

（プロジェクトに requirements.txt があればそれを利用してください）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクトを編集可能モードでインストールする場合）
     - pip install -e .

4. 環境変数設定（.env を作成、後述参照）

---

## 環境変数 (.env)

config.Settings で参照される主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD（必須）: kabu ステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など監視設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV: development / paper_trading / live（有効値）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して .env/.env.local を自動で読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパースは export KEY=val, クォートやコメント行等に対応しています。

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトから実行する例です。適宜 logging を設定してください。

1) DuckDB に接続して日次 ETL を実行（J-Quants トークンが設定されている前提）:
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースセンチメント（score_news）を実行（OpenAI API キーが必要）:
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None → 環境変数 OPENAI_API_KEY を参照
print(f"written scores: {written}")

3) 市場レジーム判定（score_regime）:
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

4) 監査 DB 初期化（監査用 DuckDB を新規作成）:
from kabusys.data.audit import init_audit_db

conn_audit = init_audit_db("data/audit.duckdb")
# 以後 conn_audit を使って監査ログを書き込めます

5) カレンダー更新ジョブを手動実行:
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect(str(settings.duckdb_path))
saved = calendar_update_job(conn)
print("saved calendar records:", saved)

注記:
- score_news / score_regime のような LLM を呼ぶ関数は OPENAI_API_KEY を必要とします。api_key を明示的に渡すことも可能です。
- run_daily_etl は内部で calendar ETL → prices ETL → financials ETL → 品質チェックを順に実行します。個別関数も公開されています（run_prices_etl, run_financials_etl, run_calendar_etl）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数/設定管理、.env 自動読み込み
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント（OpenAI）関連
  - regime_detector.py  — マクロ + ETF を用いる市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント（取得・保存機能）
  - pipeline.py            — ETL パイプライン / run_daily_etl
  - etl.py                 — ETLResult の再エクスポート
  - calendar_management.py — マーケットカレンダー管理（営業日判定等）
  - news_collector.py      — RSS 収集・前処理
  - quality.py             — データ品質チェック
  - stats.py               — 共通統計ユーティリティ（zscore_normalize）
  - audit.py               — 監査ログテーブル作成・初期化
- research/
  - __init__.py
  - factor_research.py     — モメンタム/バリュー/ボラティリティ ファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

この README の記載は上記ソースコードに基づきます。各モジュールの docstring に詳細な設計方針や注意点（ルックアヘッド防止、トランザクション処理、リトライ等）が記載されていますので、実装時はそちらも参照してください。

---

## 補足 / 注意点

- Python バージョン: 本コードは Python 3.10 以上を前提としています（型アノテーションに | を使用）。
- OpenAI 呼び出し:
  - news_nlp / regime_detector は gpt-4o-mini を想定し、JSON mode を利用する設計です。API のレスポンス形式に厳密に依存するため、SDK バージョンやモデルの挙動に合わせて調整してください。
  - LLM 呼び出しが失敗した場合はスコアを 0 にフォールバックする等、フェイルセーフが組まれていますが、運用時にはレート制御やコストに注意してください。
- J-Quants:
  - get_id_token / fetch_* 関数は rate limit（120 req/min）や 401 リフレッシュを考慮しています。API キー（JQUANTS_REFRESH_TOKEN）を必ず設定してください。
- データ保存:
  - DuckDB に対する保存は冪等に行われます（ON CONFLICT DO UPDATE）。監査ログは削除しない前提です。
- ローカルの .env, .env.local の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存します。CI やテストで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要であれば、README に含めるコマンド例（systemd unit / crontab / 実運用向けの注意）や、CI 用のテスト手順、requirements.txt の候補等も作成します。どの部分を優先的に詳述しましょうか？