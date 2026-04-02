# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
DuckDB をデータレイクとして使用し、J-Quants からのデータ取得（ETL）、ニュース収集／NLP による銘柄別スコアリング、研究用ファクター計算、監査ログ（発注トレーサビリティ）などのユーティリティを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（datetime.today()/date.today() の盲目的な使用を避ける）
- DuckDB 上での idempotent（冪等）な保存
- 外部 API 呼び出しは再試行・バックオフ・フェイルセーフを実装
- テストしやすくモジュール分離を重視

バージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートの検出）
  - 必須環境変数の明示的チェック（settings オブジェクト）

- データ ETL（J-Quants）
  - 株価日足（raw_prices / prices_daily）
  - 財務データ（raw_financials）
  - JPX マーケットカレンダー（market_calendar）
  - 差分更新・ページネーション・トークン自動更新・レート制御・リトライ実装

- データ品質チェック
  - 欠損（OHLC）
  - スパイク（前日比）
  - 重複（主キー）
  - 日付不整合（将来日付／非営業日）

- ニュース収集と NLP
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、正規化）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（銘柄別 ai_score）集計
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）

- 研究用ユーティリティ
  - ファクター計算（モメンタム/バリュー/ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（Audit / Traceability）
  - signal_events, order_requests, executions テーブル定義・初期化
  - 監査DB初期化ユーティリティ（DuckDB）

---

## 前提・必要環境

- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

（パッケージ管理はプロジェクトの requirements.txt / pyproject.toml に合わせてください）

例:
pip install duckdb openai defusedxml

---

## 環境変数（主なもの）

以下は settings（kabusys.config.Settings）で参照される主要環境変数です。必須項目は README の例を参照して .env に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行/発注関連）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 送信先チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 使用時）

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml）を起点に .env / .env.local を自動読み込みします。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo>

2. Python 仮想環境作成と有効化（例）
   python -m venv .venv
   source .venv/bin/activate

3. 必要パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを使ってください）

4. 環境変数を用意
   プロジェクトルートに `.env`（または `.env.local`）を作成し、上記の必須値を設定してください。
   例（.env）:
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=yourpassword
   DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB 用ディレクトリ作成（必要に応じて）
   mkdir -p data

---

## 使い方（代表的な例）

以下は基本的な Python からの利用例です。すべての API はライブラリのインポートで直接呼べます。

1) DuckDB 接続を作って日次 ETL を実行する

from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニューススコアリング（OpenAI が必要）

from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")

3) 市場レジーム判定

from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))

4) 監査ログ DB の初期化（発注トレース用）

from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます

5) RSS フィード取得（ニュース収集モジュール）

from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])

（注）news_collector は SSRF 対策・レスポンスサイズ制限・XML パース例外処理などを備えています。

---

## 主要モジュール（抜粋と用途）

- kabusys.config
  - settings: 環境変数の取得と検証 (.env 自動読み込み含む)

- kabusys.data
  - pipeline: run_daily_etl 等、ETL のエントリポイントとヘルパー
  - jquants_client: J-Quants API 取得 & DuckDB 保存ロジック（ページネーション・レート制御・トークン自動更新）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得・正規化・前処理
  - calendar_management: 市場カレンダーの判定/更新ロジック
  - audit: 監査ログスキーマ初期化ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp: 銘柄ごとのニュースセンチメントスコア付与（OpenAI 呼び出しのバッチ化・バリデーション）
  - regime_detector: ETF 1321 の MA とマクロニュースを合成した市場レジーム判定

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成

以下はソースツリーの抜粋（主要ファイルのみ）。トップは src/kabusys 以下です。

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - pipeline.py
  - etl.py
  - jquants_client.py
  - quality.py
  - stats.py
  - news_collector.py
  - calendar_management.py
  - audit.py
  - etl.py (再エクスポート/インターフェース)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- researchパッケージおよび他のサブモジュール群...

（実際のリポジトリにはさらにモジュールやテストが含まれる可能性があります）

---

## 実装上の注意点 / 運用メモ

- Look-ahead Bias を避けるため、各アルゴリズムは明示的な target_date を受け取り、内部で現在時刻を乱用しない実装になっています。バッチ処理やバックテストでは target_date を明示的に与えてください。
- J-Quants / OpenAI の API 呼び出しは失敗時にリトライやフェイルセーフ（0.0 で代替）を行うため、部分的に失敗しても他の処理は継続します。ログを確認して対応してください。
- DuckDB の executemany に空リストを渡すと例外になるバージョンがあるため、保存処理では事前に空チェックを行っています。
- audit.init_audit_schema の transactional オプションは DuckDB のトランザクション挙動に注意して使用してください（ネストトランザクション不可）。

---

## 追加情報・お問い合わせ

- 各モジュールの詳細はソースコード中の docstring に設計方針・処理フローが記載されています。まずはそちらを参照してください。
- README の内容や環境設定で不明点があれば、プロジェクト管理者・リポジトリの issue にて問い合わせてください。

以上。README の改善点・追加したいセクションがあれば教えてください。