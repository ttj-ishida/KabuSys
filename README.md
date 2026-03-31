# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP、AI を使った市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどを一貫して提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API からの株価（日次 OHLCV）、財務諸表、マーケットカレンダー取得（ページネーション・リトライ・レート制御対応）
  - 差分更新 / バックフィル設計
  - DuckDB へ冪等保存（ON CONFLICT 相当の更新）
- ニュース収集
  - RSS 取得（SSRF 対策・トラッキングパラメータ除去・サイズ制限）
  - raw_news / news_symbols との紐付け用ユーティリティ
- ニュース NLP / AI
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約（`score_news`）
  - ETF（1321）の MA 乖離とニュースセンチメントを合成した市場レジーム判定（`score_regime`）
  - API 呼び出しでの堅牢なリトライ・フォールバック設計（失敗時はフェイルセーフ）
- Research（ファクター計算・特徴量解析）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - z-score 正規化ユーティリティ
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（QualityIssue を返す）
- カレンダー管理
  - market_calendar を用いた営業日判定、next/prev/trading days 取得、カレンダー差分更新ジョブ
- 監査ログ（Audit）
  - signal_events / order_requests / executions といった監査テーブルの初期化（DuckDB）
  - 監査データベース初期化ユーティリティ
- 設定管理
  - .env / .env.local / 環境変数からの読み込み（自動ロード、必要に応じて無効化可能）

---

## 前提条件

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI など）

（プロジェクトで使用される正確な依存は requirements ファイル等で管理してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - 例: git clone <repo_url>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - またはプロジェクトの requirements.txt があれば: pip install -r requirements.txt
   - 開発インストール（パッケージとして使う場合）:
     - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに .env または .env.local を置くと自動でロードされます（デフォルト）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID：Slack 通知先チャンネル ID
- OPENAI_API_KEY：OpenAI API キー（AI 機能を利用する際）

任意（デフォルトあり）:
- KABU_API_BASE_URL（デフォルト "http://localhost:18080/kabusapi"）
- DUCKDB_PATH（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH（デフォルト "data/monitoring.db"）
- PID_FILE_PATH（デフォルト "data/execution.pid"）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV（"development" / "paper_trading" / "live"、デフォルト "development"）
- LOG_LEVEL（"DEBUG","INFO","WARNING","ERROR","CRITICAL"、デフォルト "INFO"）

注:
- Settings は kabusys.config.settings で提供されます。未設定の必須変数にアクセスすると ValueError が発生します。

---

## 使い方（基本例）

- DuckDB 接続の取得例:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（prices / financials / calendar をまとめて実行）
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュース NLP（指定日分のスコアを ai_scores に書き込む）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key を渡すか OPENAI_API_KEY を環境変数に設定

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- ファクター計算 / Research
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - moment = calc_momentum(conn, target_date=date(2026,3,20))

- 監査ログ DB 初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- J-Quants API を直接使う（必要に応じて）
  - from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  - token = get_id_token()
  - records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))

- ニュース取得（RSS）
  - from kabusys.data.news_collector import fetch_rss
  - articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

---

## API（よく使う公開関数）

- kabusys.config.settings — 環境設定オブジェクト
- kabusys.data.pipeline.run_daily_etl(...) — メイン ETL エントリポイント（戻り値: ETLResult）
- kabusys.data.jquants_client.* — J-Quants の取得/保存ユーティリティ (get_id_token, fetch_daily_quotes, save_daily_quotes 等)
- kabusys.data.news_collector.fetch_rss(...) — RSS の取得（NewsArticle 型を返す）
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) — ニュース NLU スコアリング
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — 市場レジーム判定
- kabusys.research.* — ファクター/IC/統計関数
- kabusys.data.quality.run_all_checks(...) — データ品質チェック
- kabusys.data.audit.init_audit_db / init_audit_schema — 監査テーブル初期化

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定読み込み
- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLU / OpenAI 呼び出し
  - regime_detector.py           — MA とニュースを合成した市場レジーム判定
- data/
  - __init__.py
  - pipeline.py                  — ETL パイプライン（run_daily_etl など）
  - jquants_client.py            — J-Quants API クライアント（取得・保存）
  - news_collector.py            — RSS 収集・前処理
  - calendar_management.py       — 市場カレンダー管理（is_trading_day 等）
  - stats.py                     — 汎用統計ユーティリティ（z-score など）
  - quality.py                   — データ品質チェック
  - audit.py                     — 監査ログスキーマ初期化
  - etl.py                       — ETL インターフェース（ETLResult 再エクスポート）
- research/
  - __init__.py
  - factor_research.py           — Momentum/Value/Volatility 等
  - feature_exploration.py       — forward returns, IC, 統計サマリー
- research/*                      — 追加の研究用ユーティリティ

（実際のリポジトリにはさらにモジュール・ユーティリティが含まれます）

---

## 設計上の注意点 / 運用メモ

- Look-ahead bias の抑制
  - 多くのモジュールは datetime.today()/date.today() を直接参照せず、明示的に target_date を受け取ります。バックテストや日次バッチではこの慣習に従ってください。
- 冪等性（Idempotency）
  - ETL / 保存処理は ON CONFLICT 相当で更新を行い、重複挿入を防止します。
- フェイルセーフ
  - 外部 API（OpenAI / J-Quants 等）呼び出しで失敗が発生しても、可能な限り処理を継続する設計です（ただしエラーはログへ）。
- 自動 .env ロード
  - プロジェクトルート (.git または pyproject.toml のあるディレクトリ) から .env/.env.local を自動で読み込みます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しについて
  - news_nlp / regime_detector は gpt-4o-mini の JSON Mode を期待します。レスポンス検証やリトライを実装していますが、API の削減およびコスト管理に注意してください。

---

## 参考：よくある操作例（短いまとめ）

- ETL を今すぐ実行（今日分）:
  - conn = duckdb.connect(str(settings.duckdb_path))
  - run_daily_etl(conn)

- OpenAI によるニューススコア取得:
  - score_news(conn, date(2026,3,20))

- 市場レジーム算出:
  - score_regime(conn, date(2026,3,20))

---

この README はコードベースの概要と典型的な利用方法を示すためのものです。詳細な実装や運用手順は各モジュールの docstring（ソース内コメント）を参照してください。必要ならばサンプルスクリプトや CI/デプロイ手順の追加ドキュメントを作成します。