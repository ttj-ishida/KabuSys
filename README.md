# KabuSys

日本株のデータプラットフォームと自動売買（バックオフィス含む）を支援するライブラリ群です。  
本リポジトリは、J-Quants / JPX からのデータ取得（ETL）、ニュースの収集・AIによるセンチメント評価、ファクター計算、監査ログ（トレーサビリティ）、市場カレンダー管理などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの差分取得と DuckDB への冪等保存（ETL）
- RSS ニュース収集と銘柄紐付け
- OpenAI を用いたニュースセンチメント / マクロセンチメント評価（gpt-4o-mini を想定）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- 市場カレンダー管理（JPX）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の方針として、バックテストや運用におけるルックアヘッドバイアス回避、API リトライ・バックオフ、冪等性・トレーサビリティを重視しています。

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch / save 関数群
- ニュース処理
  - RSS 収集（kabusys.data.news_collector）
  - ニュース -> 銘柄マッピング、raw_news 保存
- AI スコアリング
  - 銘柄別ニュースセンチメント: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（MA200 + マクロニュース）: kabusys.ai.regime_detector.score_regime
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility）: kabusys.research
  - 将来リターン / IC / 統計サマリー等
- データ品質チェック
  - 欠損 / スパイク / 重複 / 日付不整合（kabusys.data.quality）
- 監査ログ（audit）
  - init_audit_db / init_audit_schema（kabusys.data.audit）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / get_trading_days / calendar_update_job

---

## 前提 / 依存

主な依存（例）

- Python 3.9+
- duckdb
- openai
- defusedxml

実行環境に合わせて requirements.txt を用意してください。最低限必要なパッケージは上記です。

---

## 環境変数（.env）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読込されます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で利用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

例（`.env`）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（例）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - （開発時） pip install -e .

   requirements.txt の例:
   - duckdb
   - openai
   - defusedxml

4. .env を作成し必要な環境変数を設定

5. DuckDB 用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 初期化 / データベース

- 監査ログ専用 DB の初期化（DuckDB）:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

- 既存接続へ監査スキーマを追加:
  from kabusys.data.audit import init_audit_schema
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

注意: init_audit_schema は内部で SET TimeZone='UTC' を実行します。

---

## 使い方（代表的な例）

共通: DuckDB 接続
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

1) 日次 ETL 実行
from kabusys.data.pipeline import run_daily_etl
from datetime import date
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())  # ETL の結果サマリ

2) ニュースセンチメント（AI）
from kabusys.ai.news_nlp import score_news
from datetime import date
n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key を省略すると OPENAI_API_KEY を参照
print(f"書き込み銘柄数: {n}")

3) 市場レジーム判定（AI）
from kabusys.ai.regime_detector import score_regime
from datetime import date
r = score_regime(conn, target_date=date(2026,3,20), api_key=None)
print("OK" if r == 1 else "NG")

4) ファクター計算（研究用）
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
mom = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
val = calc_value(conn, date(2026,3,20))

5) データ品質チェック
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for issue in issues:
    print(issue)

6) カレンダー更新バッチ
from kabusys.data.calendar_management import calendar_update_job
calendar_update_job(conn)

テスト・モック:
- OpenAI への実際の呼び出しはモジュール内の _call_openai_api を unittest.mock.patch で差し替え可能です（news_nlp / regime_detector）。
- news_collector の HTTP レイヤーは _urlopen をモック可能です。

---

## 実運用上の注意

- OpenAI 呼び出しには料金がかかるためキーと利用量に注意してください。
- J-Quants API のレート制限（デフォルト 120 req/min）を尊重していますが、大量取得や並列処理時は注意してください。
- 環境設定（KABUSYS_ENV）に応じて live/paper_trading/development を切り替えて下さい。is_live / is_paper / is_dev が設定を参照します。
- 自動 .env 読み込みはプロジェクトルート（.git か pyproject.toml があるディレクトリ）を基準に実行されます。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョン（例: 0.10）の挙動を考慮した実装になっています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数・設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースセンチメント（OpenAI）
    - regime_detector.py  -- マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   -- J-Quants API クライアント（fetch / save）
    - pipeline.py         -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py   -- RSS 収集・前処理
    - calendar_management.py -- 市場カレンダー管理
    - quality.py          -- データ品質チェック
    - audit.py            -- 監査ログテーブル定義・初期化
    - etl.py              -- ETLResult エクスポート
    - stats.py            -- 共通統計ユーティリティ（zscore 正規化）
  - research/
    - __init__.py
    - factor_research.py  -- モメンタム / バリュー / ボラティリティ
    - feature_exploration.py -- forward returns / IC / summary / rank
  - ai, research, data 以外に strategy / execution / monitoring 用の名前空間を想定（__all__ に含まれますが、一部は未掲載）

（上記は主要モジュールの抜粋です。実際のリポジトリではさらにファイルが含まれる可能性があります。）

---

## テストとモックポイント

- OpenAI 呼び出し:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
  これらを patch してテストできます。

- news_collector の HTTP:
  - kabusys.data.news_collector._urlopen をモックしてネットワーク依存を排除可能。

- jquants_client の HTTP 層は urllib を用いておりリトライロジックが組まれています。get_id_token のリフレッシュロジックもテスト可能です。

---

## ライセンス / コントリビューション

（ここにライセンスやコントリビュート方法を記載してください）

---

この README はコード内ドキュメント（docstring）をもとに作成しています。実運用時は secrets の管理、API キーやトークンの権限・ローテーション、テスト環境と本番環境の分離（KABUSYS_ENV）を必ず徹底してください。