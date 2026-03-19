KabuSys — 日本株自動売買システム (README)
=======================================

概要
----
KabuSys は日本株のデータ取得・加工・特徴量生成・シグナル生成・発注監査までを想定した自動売買基盤のコアライブラリです。主に以下のレイヤーを提供します。

- Data (J-Quants からのデータ取り込み、DuckDB スキーマ、ETL)
- Research (ファクター計算、特徴量探索・統計)
- Strategy (特徴量正規化 → シグナル生成)
- Execution / Audit（スキーマ側での発注・約定・監査設計）

本リポジトリはパイプライン実装、統計ユーティリティ、RSS ニュース収集などのユーティリティ関数群を含み、研究・本番双方での利用を想定しています。

主な機能
--------
- DuckDB スキーマ定義と初期化（init_schema）
- J-Quants API クライアント（レート制御、リトライ、トークン更新）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの取得
- ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- 特徴量計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量の Z スコア正規化（クロスセクション）
- シグナル生成（複数コンポーネントスコアの重み付け、BUY/SELL の生成）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策、XML 脆弱性対策）
- 発注・約定・監査用スキーマ定義（トレーサビリティ設計）

セットアップ手順
----------------

1. リポジトリをクローン（パッケージは src/ 配下に配置されています）
   - この README は src/kabusys の内容を前提にしています。

2. Python 環境の準備（推奨: venv）
   - python3 -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージのインストール（最低限）
   - duckdb: データベース
   - defusedxml: RSS XML の安全なパース
   例:
   - pip install duckdb defusedxml

   （プロジェクトに requirements ファイルがある場合はそれを使用してください。）

4. 環境変数の設定
   - ルートディレクトリ（.git または pyproject.toml のあるディレクトリ）に .env/.env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID
     - KABU_API_PASSWORD     : kabu ステーション API のパスワード
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると自動 .env 読み込みを無効化
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite のパス（デフォルト data/monitoring.db）
   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

使い方（例）
------------

以下は簡単な対話／スクリプト利用例です。適宜 logging 設定や環境変数を整えてください。

1. DuckDB スキーマ初期化
   ```
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（市場カレンダー・株価・財務を差分取得）
   ```
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を指定しないと今日
   print(result.to_dict())
   ```

3. 特徴量構築
   ```
   from kabusys.strategy import build_features
   from datetime import date

   build_features(conn, date(2024, 1, 10))
   ```

4. シグナル生成
   ```
   from kabusys.strategy import generate_signals
   from datetime import date

   total = generate_signals(conn, date(2024, 1, 10))
   print(f"signals generated: {total}")
   ```

5. ニュース収集（RSS）
   ```
   from kabusys.data.news_collector import run_news_collection

   known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # ソースごとの新規保存件数
   ```

注意点 / トラブルシューティング
--------------------------------
- settings が必須環境変数をチェックします。欠けていると ValueError が発生します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。CIやテストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB ファイルパスの親ディレクトリは自動作成されますが、パーミッション等に注意してください。
- J-Quants API 呼び出しはレート制限とリトライを実装済みですが、実運用時は API 仕様（キー制限等）に従ってください。
- RSS フィードは外部ネットワークに依存します。SSRF 対策や受信サイズ制限が入っていますが、ネットワーク失敗は呼び出し元でハンドリングしてください。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要モジュール一覧（抜粋）です。詳細は各モジュールの docstring を参照してください。

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - schema.py                     — DuckDB スキーマ定義と init_schema
    - jquants_client.py             — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS 収集 / 保存 / 銘柄抽出
    - calendar_management.py        — 市場カレンダーのユーティリティ
    - features.py                   — zscore_normalize 再エクスポート
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査テーブル定義 DDL（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py            — momentum / volatility / value 計算
    - feature_exploration.py        — 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        — features テーブル生成（build_features）
    - signal_generator.py           — signals 生成（generate_signals）
  - execution/                      — 発注層の雛形（詳細実装は別）
  - monitoring/                     — 監視・ログ周り（未公開のユーティリティ想定）
  - その他（テスト・CI 用ファイルは別途）

開発 / 貢献
------------
- 各モジュールは docstring に設計方針と前提（参照するテーブル等）が記載されています。まずは docstring を読み、DuckDB 上でのテーブル状態やデータ有無を確認しながら実行してください。
- 新機能や修正は単体モジュールのユニットテストを追加してください（本 README にはテストフレームワークは含めていません）。

ライセンス
----------
- 本 README ではライセンスの記載を省略しています。実際のプロジェクトでは LICENSE を追加してください。

補足
----
- 本 README はコード内の docstring を基に作成しています。実運用ではログ設定（ローテーション等）、モニタリング、堅牢なエラーハンドリング、発注実行層の外部インターフェース（ブローカー接続・署名等）を別途実装してください。