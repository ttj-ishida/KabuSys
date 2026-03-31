KabuSys — 日本株自動売買プラットフォーム（README）
=================================================

概要
----
KabuSys は日本株向けのデータ基盤・リサーチ・AI スコアリング・監査/ETL ツール群を提供する Python パッケージです。J-Quants API を用いた株価・財務・マーケットカレンダーの ETL、RSS ニュース収集と LLM を用いたニュースセンチメント評価、ファクター計算や市場レジーム判定、監査ログ（発注→約定トレーサビリティ）の初期化等を含みます。

主な特徴
--------
- J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御、冪等保存）
- ETL パイプライン（prices / financials / market_calendar の差分取得・保存・品質チェック）
- ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去、冪等保存）
- ニュース NLP：OpenAI（gpt-4o-mini）の JSON モードを使った銘柄別センチメント算出（ai_scores へ保存）
- 市場レジーム判定：ETF（1321）200日移動平均乖離とマクロニュースセンチメントを合成
- 研究用モジュール：モメンタム／ボラティリティ／バリュー等のファクター計算、将来リターン・IC 等
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal/events/order_requests/executions）スキーマ初期化ユーティリティ（DuckDB）

セットアップ手順
----------------

前提
- Python 3.10+ を推奨（typing の union | 等を使用しているため）
- DuckDB、OpenAI SDK 等の外部ライブラリが必要

1. リポジトリをクローン（省略可）
   git clone <repo>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows

3. パッケージと依存のインストール
   pip install -e .
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / setup.cfg があるなら pip install -e . でまとまる想定です）
   必要に応じて logger 等の追加依存をインストールしてください。

4. 環境変数
   .env（または .env.local）に必要な環境変数を設定します。自動ロードは kabusys.config モジュールで .env/.env.local をプロジェクトルートから探して行われます。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（必須は明記）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - OPENAI_API_KEY — OpenAI 呼び出しで利用（score_news / score_regime は引数で上書き可能）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
   - KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト development）
   - LOG_LEVEL — "DEBUG"/"INFO"/...（デフォルト INFO）

使い方（基本例）
---------------

以下は典型的な利用例です。実行は CLI スクリプト等でラップしてください。

1) DuckDB 接続を作成して ETL を実行する
- ETL（株価 / 財務 / カレンダーの差分処理と品質チェック）

from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

2) ニュースセンチメントの算出（OpenAI API キーが環境変数にある場合は api_key を省略可能）

from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {written}")

3) 市場レジーム判定（ETF 1321 とマクロニュースを組み合わせる）

from datetime import date
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) 監査ログ DB の初期化（監査スキーマを追加）

from kabusys.config import settings
from kabusys.data.audit import init_audit_db
conn = init_audit_db(settings.duckdb_path)  # または別 DB パス

重要な API / 関数
- kabusys.data.pipeline.run_daily_etl(...) : 日次 ETL のエントリポイント
- kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl : 個別 ETL
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar : 生 API 取得
- kabusys.data.jquants_client.save_* : DuckDB への保存（冪等）
- kabusys.data.quality.run_all_checks : 品質チェック
- kabusys.ai.news_nlp.score_news : ニュース NLP スコアリング（ai_scores 書き込み）
- kabusys.ai.regime_detector.score_regime : 市場レジーム判定（market_regime 書き込み）
- kabusys.data.audit.init_audit_schema / init_audit_db : 監査テーブル初期化

設計上の注意点
--------------
- ルックアヘッドバイアス対策：内部ロジックは date.today()/datetime.today() を直接参照する操作を避け、外部から target_date を注入する設計です。バックテスト等では必ず過去データのみに基づく呼び出しを行ってください。
- OpenAI 呼び出し：API 構成は gpt-4o-mini と JSON mode を利用する想定です。API 失敗時はフェイルセーフ（多くのケースで 0.0 フォールバックやスキップ）を採用しています。
- ETL は冪等性を重視：DuckDB への保存は ON CONFLICT DO UPDATE を多用しているため、再実行での重複書込は基本的に抑制されます。
- .env 自動ロード：kabusys.config ではプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動で読み込みます。テスト等でこれを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

ディレクトリ構成（主要ファイル）
-----------------------------

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースセンチメント（OpenAI を用いる）
  - regime_detector.py           — 市場レジーム判定（ETF MA200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント + DuckDB 保存ユーティリティ
  - pipeline.py                  — ETL パイプラインと run_daily_etl エントリ
  - etl.py                       — ETL 結果型 ETLResult のエクスポート
  - quality.py                   — データ品質チェック
  - news_collector.py            — RSS ニュース収集・前処理
  - calendar_management.py       — マーケットカレンダー管理（営業日判定等）
  - stats.py                     — 汎用統計（zscore 正規化等）
  - audit.py                     — 監査ログ（テーブル作成 / init）
- research/
  - __init__.py
  - factor_research.py           — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py       — 将来リターン・IC・統計サマリー等
- monitoring/ (未表示部分あり)   — 実行プロセス監視関連（PID、リソース閾値）等
- execution/, strategy/ など      — 発注・戦略実行関連（コードベースに含まれる想定）

（上記は主要モジュールの抜粋です。実際のリポジトリでは追加ファイル・モジュールが存在する可能性があります）

よくある質問（FAQ）
-------------------
Q. OpenAI API キーはどう渡す？
A. score_news/score_regime 等の関数は api_key 引数を受け取り、None の場合は環境変数 OPENAI_API_KEY を参照します。関数呼び出し時に明示的に渡すことも可能です。

Q. J-Quants の認証は？
A. JQUANTS_REFRESH_TOKEN を設定してください。kabusys.data.jquants_client.get_id_token() で id_token を取得し、内部でキャッシュおよび自動リフレッシュを行います。

Q. DuckDB のスキーマはどこで初期化する？
A. ETL 実行前に適切なスキーマ定義（raw_prices / raw_financials / market_calendar / ai_scores 等）を作成する必要があります。audit 用スキーマは kabusys.data.audit.init_audit_schema / init_audit_db を利用して初期化できます。

貢献 / テスト
--------------
- Unit テストやモックが必要な箇所（OpenAI 呼び出しや外部ネットワーク）は、モジュール内で明示的に差し替え（unittest.mock.patch）しやすい設計になっています。
- PR の際はコード整合性・型の確認、外部 API 呼び出しを伴うテストはモック化することを推奨します。

免責
----
本リポジトリは学術的 / 研究的な目的で提供される設計実装例です。実際の自動売買での使用は自己責任で行ってください。実マーケットでの発注や資金管理に関しては慎重に設計・検証してください。

---

必要であれば、README にサンプル .env.example、SQL スキーマ定義スニペット、または具体的な ETL 実行スクリプト（cron / systemd での運用例）などを追記できます。どれを追加しますか？