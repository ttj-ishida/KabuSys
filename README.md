# KabuSys

日本株向け自動売買・データ基盤ライブラリ（DuckDB ベース）。  
ETL（J-Quants 連携）→ 品質チェック → ニュース収集・AI スコアリング → ファクター/リサーチ → 戦略判定 → 監査・実行管理、までをサポートするモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ収集・前処理・特徴量生成・ニュース NLP（LLM）を組み合わせて、
自動売買戦略や研究用途に必要な機能を一貫して提供する Python パッケージです。  
主に以下を目的とします。

- J-Quants API からの株価・財務・市場カレンダーの差分 ETL（DuckDB 保存）
- ニュース RSS の収集と銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／市場レジーム判定
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と研究用ユーティリティ
- 監査ログ（signal → order_request → execution）のスキーマ初期化・管理
- データ品質チェック、カレンダー管理、ETL パイプライン制御

---

## 主な機能一覧

- data
  - jquants_client：J-Quants API 呼び出し、ページネーション、保存（raw_prices, raw_financials, market_calendar）
  - pipeline：日次 ETL（run_daily_etl）・個別 ETL（prices/financials/calendar）
  - quality：欠損・スパイク・重複・日付不整合のチェック
  - news_collector：RSS 収集、SSRF 対策、トラッキングパラメータ除去
  - calendar_management：営業日判定／next/prev／calendar 更新ジョブ
  - audit：監査ログ用 DDL 初期化（init_audit_schema / init_audit_db）

- ai
  - news_nlp.score_news：銘柄ごとのニュースセンチメントを LLM で算出し ai_scores に保存
  - regime_detector.score_regime：ETF(1321)の MA200 乖離 + マクロニュースで市場レジーム判定

- research
  - factor_research：calc_momentum / calc_value / calc_volatility
  - feature_exploration：forward returns / IC / factor summary / rank
  - data.stats：zscore_normalize（共通ユーティリティ）

- config
  - Settings クラス：環境変数ベースの設定取得（自動 .env ロード機能あり）

---

## 要件

- Python 3.10+
- DuckDB
- openai（OpenAI v1 SDK を想定）
- defusedxml
- そのほか標準ライブラリ中心（requests は使っていない実装）

（実行環境に合わせて requirements.txt を作成してください）

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. インストール（開発モード）
   - python -m pip install -e . 
   - 必要パッケージをインストール: pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置できます。
   - 自動読み込み順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（少なくともテストや ETL 実行に必要なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- OPENAI_API_KEY — OpenAI API キー（score_news/score_regime 実行時）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行モジュール使用時）
- （オプション）LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知連携
- DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH などは Settings にデフォルトあり

設定値は `kabusys.config.settings` で取得できます。

---

## 使い方（サンプル）

以下は主要なユーティリティの簡単な使用例です。実行前に必須環境変数を設定してください。

- DuckDB 接続を開く例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとのスコア付与）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  wrote = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
  print("書き込み銘柄数:", wrote)
  ```

- 市場レジーム判定（ETF 1321 ベース）:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  status = score_regime(conn, target_date=date(2026, 3, 20))
  print("OK" if status == 1 else "NG")
  ```

- 監査ログスキーマ初期化（監査 DB 作成）:
  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit をアプリの監査用に使用
  ```

- RSS フィード取得（ニュース収集）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- AI 関連（score_news, score_regime）は OpenAI API キーが必須です。api_key 引数で明示的に渡せます。
- 日付はすべて外部から渡す（内部で date.today() に依存しない実装になっています）ため、バックテスト環境でもルックアヘッドバイアスを低減できます。

---

## 設定（Environment / .env の振る舞い）

- 自動 .env ロードはパッケージ初期化時に行われ、プロジェクトルートは `.git` または `pyproject.toml` を基準に探索します。
- 読み込まれる順序:
  1. OS 環境変数（最優先）
  2. .env.local（存在すれば上書き）
  3. .env（最後に読み込み）
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを停止します（テスト等で利用）。
- .env のパースは export プレフィックス、クォート、コメント処理などに対応しています。

主要な Settings プロパティ（参照用）:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url
- settings.line_channel_access_token
- settings.duckdb_path / settings.sqlite_path
- settings.pid_file_path / settings.kill_flag_path / settings.kill_flag_clear_on_start
- settings.cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct
- settings.env（development / paper_trading / live）
- settings.log_level

---

## ディレクトリ構成

主要ファイル・モジュールの概観:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数/設定の読み込み
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメントスコアリング（LLM）
    - regime_detector.py    — 市場レジーム判定（ETF1321 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント + DuckDB 保存
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - quality.py            — データ品質チェック群
    - news_collector.py     — RSS 取得・前処理・保存ロジック
    - calendar_management.py— 市場カレンダー管理・営業日判定・更新ジョブ
    - audit.py              — 監査ログスキーマ初期化・監査 DB ヘルパー
    - etl.py                — ETLResult の再エクスポート
    - stats.py              — 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py    — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py— 将来リターン・IC・summary・rank 等
  - (その他: strategy / execution / monitoring のプレースホルダーが __all__ に列挙)

各モジュールはドキュメント文字列で設計方針・前提（Look-ahead バイアス対策、冪等性、ログ出力など）を明示しています。

---

## 運用・注意点

- J-Quants API のレート制限（120 req/min）を守る実装になっています（内部 RateLimiter）。
- OpenAI 呼び出しはリトライ・バックオフ処理を含みますが、API エラー時は安全側（デフォルトスコア 0.0）で継続する設計です。
- DuckDB の executemany に対する互換性（空リストへの対応）やトランザクション回復処理に配慮した実装があります。
- ニュース収集は SSRF 対策・受信サイズ上限・XML パース安全対策（defusedxml）を行っています。
- 監査ログは削除しない前提で設計されており、order_request_id による冪等性を確保します。

---

## 開発・テスト

- 自動テストはモジュール単位で mock を活用して外部 API 呼び出し（OpenAI / J-Quants / HTTP）を差し替える想定です。
- KABUSYS_DISABLE_AUTO_ENV_LOAD を使うとテスト時に .env の自動ロードを抑制できます。
- 例: unittest.mock.patch を使って _call_openai_api や _urlopen をモック可能です（各モジュールの docstring に記載あり）。

---

## ライセンス・貢献

（この README にライセンス情報が含まれていない場合はプロジェクトルートの LICENSE を参照してください）

貢献・バグ報告・改善提案は issue / PR をお送りください。

---

必要であれば、README にサンプル .env.example、より詳細な CLI 実行例（systemd / cron 用の起動例）、または各モジュールの API リファレンス抜粋を追加できます。どの情報を追加したいか教えてください。