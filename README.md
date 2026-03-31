# KabuSys

KabuSys は日本株向けのデータプラットフォームと自動売買（リサーチ・戦略・監査）ユーティリティ群を提供する Python パッケージです。J-Quants からのデータ取得・ETL、ニュースの収集と LLM によるニュース評価、ファクター計算、マーケットカレンダー管理、監査ログテーブルの初期化などを含みます。

バージョン: 0.1.0

---

## 主要機能（概要）

- データ取得 / ETL
  - J-Quants API 経由で株価日足、財務データ、マーケットカレンダーを差分取得・保存（DuckDB）
  - 差分取得・バックフィル・ページネーション・トークン自動リフレッシュ、レートリミット対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（quality モジュール）
- ニュース収集・NLP
  - RSS からニュースを収集し raw_news に保存（SSRF 対策、URL 正規化）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア算出（news_nlp.score_news）
- 市場レジーム判定
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（regime_detector.score_regime）
- 研究・ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター算出（research パッケージ）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル DDL、初期化ユーティリティ（data.audit）
- 設定管理
  - .env ファイルおよび OS 環境変数からの自動ロード、アプリ設定へのアクセス（kabusys.config）

---

## 必要条件 / 依存ライブラリ（主なもの）

- Python >= 3.10
- duckdb
- openai（OpenAI の Python SDK、Chat Completions を利用）
- defusedxml
- （標準ライブラリ: urllib, json, datetime 等）

インストール例（最小）:
pip install duckdb openai defusedxml

プロジェクトを editable インストールする場合:
python -m pip install -e .

（requirements.txt を用意している場合はそれを使用してください）

---

## 環境変数（主なもの）

以下の環境変数/キーがコード内で参照されます。必須のものは README 内に明記します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client.get_id_token に利用）
- SLACK_BOT_TOKEN — Slack 通知（必要な場合）
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- KABU_API_PASSWORD — kabu API（kabuステーション）パスワード

オプション（デフォルト値あり）:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト "development"）
- LOG_LEVEL — ログレベル ("DEBUG","INFO"...)
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring 用)（デフォルト: data/monitoring.db）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

.env の自動読み込み:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して、`.env` → `.env.local` の順に読み込みます（OS 環境変数が優先、`.env.local` は上書き）。
- 自動読み込みを無効にしたいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡単な .env 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install -e .             # パッケージを開発モードでインストール
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、OS 環境変数を設定します（上記参照）。

5. DuckDB ファイルの保存先ディレクトリを作成
   mkdir -p data

---

## 使い方（主要なユースケースの例）

以下は簡単な Python スクリプト例です。適宜ログ設定や例外処理を追加してください。

- DuckDB 接続を作る例:
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

- ETL（日次パイプライン）を実行する:
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

- ニュースの NLP スコアを生成（OpenAI API 必須）:
from kabusys.ai.news_nlp import score_news
from datetime import date

# conn は DuckDB 接続
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} symbols")

- 市場レジーム判定:
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB を初期化して接続を取得:
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます

- 研究系ユーティリティの使用例:
from kabusys.research import calc_momentum, calc_volatility
from datetime import date
moms = calc_momentum(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))

注意点:
- score_news / score_regime は OpenAI API（Chat Completions）を利用します。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- DuckDB の接続は文字列パスを渡す形が確実です（str(settings.duckdb_path)）。

---

## ログ・デバッグ

- 設定: LOG_LEVEL 環境変数でログレベルを指定できます（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- デフォルトは INFO。

---

## モジュール・ディレクトリ構成

以下は主要ファイル / モジュールの一覧（src/kabusys 以下）。README 用に簡潔に説明します。

- kabusys/
  - __init__.py — パッケージ初期化（__version__ 等）
  - config.py — .env 自動ロード、Settings クラス（環境変数の取得と検証）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM ベースの銘柄センチメント評価（score_news）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュースの LLM スコア合成）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - news_collector.py — RSS 収集・前処理・raw_news 保存
    - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
    - audit.py — 監査ログ（DDL・初期化・init_audit_db）
    - stats.py — zscore_normalize などの統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

---

## 注意事項 / 設計方針のポイント

- Look-ahead バイアス対策:
  - 関数は内部で date.today() を無闇に参照しない等、バックテスト時の情報漏洩を抑制する設計になっています。必ず target_date を明示してください。
- 冪等性:
  - J-Quants の保存関数や監査テーブル初期化は冪等に動くよう設計されています（ON CONFLICT 等）。
- フェイルセーフ:
  - LLM 呼び出しや外部 API の失敗は基本的に例外で全体処理を止めず、フォールバック値を使って継続することが多いです（ログに WARN）。
- セキュリティ:
  - news_collector は SSRF 対策、XML bombing 対策（defusedxml）、応答サイズ制限などを導入しています。

---

## 貢献 / テスト

- 新機能やバグ修正は PR をお願いします。
- ユニットテストでは外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックすることを推奨します（module 内で _call_openai_api や _urlopen を差し替えられる設計がされています）。

---

この README はコードベースの主要部分を簡潔にまとめたものです。詳細は各モジュールの docstring とソースを参照してください。必要であればサンプルスクリプトや requirements.txt、.env.example を用意しますので教えてください。