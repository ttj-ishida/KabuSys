# KabuSys

日本株向け自動売買システムのライブラリ群（モジュール群）。データ取得・ETL、特徴量計算、シグナル生成、監査ログなどを含む研究〜運用までの基盤機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は次のレイヤーを持つ設計の自動売買基盤です。

- Data Platform: J-Quants API からのデータ取得、DuckDB ベースのスキーマ、ETL パイプライン、ニュース収集
- Research: ファクター計算・特徴量探索ツール（ルックアヘッドバイアス回避を考慮）
- Strategy: 正規化済み特徴量から最終スコアを算出し売買シグナルを作成
- Execution / Monitoring: 発注・約定・ポジション・監査用スキーマやフロー（発注連携は別実装想定）

設計方針の要点:
- 冪等性（DB への保存は ON CONFLICT / UPSERT）
- ルックアヘッドバイアス回避（target_date ベース）
- ネットワークリトライ・レート制御・SSRF 対策等の安全策
- 外部依存を最小化し、DuckDB と標準ライブラリ中心で実装

---

## 主な機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート基準）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN 等）
- Data / ETL（kabusys.data）
  - J-Quants クライアント（jquants_client）: データ取得、リトライ、レート制御、DuckDB 保存ユーティリティ
  - スキーマ定義・初期化（schema.init_schema）
  - 日次 ETL パイプライン（pipeline.run_daily_etl）
  - ニュース収集（news_collector）: RSS 取得→前処理→DB 保存、銘柄抽出
  - カレンダー管理（calendar_management）: 営業日判定、カレンダー更新ジョブ
  - 統計ユーティリティ（stats.zscore_normalize）
- Research（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- Strategy（kabusys.strategy）
  - 特徴量合成・正規化（feature_engineering.build_features）
  - シグナル生成（signal_generator.generate_signals）
    - final_score の算出、Bear レジーム抑制、BUY/SELL の判定、signals テーブルへの保存
- Audit（kabusys.data.audit）
  - 監査テーブル群（signal_events / order_requests / executions 等）定義（トレーサビリティ）
- その他
  - News の SSRF 防御、XML 攻撃対策、レスポンスサイズ制限などの耐障害・セキュリティ対策

---

## 必要条件（例）

- Python 3.10+
- 主要依存（プロジェクト側で管理してください）:
  - duckdb
  - defusedxml

（上記はコード内で使用されているライブラリです。実際の pyproject/requirements.txt に合わせてください。）

---

## 環境変数（必須 / 任意）

config.Settings で参照する主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD - kabuステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID - Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV - 環境（development / paper_trading / live）, デフォルト `development`
- LOG_LEVEL - ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）, デフォルト `INFO`
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH - 監視用 SQLite パス（デフォルト `data/monitoring.db`）

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます。

注意: パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env / .env.local を自動ロードします。

---

## セットアップ手順（Quick Start）

1. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージのインストール（例）
   - pip install duckdb defusedxml
   - その他プロジェクトで必要なパッケージを pyproject/requirements.txt に従ってインストール

3. プロジェクトルートに .env を作成（.env.example を参考に）
   - 必須の環境変数（JQUANTS_REFRESH_TOKEN など）を設定

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # 既定のパスを使う場合
     conn.close()
     ```
   - メモリ DB を使う場合: init_schema(":memory:")

---

## 使い方（代表的な API）

以下は主要ワークフローの簡単な使用例です。

- 日次 ETL の実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 既に初期化済みの場合は get_connection()
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- 特徴量（features）構築
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total_signals}")
  conn.close()
  ```

- ニュース収集（RSS）と銘柄紐付け
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203","6758","9984"}  # 有効銘柄セット（例）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  conn.close()
  ```

- カレンダー更新ジョブ（夜間バッチ等で）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  conn.close()
  ```

注意点:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。スキーマ初期化は init_schema を用いて行ってください。
- pipeline.run_daily_etl 等は内部でエラーを捕捉して処理継続する設計ですが、戻り値の ETLResult で失敗・品質問題を確認してください。

---

## ディレクトリ構成（主要部分）

簡易ツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                         # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                # J-Quants API クライアント（取得・保存）
    - news_collector.py                # RSS 取得 & raw_news 保存・銘柄抽出
    - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
    - schema.py                        # DuckDB スキーマ定義 & init_schema
    - stats.py                         # 統計ユーティリティ（zscore_normalize）
    - features.py                      # features の公開インターフェース（再エクスポート）
    - calendar_management.py           # マーケットカレンダー管理
    - audit.py                          # 監査ログ用の DDL / 初期化ロジック
    - execution/                        # 発注関連モジュール（骨格）
  - research/
    - __init__.py
    - factor_research.py               # momentum / volatility / value の計算
    - feature_exploration.py           # calc_forward_returns, calc_ic, factor_summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py           # features を作成して features テーブルへアップサート
    - signal_generator.py              # final_score 計算・BUY/SELL シグナル生成
  - execution/                          # 発注実行ロジック（未定義の部分あり）
  - monitoring/                         # 監視（未定義の部分あり）

（上記は実装済みファイルの概略です。詳細は各モジュールの docstring を参照してください。）

---

## 重要な設計上の注意・運用メモ

- ルックアヘッドバイアス対策: 戦略系関数は target_date 時点の情報のみを利用するよう設計されています。将来データを用いないよう注意してください。
- 冪等性: データ保存は ON CONFLICT / UPSERT で重複を避けています。バッチ再実行に耐える設計です。
- レート制御 / 再試行: J-Quants クライアントは固定間隔スロットリング（120 req/min）とリトライ（指数バックオフ）を行います。
- セキュリティ: news_collector では SSRF 対策や defusedxml による XML パースの安全化、受信サイズ制限などを実装しています。
- テスト: 設計上、id_token の注入や _urlopen のモック差し替えでユニットテストが行いやすくなっています。
- production では KABUSYS_ENV を `live` に設定し、発注・モニタリング周りの実装を適切に設定してください。

---

この README はソースコード内の docstring と設計コメントに基づくサマリです。各モジュールの詳細は該当ファイル（src/kabusys/...）の docstring / 関数ドキュメントを参照してください。