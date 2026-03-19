# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ（監査含む）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のクオンツ運用に必要な基盤機能を集めたライブラリです。  
主に次を目的としています。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いたローカルデータレイクの管理（Raw / Processed / Feature / Execution レイヤ）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量正規化・合成（features テーブル生成）
- シグナル（BUY / SELL）生成ロジック
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダー管理（営業日判定等）
- ETL パイプライン（差分取得・品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計方針としてルックアヘッドバイアス回避、冪等性、ネットワーク対策（レート制限・リトライ・SSRF対策）等に注意して実装されています。

---

## 主な機能（モジュール別）

- kabusys.config
  - 環境変数読み込み（.env / .env.local の自動読み込み）と設定オブジェクト `settings`
- kabusys.data.jquants_client
  - J-Quants API クライアント、取得・保存（raw_prices / raw_financials / market_calendar）
  - レート制御、リトライ、トークンリフレッシュ、DuckDB への冪等保存
- kabusys.data.schema
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit）
  - init_schema(), get_connection()
- kabusys.data.pipeline
  - 日次 ETL（差分取得、backfill、品質チェック）: run_daily_etl()
  - 個別 ETL ジョブ（prices, financials, calendar）
- kabusys.data.news_collector
  - RSS 取得・パース、記事正規化、raw_news 保存、銘柄コード抽出・紐付け
  - SSRF・gzip・XML 攻撃対策、受信サイズ制限
- kabusys.research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量解析ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.strategy
  - 特徴量生成（build_features）
  - シグナル生成（generate_signals）
- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、カレンダー更新ジョブ
- kabusys.data.audit
  - 監査ログ用テーブル定義（signal_events / order_requests / executions 等）
- kabusys.data.stats
  - 共通統計ユーティリティ（zscore_normalize）

---

## セットアップ手順

以下は一般的なセットアップ手順の例です。

1. リポジトリを取得
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール  
   （本リポジトリに requirements ファイルがない場合は最低限以下を入れてください）
   - pip install duckdb defusedxml

   実運用では他に logging やテスト用のライブラリが必要になることがあります。

4. 環境変数の設定  
   プロジェクトのルートに `.env` または `.env.local` を置くと自動的に読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みは無効化されます）。

   必須の環境変数（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション等の API パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   オプション（デフォルトあり）:
   - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
   - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
   - DUCKDB_PATH : duckdb ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite のパス（デフォルト data/monitoring.db）

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL かスクリプトで実行:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（簡単な例）

以下は主要な利用シナリオの例です。実際は適切なログ設定や例外処理を組み合わせてください。

- DuckDB 接続 & スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（J-Quants からの差分取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # 省略時: target_date = today, id_token = cached
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへ保存）
  ```python
  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, date(2026, 1, 31))
  print(f"built features: {count}")
  ```

- シグナル生成（signals テーブルへ保存）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date(2026, 1, 31))
  print(f"signals written: {total}")
  ```

- RSS ニュース収集（raw_news / news_symbols へ保存）
  ```python
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- テスト時の環境変化
  - 自動で `.env` を読み込む仕組みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテストなどで便利です）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys 配下の主要モジュールを抜粋しています。

- kabusys/
  - __init__.py
  - config.py                            # 環境変数管理・Settings
  - data/
    - __init__.py
    - jquants_client.py                  # J-Quants API クライアント + 保存機能
    - news_collector.py                  # RSS ニュース収集と保存
    - schema.py                          # DuckDB スキーマ定義・init_schema
    - stats.py                           # 統計ユーティリティ（zscore_normalize）
    - pipeline.py                        # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py             # カレンダー管理・営業日判定
    - audit.py                           # 監査ログテーブル
    - features.py                         # features インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py                 # モメンタム/ボラティリティ/バリューの計算
    - feature_exploration.py             # IC, forward returns, summary
  - strategy/
    - __init__.py
    - feature_engineering.py             # features を作成するビルド処理
    - signal_generator.py                # final_score 計算・BUY/SELL 生成
  - execution/
    - __init__.py                         # 発注層（空のパッケージスタブ）
  - monitoring/                            # 監視・通知関連（ディレクトリあり）

補足:
- DuckDB スキーマは schema.py に集約されており、Raw / Processed / Feature / Execution / Audit 層のテーブル DDL が定義されています。
- research 以下は主に研究・分析用ユーティリティで、戦略実行ロジックとは依存関係を分離しています。

---

## 注意点 / 運用上のポイント

- 環境（KABUSYS_ENV）は `development`, `paper_trading`, `live` のいずれかを指定してください。値が不正な場合はエラーになります。
- J-Quants API はレート制限（120 req/min）に合わせた制御を組み込んでいますが、運用時には API 利用状況に応じた追加制御が必要になる場合があります。
- DuckDB のバージョン差分により外部キーや ON DELETE の挙動に制限があるため、コード中にその旨の注記があります（実運用でのデータ削除等は注意してください）。
- ニュース RSS の取得では SSRF・XML 攻撃・Gzip Bomb などへの対策を実装していますが、外部ソースの取り扱いには常に注意してください。
- シグナル→発注→約定のトレーサビリティは audit モジュールで整備されています。実運用では order_request_id による冪等制御が重要です。

---

## 貢献・拡張

- 新しいデータソース、AI スコア連携、ブローカー接続（execution 層）などは既存モジュールを参考に実装・追加してください。
- テストは各モジュールを孤立してテスト可能な設計を意識しています（例: id_token 注入、_urlopen のモックなど）。

---

README に記載されていない操作や API の詳細はソースコード（特に docstring）に仕様が書かれています。必要であれば具体的な利用シナリオやサンプルスクリプトの追加も対応します。