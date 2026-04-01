# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（発注〜約定のトレーサビリティ）などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスに配慮（内部で datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカルデータレイク
- 外部 API 呼び出しはリトライ・レートリミット・フォールバック実装済み
- 冪等性を重視（DB 保存は ON CONFLICT / DELETE→INSERT の形で置換）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（例）
- 環境変数（.env）
- ディレクトリ構成
- よくある注意点 / トラブルシューティング

---

プロジェクト概要
----------------
KabuSys は日本株の自動売買システムを構築するための共通ライブラリ群です。主に以下の領域をカバーします。

- データ収集 / ETL（J-Quants API 経由で株価・財務・市場カレンダーを取得）
- ニュース収集・NLP（RSS → raw_news、OpenAI でセンチメントを算出）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- リサーチユーティリティ（ファクター計算、将来リターン、IC、統計要約）
- 監査ログ（signal → order_request → execution をトレースする監査用スキーマ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

機能一覧
--------
- ETL
  - run_daily_etl(): 市場カレンダー / 株価 / 財務 の差分取得と保存
  - 個別 ETL：run_prices_etl, run_financials_etl, run_calendar_etl
- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - トークン取得・自動リフレッシュ・レートリミット実装
- ニュース処理
  - fetch_rss(): RSS 取得 + SSRF 対策 + 前処理
  - score_news(): OpenAI を用いた銘柄別ニュースセンチメント算出 -> ai_scores へ保存
- 市場レジーム判定
  - score_regime(): ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成し market_regime を更新
- リサーチ
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- データ品質（quality.run_all_checks）
- カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
- 監査ログ初期化（init_audit_schema / init_audit_db）

---

セットアップ手順
----------------

前提
- Python 3.9+（typing ヒントの記述より推奨）
- ネットワーク接続（J-Quants, OpenAI への API アクセス）

1. リポジトリをクローン／展開
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際の requirements.txt があればそちらを使用してください。

4. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（kabusys.config）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB データベース初期化（監査DBなど）
   - 例: Python REPL / スクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - パスの親ディレクトリは自動作成されます。

---

環境変数（主なもの）
-------------------
以下は本プロジェクトが参照する代表的な環境変数です（.env に記載）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注系で使用）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）データベースパス（デフォルト data/monitoring.db）
- PID_FILE_PATH: 実行プロセスの PID 保存先（デフォルト data/execution.pid）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

.example（.env の簡易例）
------------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

注意: .env.example を参考に必須値を設定してください。

---

使い方（主要ワークフロー）
------------------------

※ 下記は最小限の利用例です。ログ設定やエラーハンドリングは用途に応じて追加してください。

1) 日次 ETL の実行（株価・財務・カレンダー取得と品質チェック）
Python スクリプト例:
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニューススコアリング（OpenAI を使って銘柄ごとのニューススコアを ai_scores に保存）
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")

3) 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM を合成）
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))

4) 監査 DB の初期化（発注・約定トレース用スキーマを作成）
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降、order_requests / executions 等のテーブルを利用可能

5) 研究用ユーティリティ（ファクター計算等）
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))

---

ディレクトリ構成（主要ファイル）
--------------------------------
パッケージルート: src/kabusys

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 jquants_client 関連ユーティリティ)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/, strategy/, execution/ 等（パッケージ公開予定/参照用）

各モジュールの責務：
- data/jquants_client.py: J-Quants API 通信、保存処理
- data/pipeline.py: 日次 ETL のオーケストレーション（run_daily_etl）
- data/news_collector.py: RSS 収集と前処理
- ai/news_nlp.py: ニュースを OpenAI で評価して ai_scores に保存
- ai/regime_detector.py: マクロセンチメント + ETF MA で market_regime を算出
- research/*: ファクター計算と解析用ユーティリティ
- data/audit.py: 監査ログスキーマ初期化ユーティリティ

---

実装上の重要なポイント / 注意点
--------------------------------
- .env の自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml を起点）から .env / .env.local を自動で読み込みます。
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- API 呼び出しのフェイルセーフ
  - OpenAI コールや J-Quants 呼び出しはリトライやフォールバック（失敗時は中立スコア 0.0 等）を実装しています。重大な失敗はログに記録されますが、パイプラインはできる限り継続します。

- Look-ahead バイアス対策
  - バックテストやモデル学習でのルックアヘッドを防ぐため、各モジュールは target_date 引数を受け取り、datetime.now() などの直接参照を避ける実装になっています。API を使う際は target_date を明示して扱うことを推奨します。

- DuckDB の executemany の制約
  - DuckDB バージョン差異により executemany に空パラメータが渡せない箇所があるため、該当箇所では事前に空チェックを行っています。

- セキュリティ
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml による XML パース防御などを行っています。

---

トラブルシューティング
----------------------
- OpenAI / J-Quants の認証エラー
  - 環境変数 OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN を確認してください。
  - J-Quants はリフレッシュトークンから id_token を取得します。401 が来た場合は自動でリフレッシュを試みます。

- .env が読み込まれない
  - プロジェクトルートが .git または pyproject.toml を含むディレクトリであることを確認してください。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）がセットされていないか確認。

- DuckDB への書き込みでエラーが出る
  - ファイルパスの親ディレクトリが存在するか、適切な権限があるか確認してください。
  - init_audit_db() は親ディレクトリを自動作成しますが、それ以外のケースは手動作成が必要になる場合があります。

---

貢献・拡張
----------
- 新しいニュースソースの追加: data/news_collector.py の DEFAULT_RSS_SOURCES を拡張し fetch_rss → raw_news 保存ロジックを呼ぶ
- 追加の研究メソッド: research パッケージに関数を追加してください（prices_daily / raw_financials のみ参照する設計）
- 発注・ブローカー連携: execution / strategy 層を実装し、order_requests テーブルを利用して監査トレースを確保してください

---

ライセンス / コード品質
----------------------
（この README にはライセンス情報は含まれていません。プロジェクトルートの LICENSE ファイルを確認してください。）

---

お問い合わせ
------------
問題や質問があれば、リポジトリの Issue に記載してください。README に不足がある箇所は PR での改善歓迎します。

以上。