# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI でのセンチメント評価）、ファクター計算、監査ログ（発注/約定トレース）、市場カレンダー管理、データ品質チェックなどを提供します。

---

## 主要な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（ページネーション・レート制御・再試行対応）。
  - ETL の結果をまとめて返す run_daily_etl（差分取得・バックフィル・品質チェック含む）。

- ニュース収集・NLP
  - RSS からのニュース収集（SSRF対策、トラッキングパラメータ除去、前処理）。
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント評価（score_news）。
  - マクロニュース + ETF（1321）の200日MA乖離を合成して市場レジーム判定（score_regime）。

- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算（calc_momentum, calc_volatility, calc_value）。
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化ユーティリティ。

- データ品質チェック
  - 欠損、主キー重複、スパイク（急騰・急落）、日付不整合（未来日／非営業日のデータ）などを検出。

- 監査ログ（Audit）
  - シグナル → 発注リクエスト → 約定の一連のトレーサビリティを保持する監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）。

- カレンダー管理
  - market_calendar テーブルを用いた営業日の判定・次/前営業日の取得・期間内の営業日取得、夜間バッチ更新ジョブ。

---

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントの | を使用しているため）
- DuckDB, OpenAI SDK 等の依存ライブラリが必要

1. リポジトリをチェックアウト / コピー
   - 一般的にはパッケージルートに `pyproject.toml` や `.git` が存在します。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
   - 主要依存の例:
     - duckdb
     - openai
     - defusedxml
   - 開発 / 配布形式に合わせて `pip install -e .` などを利用してください。

4. 環境変数 / .env の設定
   - 必須（機能による）：
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（注文関連）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意（デフォルトあり）：
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...
     - KABU_API_BASE_URL — kabuAPI のベースURL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
     - OPENAI_API_KEY — OpenAI を利用する機能で使用
   - .env 自動ロード:
     - パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動読み込みします。
     - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データベース初期化（監査ログ等）
   - 監査ログ専用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - 既存の DuckDB 接続に監査スキーマだけ追加する場合は `init_audit_schema(conn)` を使用。

---

## 使い方（簡易ガイド）

以下は主要なユースケースのコード例（対話的に実行する想定）。

- DuckDB 接続の作成:
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行:
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニューススコア（AI）を計算して保存:
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - written = score_news(conn, target_date=date(2026, 3, 20), api_key="<OPENAI_API_KEY>")
  - print(f"書き込み件数: {written}")

- 市場レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="<OPENAI_API_KEY>")

- ファクター計算 / 研究用 API:
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - recs = calc_momentum(conn, date(2026,3,20))
  - normalized = from kabusys.data.stats import zscore_normalize
  - zrecs = zscore_normalize(recs, ["mom_1m", "mom_3m", "mom_6m"])

- RSS フィード取得（ニュース収集補助）:
  - from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  - articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")

- 監査 DB 初期化（トランザクション有効）:
  - from kabusys.data.audit import init_audit_db
  - conn_audit = init_audit_db("data/audit.duckdb")

注意:
- OpenAI API を使う関数は api_key 引数に明示的にキーを渡すか、環境変数 OPENAI_API_KEY を設定してください。未設定時は ValueError を送出します。
- 各関数の詳細な挙動（例: 時刻ウィンドウ、データ不足時のフォールバック、リトライポリシー）は該当モジュールの docstring を参照してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD (必須 for kabu 機能) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuAPI ベース URL（既定: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（既定: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（既定: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する（任意、1 を設定）

.env のパースは POSIX style（export対応、シングル/ダブルクォート対応、行末コメント処理）を行います。詳細は kabusys.config の実装を参照してください。

---

## ディレクトリ構成（概要）

（パッケージルート）/
- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン定義
  - config.py — 環境変数・設定管理（自動 .env 読み込み、settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py — 銘柄別ニュースセンチメント（OpenAI 呼び出し、バッチ/リトライ/バリデーション）
    - regime_detector.py — ETF (1321) MA とマクロニュースを合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集、前処理、SSRF 対策
    - calendar_management.py — 市場カレンダー / 営業日判定 / calendar_update_job
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py — 監査ログ（signal_events / order_requests / executions）DDL と初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー / rank
  - research 関連やその他モジュールは研究用途に特化（本番発注コードとは切り離し）
- pyproject.toml / setup.cfg / requirements.txt （プロジェクト依存に応じて）

---

## 開発・運用上の注意

- Look-ahead バイアス対策が各所に組み込まれています（関数は date 引数を受け、datetime.today() を参照しない設計）。
- OpenAI / J-Quants API 呼び出しはリトライ・バックオフ・エラーハンドリング済み。API キー・レート制限に注意してください。
- DuckDB の executemany 等、一部 API の挙動に依存したワークアラウンドが実装されています（空リストの executemany 回避など）。
- 監査ログは削除しない前提、order_request_id を冪等キーとして二重発注を防止する設計です。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査、プライベートIPブロック、スキーム検証）を実装しています。
  - .env に機密情報を格納する場合は適切なファイルアクセス制御を行ってください。

---

## 参考: よく使う API まとめ

- ETL:
  - run_daily_etl(conn, target_date, id_token=None, ...)
- データ取得 (J-Quants):
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - save_daily_quotes(conn, records)
- ニュース／AI:
  - fetch_rss(url, source)
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)
- 監査:
  - init_audit_db(db_path)
  - init_audit_schema(conn)
- カレンダー:
  - calendar_update_job(conn)
  - is_trading_day(conn, date)
  - next_trading_day(conn, date)

---

必要であれば、各モジュール別の API 参照（関数の引数・返り値・例外動作）をまとめた詳細なドキュメントも作成します。どのモジュールのドキュメントが必要か教えてください。