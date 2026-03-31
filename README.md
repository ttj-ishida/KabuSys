# KabuSys

日本株向けのデータプラットフォーム／自動売買補助ライブラリです。  
DuckDB をデータ層に使い、J-Quants からのデータ ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## プロジェクト概要

KabuSys は以下を主目的とした内部ライブラリです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得（ETL）
- RSS ベースのニュース収集と前処理、LLM による銘柄別ニュースセンチメント算出
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order_request → execution）のテーブル定義・初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上、バックテストでのルックアヘッドバイアスを避けるために日付参照は明示的な引数を使う方針です。

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - jquants_client: fetch / save 関数（ページネーション・リトライ・レート制限対応）
- ニュース関連
  - RSS 取得・前処理（SSRF・サイズ・gzip 対策含む）
  - 銘柄紐付け・raw_news への保存ロジック（news_collector）
  - OpenAI によるニュースセンチメント（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF (1321) の MA200 乖離とマクロニュースの LLM スコアを混合して日次レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究（research）
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- データ品質チェック（kabusys.data.quality）
- 監査ログ（kabusys.data.audit）
  - init_audit_schema / init_audit_db: 監査用 DuckDB スキーマ初期化

---

## 必要要件

- Python 3.10 以上（PEP 604 の union 型表記などを使用）
- 主要依存（例）
  - duckdb
  - openai (OpenAI SDK)
  - defusedxml
  - （標準ライブラリ・urllib 等）
- 外部サービス
  - J-Quants API アクセス（リフレッシュトークン）
  - OpenAI API キー（ニュース NLP / レジーム判定）
  - （オプション）kabu-station API のパスワード、Slack トークン など

インストールはプロジェクトの packaging に依存しますが、開発環境では pip で個別インストールできます。例:

pip install duckdb openai defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt による管理を推奨）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - 要件ファイルがない場合:
     - pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（最低限必要なキー）
- JQUANTS_REFRESH_TOKEN=...
- OPENAI_API_KEY=...
- KABU_API_PASSWORD=...
- SLACK_BOT_TOKEN=...
- SLACK_CHANNEL_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

（.env.example を用意してプロジェクトで共有することを推奨）

---

## 主要な使い方（簡易例）

以下はいくつかの主要操作の Python スニペット例です。実行前に環境変数（OpenAI / J-Quants トークン等）を設定してください。

- DuckDB 接続を作成する

from datetime import date
import duckdb

conn = duckdb.connect(str("data/kabusys.duckdb"))  # デフォルトパスは settings.duckdb_path

- 日次 ETL を実行する（市場カレンダー / 株価 / 財務 / 品質チェック）

from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

- ニュースのセンチメントを計算して ai_scores に書き込む

from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {n_written}")

- 市場レジームをスコア計算して market_regime に保存する

from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)

- 監査ログ DB を初期化する（監査専用 DB を作る場合）

from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn を保存しておけば監査ログ操作が可能

- RSS フィードを取得する（ニュース収集の一部）

from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])

- 設定値にアクセスする

from kabusys.config import settings

print(settings.duckdb_path, settings.is_live, settings.log_level)

注意:
- score_news / score_regime は OpenAI API を呼ぶため、API キーまたは api_key 引数が必須です。未設定時は ValueError が発生します。
- ETL 関連は J-Quants リフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用（必須ではないが設定可能）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV: 開発環境 (development / paper_trading / live)
- LOG_LEVEL: ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

.env ファイルのパースは柔軟で、export プレフィックスやクォート、インラインコメントに対応します。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定の読み込みと Settings クラス
  - ai/
    - __init__.py (score_news を公開)
    - news_nlp.py
      - ニュースの LLM ベースセンチメント算出、ai_scores への書込み
    - regime_detector.py
      - ETF + マクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント (取得/保存/認証/レートリミット/リトライ)
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
      - ETLResult データクラス
    - news_collector.py
      - RSS 取得・前処理・ID 生成・セキュリティ対策（SSRF/Gzip/サイズ等）
    - calendar_management.py
      - market_calendar の管理と営業日判定ユーティリティ
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損/スパイク/重複/日付不整合）
    - audit.py
      - 監査ログ用テーブル定義・初期化（signal_events / order_requests / executions）
    - etl.py
      - ETLResult の再公開インターフェース
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム・バリュー・ボラティリティ等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数等

---

## 運用上の注意点 / ヒント

- OpenAI 呼び出しはネットワークやレートに左右されるため、score_news / score_regime はリトライとフォールバック（失敗時はスコア0）を実装しています。ログで失敗を監視してください。
- J-Quants API はレート制限 (120 req/min) を守る実装になっていますが、大量ページネーションやバッチ処理の際は注意してください。
- DuckDB executemany に空リストを渡すと問題になる箇所があるので、コード側で空チェックをしてあります（互換性対策）。
- 自動で .env を読み込む挙動はテスト時に邪魔になる場合があるため、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。
- 監査ログスキーマは冪等に作成されますが、DuckDB のトランザクション扱いに注意（init_audit_schema の transactional 引数参照）。

---

必要であれば README に追記すべき点（例: 実行例の詳細、CI/デプロイ手順、ローカルでの簡易データ初期化スクリプト、テストの実行方法など）を教えてください。README をプロジェクトのスタイルに合わせて拡張します。