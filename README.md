# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群（部分実装）。  
ETL、データ品質チェック、ニュースNLP（OpenAI 連携）、市場レジーム判定、リサーチ用ファクター計算、監査ログなどを含むモジュール群を提供します。

注意: 本リポジトリに含まれるのはライブラリ実装であり、実際の発注処理や外部サービス接続を行う場合は十分な検証と適切な資格情報管理が必要です。

## 主な機能
- 環境設定読み込み・管理
  - .env / .env.local を自動読み込み（プロジェクトルートは .git もしくは pyproject.toml を基準に探索）
  - 必須設定を明示的に取得するユーティリティ
- データ ETL（J-Quants）
  - 株価日足 / 財務データ / 市場カレンダーの差分取得（ページネーション・レート制御・リトライ対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（品質チェック統合）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue による報告）
- ニュース収集
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - raw_news / news_symbols への冪等保存を想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（gpt-4o-mini を利用、JSON Mode）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM 評価の合成）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル定義と初期化ユーティリティ
  - 監査DB（DuckDB）初期化関数（UTC タイムゾーン固定）

## 必要条件
- Python 3.10 以上（型ヒントに `|`（PEP 604）を使用）
- 推奨パッケージ（一例）
  - duckdb
  - openai
  - defusedxml

例:
pip install duckdb openai defusedxml

（パッケージは実行する機能に応じて追加してください）

## セットアップ手順

1. リポジトリを取得
   - git clone などでソースを取得します。

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクト配布時は requirements.txt / pyproject.toml を用意して pip install -e . 等を使うことを推奨します）

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成すると自動で読み込まれます（.env.local は .env の上書き）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（fetch / 保存に必要）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注関連に使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot Token（通知機能がある場合）
- SLACK_CHANNEL_ID: Slack 送信先チャネル ID

任意 / デフォルトあり
- OPENAI_API_KEY: OpenAI API キー（news_nlp, regime_detector などで使用）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / ...（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

例 .env（簡易）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

## 使い方（クイックスタート）

共通: DuckDB に接続して各関数に接続オブジェクトを渡して使用します。

基本的な例（Python）:

1) DuckDB 接続を作る
from kabusys.config import settings
import duckdb
conn = duckdb.connect(str(settings.duckdb_path))

2) 監査DBの初期化（別 DB に監査ログを作る場合）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db(":memory:")  # ":memory:" でインメモリ DB

3) 日次 ETL を実行する（J-Quants データ取得 → 保存 → 品質チェック）
from kabusys.data.pipeline import run_daily_etl
from datetime import date
result = run_daily_etl(conn, target_date=date.today(), id_token=None)
# result は ETLResult オブジェクト（fetched/saved や quality_issues, errors を確認）

4) ニュース NLP（銘柄別センチメント）を実行する
from kabusys.ai.news_nlp import score_news
from datetime import date
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
# api_key を省略すると OPENAI_API_KEY が使用されます

5) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

注意点:
- OpenAI を使う機能は API キーが必要です。api_key を関数引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- run_daily_etl は内部でカレンダーを取得し、対象日を営業日に調整してから株価・財務 ETL を行います。
- ETL や NLP の処理は外部 API を呼ぶため、レート制限やエラーに注意してください。実装はリトライ・フォールバックの処理を備えていますが、実運用では十分な監視とエラーハンドリングを行ってください。

## 主な公開 API（抜粋）
- kabusys.config.settings: 環境設定オブジェクト（settings.jquants_refresh_token, settings.duckdb_path など）
- kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
- kabusys.data.pipeline.ETLResult: ETL 実行結果データクラス
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / save_*（J-Quants 連携）
- kabusys.data.quality.run_all_checks(conn, ...)
- kabusys.data.audit.init_audit_db / init_audit_schema
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research.*: calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize

## ディレクトリ構成（主なファイル）
src/kabusys/
- __init__.py
- config.py                   -- 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py               -- ニュース NLP（銘柄センチメント算出）
  - regime_detector.py        -- 市場レジーム判定（MA200 + LLM）
- data/
  - __init__.py
  - calendar_management.py    -- 市場カレンダー管理（営業日判定等）
  - etl.py                    -- ETL インターフェース再エクスポート
  - pipeline.py               -- 日次 ETL パイプライン / 個別 ETL ジョブ
  - stats.py                  -- 統計ユーティリティ（zscore_normalize 等）
  - quality.py                -- データ品質チェック
  - audit.py                  -- 監査ログスキーマ定義・初期化
  - jquants_client.py         -- J-Quants API クライアント（取得・保存）
  - news_collector.py         -- RSS ニュース収集
- research/
  - __init__.py
  - factor_research.py        -- ファクター計算（Momentum / Value / Volatility）
  - feature_exploration.py    -- 将来リターン、IC、統計サマリー等
- (strategy/, execution/, monitoring/)  -- __all__ に名前はあるが実装はこの配下にないか別途

## 開発者向けメモ
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の呼び出しは内部でリトライ・タイムアウト・レスポンス検証を行います。テスト時は各モジュールの _call_openai_api をモックして呼び出しを差し替えられるように設計されています。
- DuckDB への executemany に対する互換性（空リスト不可など）を考慮した実装になっています。
- 全ての時刻は可能な限り UTC に統一して保存しています（監査ログなどでは SET TimeZone='UTC' を実行）。

## ライセンス / 責任
この README は実装の概要を示すものであり、実運用環境での安全性・法令・金融規制・実際の発注ロジックについての保証は行いません。実際に売買や公開 API を使う場合はご自身の責任で十分な検証、監査、セキュリティ対策を行ってください。

---

必要であれば、README にサンプル .env.example の完全なテンプレートや、各機能（ETL・NLP・レジーム判定）のより詳細なコード例・設定例を追加できます。どの部分を詳細化しますか？