# KabuSys

日本株自動売買プラットフォームのライブラリ群（KabuSys）。  
データETL、ニュースNLP（OpenAI）、ファクター計算、監査ログ、マーケットカレンダー管理など、自動売買システムのコア機能を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 使い方（主要API例）
- 環境変数一覧
- 自動 .env 読み込みの挙動
- 設計上のポイント（注意事項）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株向け自動売買システムのための共通ユーティリティ群です。  
主な目的は次のとおりです：

- J-Quants API を用いた株価・財務・カレンダーの差分ETL（DuckDB 保存）
- RSS によるニュース収集と OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と研究用ツール
- マーケットカレンダー管理（営業日判定、next/prev trading day）
- 監査ログ（信号 → 発注 → 約定のトレースを行う監査テーブル群）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 市場レジーム判定（ETF + マクロニュースを組み合わせた判定）  

設計上、Look-ahead バイアス回避、冪等性（DB 保存は ON CONFLICT）、API リトライとレート制御、フェイルセーフ（API失敗時のフォールバック）を重視しています。

---

## 主な機能（機能一覧）
- データ取得・保存
  - J-Quants からの日足・財務・上場銘柄情報・カレンダー取得（fetch_*）
  - DuckDB への冪等保存（save_*）
  - 日次 ETL パイプライン（run_daily_etl）
- ニュース収集・NLP
  - RSS 収集（news_collector.fetch_rss / preprocess）
  - 銘柄単位のニュース集約と OpenAI によるセンチメント（score_news）
  - マクロニュースと ETF MA による市場レジーム判定（score_regime）
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC 計算、ファクター統計（feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- カレンダー管理
  - 営業日判定・翌営業日/前営業日取得・期間内の営業日取得（calendar_management）
  - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）
- 監査・トレーサビリティ
  - signal_events / order_requests / executions テーブルの初期化・操作（data.audit）
- 品質チェック
  - 欠損・重複・スパイク・日付不整合チェック（data.quality）

---

## 前提条件
- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）
- J-Quants リフレッシュトークン、OpenAI API キー等の環境変数を設定

requirements.txt が無い場合は上記ライブラリをインストールしてください。例：
pip install duckdb openai defusedxml

---

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - ない場合は個別インストール: pip install duckdb openai defusedxml
4. 環境変数を用意
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成するか、OS 環境変数として設定します。
   - 必須: JQUANTS_REFRESH_TOKEN（ETL を使う場合）、OPENAI_API_KEY（NLP を使う場合）
   - その他は下の「環境変数一覧」を参照
5. DuckDB / 監査DB 初期化（任意）
   - Python REPL 例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
6. ETL 実行（例）
   - run_daily_etl を使用して日次 ETL を実行します（J-Quants トークンが必要）。
     ```python
     import duckdb
     from datetime import date
     from kabusys.data.pipeline import run_daily_etl
     conn = duckdb.connect("data/kabusys.duckdb")
     res = run_daily_etl(conn, target_date=date(2026,3,20))
     print(res.to_dict())
     ```
7. AI 系機能を使う際は OPENAI_API_KEY を設定しておく

---

## 使い方（代表的な例）

- 簡単な DuckDB 接続と ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- 監査DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/monitoring_audit.duckdb")
  ```

- ニューススコアリング（OpenAI 必要）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定（OpenAI 必要）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- マーケットカレンダーの利用例
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026,3,20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

---

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須：ETL / jquants_client 用)
- KABU_API_PASSWORD (kabu ステーション API 用)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (OpenAI 呼び出し用：news_nlp / regime_detector)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知機能などに利用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用 sqlite: data/monitoring.db)
- PID_FILE_PATH (実行監視用)
- KILL_FLAG_PATH (停止フラグ)
- KILL_FLAG_CLEAR_ON_START (1 で起動時に kill flag をクリア)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT (監視しきい値)
- KABUSYS_ENV (development | paper_trading | live) — 動作環境
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

必須環境変数が足りない場合、Settings プロパティで ValueError が発生します。

---

## 自動 .env 読み込みの挙動
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` と `.env.local` を自動読み込みします。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- テスト等で自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env の解析はシェル形式に近く、export プレフィックスやクォート・行末コメント等に対応しています。

---

## 設計上のポイント / 注意事項
- Look-ahead バイアス回避のため、多くの関数は内部で datetime.today()/date.today() を直接参照せず、必ず target_date を引数として受けます。バックテストでの利用時は target_date を明示してください。
- DB 保存は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）にしています。
- J-Quants クライアントはレートリミット（120 req/min）を守るための固定間隔スロットリングと、リトライ（指数バックオフ）を実装しています。
- OpenAI 呼び出しは JSON Mode を想定し、リトライ・パース失敗時はフェイルセーフとしてゼロ（中立）にフォールバックする実装です。ただしAPIキーは必須（関数引数または環境変数 OPENAI_API_KEY）。
- news_collector は SSRF 対策、受信サイズ制限、XML パースの安全処理（defusedxml）を実装しています。
- DuckDB の executemany に関するバージョン制約（空リストの渡し方）に配慮した実装があります。DuckDB のバージョン差異に注意してください。
- init_audit_schema はトランザクションオプションがあります（DuckDB のトランザクション性に注意）。

---

## ディレクトリ構成（主要ファイル）
（ソースは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント + 保存関数
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETL 結果クラス再エクスポート
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - quality.py                       — データ品質チェック
    - calendar_management.py           — マーケットカレンダー管理
    - news_collector.py                — RSS 収集と前処理
    - audit.py                         — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py               — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py           — calc_forward_returns, calc_ic, factor_summary, rank
  - (その他) strategy/, execution/, monitoring/ モジュール群（パッケージ公開を想定）

---

この README はコードベースの主要機能・使い方の概要をまとめたものです。  
より詳細な仕様（データスキーマ、プロンプト設計、運用手順）は各モジュールのドキュメントやコメントを参照してください。必要があれば README に手順追加や使い方の具体例を追記します。