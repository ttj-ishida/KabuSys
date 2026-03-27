# KabuSys

日本株向けのデータプラットフォーム兼自動売買（バックテスト / 研究 / 実行支援）ライブラリです。  
DuckDB をデータレイヤに用い、J-Quants API からの ETL、ニュース収集・NLP、ファクター計算、監査ログ（発注〜約定トレーサビリティ）などを包含します。

主な設計方針：
- ルックアヘッドバイアスを避けるために日付参照を明示的に受け取る（datetime.today() を直接参照しない）
- ETL・保存は冪等（ON CONFLICT）で安全に実行
- 外部 API 呼び出しはリトライ・レート制御・フォールバック実装あり
- テストしやすいように API 呼び出し点を差し替え可能に設計

---

## 機能一覧

- 環境設定と自動 .env 読み込み
  - .env / .env.local をプロジェクトルートから自動ロード（無効化可）
  - 必須環境変数の取得ユーティリティ（settings オブジェクト）
- データ収集（J-Quants 経由）
  - 日足（OHLCV）、財務データ、JPX カレンダー、上場銘柄情報の取得・保存
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の総合実行（run_daily_etl）
- ニュース収集
  - RSS 収集、URL 正規化、SSRF 対策、前処理、raw_news への冪等保存
- ニュース NLP / AI
  - ニュースを銘柄別に集約して OpenAI（gpt-4o-mini）でセンチメント評価（score_news）
  - マクロニュース + ETF ma200 乖離を使った市場レジーム判定（score_regime）
  - API 呼び出しは JSON-mode を利用し、エラー時のフェイルセーフ（0.0 で継続）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査スキーマ提供と初期化ユーティリティ
  - 発注フローのトレースを UUID 連鎖で保証
- ユーティリティ
  - データ品質チェック、マーケットカレンダー管理、統計ユーティリティ等

---

## 動作要件 / 依存関係

推奨 Python バージョン: 3.10 以上（PEP 604 の型記法などを使用）

主な依存パッケージ（例）
- duckdb
- openai
- defusedxml

インストール方法はプロジェクトの packaging に依存しますが、単純な開発環境なら:

pip install duckdb openai defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb openai defusedxml

3. .env を作成（プロジェクトルートに配置）
   - .env.example があれば参照してください。主な環境変数:
     - JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD - kabu ステーション API 用パスワード（必須）
     - KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN - Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID - Slack チャンネル ID（必須）
     - OPENAI_API_KEY - OpenAI API キー（score_news / score_regime で未指定時に参照）
     - DUCKDB_PATH - デフォルト DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH - 監視用 SQLite パス（default: data/monitoring.db）
     - KABUSYS_ENV - 実行環境 (development|paper_trading|live)
     - LOG_LEVEL - ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
   - 自動 .env ロードはデフォルトで有効。無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース準備
   - DuckDB ファイルを指定する場合は DUCKDB_PATH を設定
   - 監査用 DB を別途作成する場合は kabusys.data.audit.init_audit_db() を使用

---

## 使い方（簡単な例）

以下は Python REPL・スクリプトから各主要機能を呼び出す例です。

1) 設定の参照

from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)

2) DuckDB 接続の作成

import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))

3) 日次 ETL の実行

from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())

4) ニュースのスコアリング（OpenAI キーは環境変数または api_key 引数で指定）

from datetime import date
from kabusys.ai.news_nlp import score_news

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照
print("scored:", count)

5) 市場レジーム判定

from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

6) 監査スキーマ初期化（audit DB）

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 既存 conn に対してスキーマだけ追加する場合:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

7) RSS フィード取得（ニュースコレクタ）

from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])

※ 実運用では各関数の戻り値を検証し、例外ハンドリング・ログ出力を適切に行ってください。

---

## 主な公開 API / 重要関数一覧

- kabusys.config.settings
  - 設定値（環境変数）を取得するプロパティ群

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=..., ...) → ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別 ETL）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token

- kabusys.data.news_collector
  - fetch_rss(url, source) → list[NewsArticle]
  - preprocess_text, URL 正規化等のユーティリティ

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None) → 書き込み銘柄数

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None) → 1（成功）

- kabusys.research.factor_research
  - calc_momentum / calc_volatility / calc_value

- kabusys.research.feature_exploration
  - calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.data.quality
  - run_all_checks(conn, target_date=..., ...) → list[QualityIssue]

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(path) → DuckDB 接続

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイル、抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの AI スコアリング（score_news）
    - regime_detector.py            — マクロ + ma200 で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 結果クラスの公開
    - news_collector.py             — RSS 取得・前処理・保存ユーティリティ
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - research/ ...                   — 研究用ユーティリティ群
  - monitoring/, execution/, strategy/, monitoring/ ... （パッケージ化想定）

この README はコードベースから主要な機能を抜粋してまとめたものです。  
各モジュールの詳細な使用法・設定や、CI/CD／運用（cron で ETL を定期実行、Slack 通知、ポジション管理、発注フロー）については個別のドキュメント（運用手順書）を参照してください。

もし README に追加したい具体的な使用例（例えば「バックテストの実行方法」や「kabu API の実行例」など）があれば教えてください。追加の例やテンプレート（.env.example）も作成します。