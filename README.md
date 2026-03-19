# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォームを想定したライブラリ群です。  
主にデータ取得（J-Quants）、ETL／品質チェック、ニュース収集、特徴量計算、研究用ユーティリティ、監査ログ（発注→約定のトレーサビリティ）などを提供します。

---

## プロジェクト概要

- 名称: KabuSys
- 目的: 日本株のマーケットデータ取得から特徴量生成、研究用分析、発注監査までをカバーする再利用可能なモジュール群を提供すること。
- 設計方針の要点:
  - DuckDB を中核にしたローカルデータベース（冪等な保存／ON CONFLICT を使用）
  - J-Quants API からの差分取得（レート制御・リトライ・トークン自動リフレッシュ）
  - ニュース収集は RSS を対象に SSRF 対策やトラッキング除去を実装
  - 研究用モジュールは pandas 等に依存せず標準ライブラリと DuckDB SQL を活用
  - 品質チェック／監査ログ等で運用に必要な可観測性を確保

---

## 主な機能一覧

- 設定管理
  - .env / 環境変数から設定を自動ロード（プロジェクトルート判定、自動ロード無効化フラグあり）
  - 必須環境変数の検証（未設定時は例外）

- データ取得 / 保存
  - J-Quants API クライアント（ページネーション対応、レート制御、リトライ、トークン自動更新）
  - raw_prices / raw_financials / market_calendar 等への冪等保存関数

- ETL パイプライン
  - 差分取得（バックフィル）、市場カレンダー先読み、品質チェックを含む日次 ETL 実行
  - ETL の実行結果（ETLResult）を返却

- データ品質チェック
  - 欠損データ検出、スパイク検出（前日比）、重複チェック、日付整合性チェック

- ニュース収集
  - RSS フィード取得・前処理（URL除去／空白正規化）・記事ID生成（正規化URL の SHA-256）・DB 保存
  - SSRF 対策、gzip サイズ制限、トラッキングパラメータ除去、銘柄コード抽出

- 特徴量・研究モジュール
  - Momentum / Volatility / Value 等のファクター計算（DuckDB と SQL を活用）
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリー、Z-score 正規化

- スキーマ／監査ログ
  - DuckDB 用のスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - 監査用テーブル（signal_events / order_requests / executions）とインデックスの初期化ユーティリティ

---

## セットアップ手順

前提: Python 3.10 以上を推奨（`|` 型などを利用しているため）。

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージのインストール  
   主要依存例（プロジェクトに requirements.txt がない場合の参考）:
   - duckdb
   - defusedxml

   例:
   - pip install duckdb defusedxml

   （プロジェクト配布に requirements.txt があれば `pip install -r requirements.txt` を使用してください。）

3. 環境変数 / .env の用意  
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意・デフォルト例:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト `INFO`
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_station_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化（DuckDB）
   - Python REPL やスクリプトからスキーマを作成します（親ディレクトリが無ければ自動作成されます）。

   例:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

5. 監査ログ用スキーマ初期化（オプション）
   - 監査ログは別関数で初期化します（init_schema の後に呼ぶのが推奨）。

   例:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（簡単な例）

- 日次 ETL を実行する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  # target_date を指定しなければ今日が対象（市場カレンダーに合わせて調整）
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 銘柄抽出に使用する有効銘柄コードセットを渡すと紐付け処理を行う
  stats = run_news_collection(conn, known_codes={"7203","6758"})
  print(stats)  # {source_name: saved_count, ...}
  ```

- ファクター計算（モメンタム）を行う
  ```python
  from kabusys.research import calc_momentum
  from kabusys.data.schema import get_connection
  from datetime import date

  conn = get_connection("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2024, 1, 31))
  # records は [{"date": ..., "code": "7203", "mom_1m": ..., ...}, ...]
  ```

- 将来リターンと IC を計算する
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, rank
  # forward returns
  fwd = calc_forward_returns(conn, target_date=date(2024,1,31), horizons=[1,5,21])
  # factor_records は別途 calc_momentum 等で得たファクターリスト
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
  print("IC (Spearman):", ic)
  ```

- Z-score 正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
  ```

---

## よく使う環境変数（まとめ）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み・Settings クラス
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得 / 保存 / rate limiter / retry）
  - news_collector.py
    - RSS 取得・前処理・保存・銘柄抽出
  - schema.py
    - DuckDB スキーマ定義・init_schema / get_connection
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - pipeline.py
    - 差分 ETL、run_daily_etl 等のパイプライン
  - features.py
    - 特徴量関連の公開インターフェース
  - calendar_management.py
    - 市場カレンダーの管理・判定ユーティリティ
  - etl.py
    - ETLResult の公開
  - quality.py
    - データ品質チェック
  - audit.py
    - 監査ログ（発注→約定トレーサビリティ）用 DDL と初期化
- research/
  - __init__.py
    - 研究用関数の再エクスポート
  - feature_exploration.py
    - 将来リターン、IC、ファクターサマリー等
  - factor_research.py
    - Momentum / Value / Volatility 等のファクター計算
- strategy/
  - __init__.py
  - （戦略モデル関連の実装場所）
- execution/
  - __init__.py
  - （発注・ブローカー連携関連の実装場所）
- monitoring/
  - __init__.py
  - （監視・メトリクス関連の実装場所）

---

## 運用上の注意

- 自動売買や本番運用時は `KABUSYS_ENV=live` を設定し、安全対策（注文の二重送信防止、audit テーブルの利用、Slack 通知、監視）を十分行ってください。
- J-Quants の API レート制限や kabuステーション API の仕様、証券会社の約定仕様などは運用時に必ず確認してください。
- DuckDB のファイルバックアップ・スキーマ互換性や、監査ログは削除しない運用を推奨します（DDL にも注意書きあり）。
- テストや CI では環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動の .env 読み込みを無効化できます。

---

必要があれば、README に含めるサンプルコマンド（Makefile エントリ、systemd ユニット例、cron/timetable での ETL 実行例）や、requirements.txt の推奨内容、CI/CD 用のテスト手順なども追記します。どの情報が必要か教えてください。