KabuSys — 日本株自動売買 / データ基盤ライブラリ
=================================

概要
----
KabuSys は日本株のデータ取得・ETL、ニュース NLP（LLM によるセンチメント評価）、市場レジーム判定、ファクター計算、監査ログ（発注→約定のトレーサビリティ）などをまとめた内部ライブラリ群です。DuckDB をローカルデータレイクとして使い、J-Quants API からの差分取得や RSS ニュース収集、OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価を想定しています。

主な特徴
-------
- データ取得 / ETL
  - J-Quants API から株価日足・財務・上場銘柄・マーケットカレンダーを差分取得し DuckDB に冪等保存
  - 日次 ETL のエントリポイント（run_daily_etl）を提供
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などを検出する品質チェック群
- ニュース収集 / NLP
  - RSS からニュースを収集し raw_news に保存
  - OpenAI を使った銘柄ごとのニュースセンチメント集約（score_news）
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュース LLM スコアを合成してレジーム判定（score_regime）
- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査用スキーマ初期化・専用 DB 初期化機能
- 研究用ユーティリティ
  - ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ、Z スコア正規化

必要条件
-------
- Python >= 3.10（PEP 604 の型表記を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml
- これ以外に標準ライブラリのみで実装されています。環境に応じて追加パッケージをインストールしてください。

環境変数 / 設定
----------------
設定は .env ファイル（プロジェクトルート）または環境変数で行います。.env.local は .env を上書きする用途で優先的に読み込まれます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/MEMORY/DISK 閾値: 監視設定
- KABUSYS_ENV: 実行環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

セットアップ手順
----------------
1. リポジトリをクローン / コピー：
   - 例: git clone <repo-url>

2. Python 環境を準備（仮想環境推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール:
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. 環境変数を準備:
   - プロジェクトルートに .env を作り、各種キーを設定（.env.example を参考にしてください）
   - 例（最低限）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=your_openai_api_key
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. DuckDB 用ディレクトリを作成（必要に応じて）:
   - mkdir -p data

基本的な使い方（コード例）
-------------------------

- DuckDB 接続の作成（設定経由）:
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行:
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄ごと）を計算して ai_scores に保存:
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("書込銘柄数:", n_written)

  ※ api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照します。

- 市場レジーム判定（market_regime テーブルに書き込む）:
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用

- 監査ログ用 DB を初期化:
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルへアクセス可能

- RSS フィードを取得（ニュース収集ユーティリティの一部）:
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])

注記 / 運用上のポイント
----------------------
- Look-ahead バイアス対策が各モジュールで意識されています（target_date 指定や DB の date < target_date 条件など）。
- OpenAI 呼び出しはレスポンス検証とリトライ（指数バックオフ）を実装しています。API エラーやパース失敗時はフェイルセーフとしてスコアを 0.0 にフォールバックする箇所があります。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストや明示的制御が必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany に空リストを渡すと動作しないバージョンがあるため、コード内で空リストチェックがされています。

ディレクトリ構成（主要モジュール）
-------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数と Settings クラス（自動 .env ロード機能含む）
- ai/
  - __init__.py
  - news_nlp.py         — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py  — ETF MA 乖離 + マクロニュース LLM を合成して market_regime に書き込む
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API 呼び出し・保存ロジック（rate limit, retry, token refresh）
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETLResult の再エクスポート
  - news_collector.py   — RSS フィード取得・前処理・保存ロジック
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - stats.py            — zscore_normalize 等の統計ユーティリティ
  - quality.py          — 品質チェック群（欠損・スパイク・重複・日付不整合）
  - audit.py            — 監査ログスキーマ初期化・専用 DB 初期化
- research/
  - __init__.py
  - factor_research.py  — momentum/value/volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計要約・ランク関数
- research/*, ai/* は研究・解析用 API を提供
- その他: strategy/, execution/, monitoring/（__all__ には含まれていますが本リストでは詳細ファイルが抜粋されていません）

開発 / テスト
--------------
- 自動 .env ロードの影響を受けないようにテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しやネットワーク依存部分はモックしてテストすることを推奨します（コード中にテスト差替え用の patch ポイントあり）。

最後に
------
本 README はコードベースから読み取れる振る舞い・設定・利用方法をまとめたものです。細かな挙動や API のバージョン依存（OpenAI SDK や DuckDB のバージョン）により実行時の差異が生じる場合があります。運用環境での稼働前に小規模なステージング検証を行ってください。

必要であれば README に含めるサンプル .env.example、docker-compose、CI の実行手順やより詳しい API リファレンス（関数引数/戻り値のサンプル） を追加します。どの情報を優先して追加しますか？