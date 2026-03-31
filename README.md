# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）です。  
ETL（J-Quants）によるマーケットデータ収集、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などを一貫して提供します。

## 主な特徴
- J-Quants API 経由の差分ETL（株価、財務、JPXカレンダー）と品質チェック
- ニュース収集（RSS）と OpenAI を用いた銘柄単位センチメントスコアリング（ai_scores）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ）と特徴量探索ユーティリティ
- 監査ログ（signal_events / order_requests / executions）用の DuckDB スキーマ初期化
- 安全性（SSRF対策、XML注入対策）、冪等保存（ON CONFLICT）、リトライ／レート制御を考慮した実装

---

## 機能一覧（主要モジュール）
- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - settings オブジェクトから各種設定取得
- kabusys.data
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - jquants_client: J-Quants API クライアント／保存関数（fetch_*/save_*）
  - news_collector: RSS 取得・前処理・保存
  - quality: データ品質チェック（欠損／重複／スパイク／日付不整合）
  - calendar_management: 営業日判定、next/prev/get_trading_days、calendar_update_job
  - audit: 監査ログテーブル初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄別ニュースセンチメントの取得→ai_scores への保存
  - regime_detector.score_regime(conn, target_date, api_key=None): 市場レジーム判定→market_regime への保存
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（主な依存ライブラリ）
- Python 3.10+
- duckdb
- openai (OpenAI Python client) — OpenAI Chat API を使用
- defusedxml
- （標準ライブラリ：urllib, json, datetime, logging 等）

※ 実行環境に合わせて適宜 requirements.txt / pyproject.toml を整備してください。

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは手動で: pip install duckdb openai defusedxml

4. パッケージをインストール（開発モード推奨）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある階層）に `.env` または `.env.local` を配置すると自動ロードされます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須の環境変数（config.Settings 参照）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token 用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（注文連携がある場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector が利用）

オプション（デフォルト値は Settings 内に定義）
- KABUSYS_ENV: development / paper_trading / live（default: development）
- LOG_LEVEL: DEBUG/INFO/...（default: INFO）
- DUCKDB_PATH: data/kabusys.duckdb（データベースファイルパス）
- SQLITE_PATH: data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など監視用設定

---

## 使い方（Python API の例）

注意: すべての操作は DuckDB 接続（duckdb.connect(...)）を渡して行います。時刻は基本的に date / datetime オブジェクトで扱います。

- ETL（日次パイプライン）を実行する例
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（AI）を実行する例
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数に設定しておく
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定を実行する例
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査DBを初期化する（監査用別DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親フォルダを自動作成
  ```

- settings 利用例
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

---

## 実行上の注意点 / 運用ヒント
- OpenAI 実行には API キー（OPENAI_API_KEY）が必須です。モデルは gpt-4o-mini を想定しています（news_nlp/regime_detector）。
- J-Quants の API はレート制限があり、クライアント側でレート制御とリトライを実装しています。JQUANTS_REFRESH_TOKEN を必ず設定してください。
- ニュース収集は RSS を利用します。news_collector は SSRF 対策や受信バイト数上限を備えています。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。CI・テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- DuckDB の executemany に空リストを渡すと例外になるバージョン（0.10 等）があります。内部実装はその点に注意してありますが、実運用では DuckDB のバージョン管理を推奨します。
- テスト時は OpenAI / HTTP クライアント呼び出しをモックして実行してください（コード内で差し替えや patch を想定しています）。

---

## ディレクトリ構成（主要ファイル）
（src 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメントのスコアリング
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py      — J-Quants API クライアント + 保存関数
    - news_collector.py      — RSS 取得 / 前処理
    - quality.py             — データ品質チェック
    - calendar_management.py — 市場カレンダー管理 / 営業日ロジック
    - stats.py               — zscore_normalize 等
    - audit.py               — 監査ログスキーマ初期化
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/, data/, research/ はそれぞれ別のユースケース（自動売買、データ処理、研究）向けに分離

---

## トラブルシューティング
- "環境変数が設定されていません" のような ValueError が出る場合は .env を確認し必須キーがセットされているか確認してください。
- OpenAI 呼び出しで RateLimitError / API エラーが出る場合、news_nlp / regime_detector はリトライ・フォールバックを実装しています。ログを参照して回復可能か判断してください。
- J-Quants API の 401 エラーはモジュール内でリフレッシュを試みますが、refresh token が間違っていると失敗します。JQUANTS_REFRESH_TOKEN を再確認してください。

---

もし README に追加してほしいコマンドラインツール例、CI 設定例、もしくは各テーブル（スキーマ）の詳細ドキュメントを希望される場合は知らせてください。必要に応じてサンプル .env.example の雛形も作成できます。