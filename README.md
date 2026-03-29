KabuSys — 日本株自動売買プラットフォーム（README）
概要
本リポジトリは「KabuSys」と呼ばれる日本株向けの自動売買 / データ基盤ライブラリ群です。
主に以下の責務を持つモジュール群を収録しています：
- データ収集・ETL（J-Quants API 連携、RSS ニュース収集、マーケットカレンダー）
- データ品質チェック・カレンダー管理
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 研究用ファクター計算・特徴量探索
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント付与）
- 市場レジーム判定（MA200 とマクロニュースの LLM 評価を合成）

設計方針（抜粋）
- ルックアヘッドバイアスに配慮（内部処理で datetime.today() を直接参照しない）
- DuckDB をローカル DB として利用（冪等保存・トランザクション制御）
- 外部 API 呼び出しにはリトライ・レート制御（J-Quants / OpenAI）
- ETL・品質チェックは Fail-Fast ではなく問題を収集して呼び出し元に通知
- セキュリティ考慮（RSS の SSRF 対策、XML パースの安全化）

主な機能一覧
- data
  - jquants_client: J-Quants API からのデータ取得（株価/財務/カレンダー）と DuckDB への保存（冪等）
  - pipeline: 日次 ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - calendar_management: 取引日判定・next/prev_trading_day・calendar_update_job
  - news_collector: RSS 取得・正規化・raw_news への保存（SSRF 対策・XML 安全化）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログテーブルの初期化 / audit DB 管理（signal_events / order_requests / executions）
  - stats: zscore_normalize 等の統計ユーティリティ
- ai
  - news_nlp.score_news: ニュースを LLM で評価し ai_scores に書き込む
  - regime_detector.score_regime: MA200 とマクロニュース（LLM）を合成して market_regime に保存
- research
  - factor_research: モメンタム/バリュー/ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン計算・IC 計算・要約統計など

セットアップ手順
前提
- Python 3.10 以上（typing の union 表記や新版機能を利用）
- DuckDB（Python パッケージ）、openai（OpenAI Python SDK）、defusedxml などが必要

インストール（開発環境想定）
1. 仮想環境作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. パッケージのインストール（requirements.txt または手動）
   pip install duckdb openai defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt を用意している想定です。
   pip install -e . でローカル開発インストールができる場合があります。

環境変数（主なもの）
このライブラリは .env / .env.local（プロジェクトルート）または環境変数から設定を読み込みます（自動ロード）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須（使用する機能に応じて）
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（jquants_client.get_id_token で使用）
- OPENAI_API_KEY         — OpenAI API キー（AI モジュール使用時）
- KABU_API_PASSWORD      — kabu ステーション連携パスワード（発注系を使う場合）
- SLACK_BOT_TOKEN        — Slack 通知を使う場合
- SLACK_CHANNEL_ID       — Slack 通知先チャンネルID

任意（デフォルト値あり）
- KABUSYS_ENV (development|paper_trading|live) — 環境（デフォルト development）
- LOG_LEVEL (DEBUG|INFO|...) — ログレベル（デフォルト INFO）
- KABUS_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）

例（.env）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（代表的な利用例）
以下は Python REPL / スクリプトからの呼び出し例です。

1) DuckDB 接続を作る
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

settings.duckdb_path は Path オブジェクトを返すため、str() を渡すか、直接 Path を渡してください。

2) 日次 ETL を実行する
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())

3) ニュースセンチメント付与（LLM を使用）
from kabusys.ai.news_nlp import score_news
from datetime import date
# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026,3,20))
print(f"written: {n_written} codes")

4) 市場レジーム判定（MA200 とマクロニュースを合成）
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026,3,20))

5) 監査ログ DB を初期化する（独立した監査 DB を作る場合）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます

6) 研究系ユーティリティ（ファクター算出等）
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))

注意事項
- OpenAI 呼び出しは API コストがかかります。テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替える設計になっています。
- J-Quants / kabu API は実アカウントの資格情報が必要です。API 呼び出しはレート制限・リトライロジックに従いますが、適切なトークン管理を行ってください。
- run_daily_etl などは DB スキーマ（raw_prices, raw_financials, market_calendar 等）が存在することを前提とします。スキーマ初期化は別途スクリプト（本 README に含まれない）で行うか、DuckDB に適切なテーブル DDL を投入してください。

ディレクトリ構成（主要ファイル / モジュール）
src/
  kabusys/
    __init__.py                -- パッケージエントリ（__version__ 等）
    config.py                  -- 環境変数 / 設定管理
    ai/
      __init__.py
      news_nlp.py              -- ニュースセンチメント付与（score_news）
      regime_detector.py       -- 市場レジーム判定（score_regime）
    data/
      __init__.py
      calendar_management.py   -- カレンダー管理 / trading day ヘルパー
      etl.py                   -- ETL 公開インタフェース（ETLResult）
      pipeline.py              -- ETL パイプライン（run_daily_etl 等）
      stats.py                 -- 統計ユーティリティ（zscore_normalize）
      quality.py               -- データ品質チェック
      audit.py                 -- 監査ログスキーマ初期化 / init_audit_db
      jquants_client.py        -- J-Quants API クライアント + 保存ロジック
      news_collector.py        -- RSS ニュース収集 / 前処理
    research/
      __init__.py
      factor_research.py       -- momentum/value/volatility 等
      feature_exploration.py   -- forward returns, IC, summary
    research/（他モジュール含む）

開発・テストについて
- 外部 API を呼ぶ処理（OpenAI / J-Quants / RSS 取得）はモック可能な設計になっています。単体テストでは _call_openai_api や kabusys.data.news_collector._urlopen、jquants_client._request などをモックして外部依存を切ることを推奨します。
- 自動環境変数読み込みはプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読みます。テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

貢献・ライセンス
- この README はコードベースの概要・利用例をまとめたものです。詳細な開発ルール、ISSUE/PR の方針、ライセンス表記はリポジトリのトップレベルに別途配置してください。

補足（よくある質問）
- Q: DuckDB スキーマはどこで定義されていますか？
  A: ETL / 保存関数（jquants_client.save_* 等）は既定のテーブル構造を期待します。初回セットアップ時は別途 DDL を実行してテーブルを作成してください（本コードには一部モジュールで init_audit_schema を提供）。

- Q: OpenAI の JSON Mode を前提としたレスポンス取り扱いですが壊れた場合は？
  A: LLM レスポンスのパース失敗時はロギングしてスコアを 0.0 にフォールバックするなどフェイルセーフを備えています。実運用ではリトライ / モデル変更 / プロンプト調整が必要です。

以上。利用上の具体的なコマンドやスキーマ初期化スクリプトが必要であれば、目的（ETL 実行 / 監査 DB 初期化 / ニュース収集 など）を教えてください。必要に応じてサンプルスクリプトを作成します。