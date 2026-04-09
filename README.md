# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants／RSS／OpenAI などの外部データを取り込み、ETL・品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログなどを一貫して提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価／財務／カレンダー等の差分取得（ETL）
- DuckDB によるデータ格納と品質チェック
- ニュース収集（RSS）と LLM（OpenAI）を用いた銘柄センチメントの自動スコアリング
- 市場レジーム判定（ETF MA と マクロニュースの LLM センチメント合成）
- 研究用ファクター計算・特徴量解析ツール
- 発注／約定の監査ログ（監査用スキーマ初期化ユーティリティ）
- 環境変数管理（.env 自動読み込み機能）

設計方針の共通点として、ルックアヘッドバイアス対策（内部で datetime.today()/date.today() を不用意に参照しない）や冪等性（DB 書き込みは ON CONFLICT を利用）・フェイルセーフ（API 失敗時は安全なデフォルトで継続）を重視しています。

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存・トークン自動リフレッシュ・レート制御）
  - カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF 対策、raw_news 保存）
  - 品質チェック（欠損・重複・スパイク・日付不整合検出）
  - 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
  - 汎用統計ユーティリティ（zscore_normalize など）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM を合成して market_regime に保存
- research/
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリーなど
- config.py
  - 環境変数管理（.env 自動読み込み、必須キー取得メソッド、各種パス・フラグ）

---

## セットアップ手順

1. 必要条件
   - Python 3.10 以上（型注釈で `X | None` を使用しているため）
   - ネットワークアクセス（J-Quants / OpenAI / RSS）

2. リポジトリをクローン（あるいはパッケージ化されている場合は pip install）
   - 開発中: リポジトリのルートで editable install
     ```bash
     pip install -e .
     ```
   - 依存パッケージ（代表例）
     ```bash
     pip install duckdb openai defusedxml
     ```
     ※実際の requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

3. 環境変数設定（.env ファイル）
   - パッケージはプロジェクトルート（.git または pyproject.toml）を探索して自動で `.env` / `.env.local` を読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必須）
     - KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携がある場合）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE: paper trading の fill モード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視関連設定
     - KABUSYS_ENV: environment ('development' | 'paper_trading' | 'live')
     - LOG_LEVEL: ログレベル（DEBUG, INFO, ...）

   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベース初期化（監査用など）
   - 監査ログ専用 DB 初期化の例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用 DuckDB にテーブルスキーマを用意するユーティリティがある想定（プロジェクト全体の schema 初期化関数を用意している場合はそちらを利用してください）。

---

## 使い方（代表的な例）

- DuckDB 接続を作り、日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジームを判定する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key=None)  # OPENAI_API_KEY を利用
  ```

- 監査スキーマを ETL 用 DB に追加する
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- ai モジュール（OpenAI）を利用する際は API 呼び出しに料金が発生します。キー・利用量に注意してください。
- run_daily_etl 等の関数は内部で network / API を呼び出します。ID トークンは settings.jquants_refresh_token を参照します。

---

## よくある運用ワークフロー

- 夜間バッチ（cron/airflow）で run_daily_etl を実行しデータ更新・品質チェック → 研究／戦略は更新データを参照
- RSS を定期収集し raw_news に保存 → 毎朝ニューススコア（score_news）を実行 → シグナル生成へ使う
- 毎日（営業日）市場レジーム（score_regime）を計算して戦略のアロケーション調整に利用
- 実運用（kabu API 経由で発注）時は audit スキーマへ信号・発注・約定を必ず書き込む

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                    # ニュース NLP スコアリング（score_news）
    - regime_detector.py             # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント（取得 + 保存 + トークン管理）
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - etl.py                         # ETL 公開インターフェース（ETLResult）
    - calendar_management.py         # 市場カレンダー管理（営業日判定等）
    - news_collector.py              # RSS 取得・前処理・保存
    - quality.py                     # データ品質チェック
    - stats.py                       # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                       # 監査ログのDDL/初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py             # Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py         # 将来リターン, IC, 統計サマリー
  - ai/、research/、data/ のテストや追加ユーティリティは必要に応じて実装

---

## 注意事項 / 運用上のヒント

- .env 自動読み込みはプロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）を基に行われます。パッケージ配布後やテスト時に挙動を変えたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは再試行やタイムアウト処理を行いますが、API の利用料金・レート制限には注意してください。
- DuckDB への executemany で空リストを渡すとエラーになるバージョン（例: 0.10）があるため、関数内で空リストをチェックしています。DuckDB バージョンに依存する動作に注意してください。
- ETL 実行結果は ETLResult で返され、品質チェックの検出結果を含みます。結果をログ・監査に残す運用を推奨します。

---

必要であれば README に以下を追記できます：
- CI / テスト実行例（pytest）
- requirements.txt の候補
- 詳細な API リファレンス（各関数の引数・戻り値のサンプル）
- Docker イメージ化／Kubernetes 運用例

ご希望があれば追記・補足します。