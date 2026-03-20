# KabuSys

日本株の自動売買・データ基盤ライブラリです。  
データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログなどを含むワンストップの内部ライブラリ群を提供します。

## プロジェクト概要

KabuSys は次のレイヤーを備えた設計を採用しています。

- Raw Layer: API から取得した未加工データ（株価・財務・ニュース等）
- Processed Layer: 整形済み市場データ（prices_daily 等）
- Feature Layer: 戦略・AI 用の特徴量（features / ai_scores）
- Execution Layer: シグナル・発注・約定・ポジション等の監査・履歴

主な実装ポイント:
- DuckDB を利用したオンディスク DB（デフォルト: data/kabusys.duckdb）
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
- RSS ベースのニュース収集（SSRF 対策・サイズ制限・トラッキング除去）
- 研究（research）モジュールに基づくファクター計算・探索
- 戦略層: 特徴量正規化 → final_score 計算 → BUY/SELL シグナル生成
- 冪等性 / トランザクション制御を意識した実装

## 機能一覧

- データ取得
  - J-Quants からの株価・財務・マーケットカレンダー取得（pagination 対応）
  - レート制限、リトライ、トークン自動更新対応
- データ永続化
  - DuckDB スキーマ定義と初期化（init_schema）
  - raw / processed / feature / execution 各種テーブル（冪等保存）
- ETL
  - 日次差分 ETL（run_daily_etl）：calendar / prices / financials の差分取得と保存
  - 差分ロジック、backfill、品質チェックフレームワーク
- ニュース収集
  - RSS フィード取得・前処理・raw_news 保存、銘柄抽出・紐付け
  - SSRF 対策・受信サイズ制限
- 研究 (research)
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量 / シグナル生成（strategy）
  - features テーブル構築（Zスコア正規化・クリッピング）
  - ai_scores と統合して final_score を計算し signals テーブルへ出力
  - Bear レジーム抑制、エグジット（ストップロス等）判定
- 監査（audit）
  - シグナル〜発注〜約定のトレーサビリティ用テーブル群

## セットアップ手順

前提:
- Python 3.9+ を想定（typing, 型注釈の記法に依存）
- DuckDB が使用可能（pip install duckdb）
- defusedxml（RSS パース保護用）

1. リポジトリをチェックアウトしてインストール
   - 開発環境向け:
     ```
     git clone <repo>
     cd <repo>
     python -m pip install -e .
     ```
   - 必要な依存パッケージをインストール:
     ```
     pip install duckdb defusedxml
     ```

2. 環境変数 / .env の準備  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（ただしテスト時など自動ロードを無効化可能）。

   必要な主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite DB パス（省略時 data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動読み込みを無効化したい場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

3. DB スキーマ初期化
   - Python REPL / スクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成
     ```

## 使い方（主要ユースケース）

以下は最小限の使い方例です。詳細は各モジュールのドキュメント文字列を参照してください。

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date 省略で今日
  print(result.to_dict())
  ```

- 特徴量構築（features テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, date(2024, 1, 10))
  print(f"features upserted: {n}")
  ```

- シグナル生成（features / ai_scores / positions を参照して signals に書き込む）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, date(2024, 1, 10))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # known_codes は銘柄抽出に使用（例: 全上場コードセット）
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)
  ```

- J-Quants からのデータ取得（クライアント利用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  recs = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
  saved = save_daily_quotes(conn, recs)
  ```

## 重要な設計・運用注意点

- ルックアヘッドバイアス回避: ファクターやシグナル計算は target_date 時点で利用可能なデータのみを参照するよう設計されています。
- 冪等性: DB への保存は ON CONFLICT / トランザクションで冪等化・原子性を確保しています。
- レート制限: J-Quants API は 120 req/min に合わせた RateLimiter を実装しています。
- ニュース収集のセキュリティ: SSRF 対策、XML の defusedxml 使用、受信サイズ制限などを実装しています。
- 環境変数自動読込: プロジェクトルートにある .env / .env.local を自動で読み込みます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

## ディレクトリ構成

主要ファイル / モジュールは以下のとおりです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                  -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存）
    - news_collector.py        -- RSS ニュース収集・前処理・DB 保存
    - schema.py                -- DuckDB スキーマ定義・初期化
    - stats.py                 -- 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
    - features.py              -- features の公開 shim
    - calendar_management.py   -- market_calendar 管理・営業日判定
    - audit.py                 -- 監査ログ用テーブル定義
    - quality.py (想定)        -- 品質チェック（pipeline から参照）
  - research/
    - __init__.py
    - factor_research.py       -- Momentum / Volatility / Value のファクター計算
    - feature_exploration.py   -- 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   -- features 作成（正規化・UPSERT）
    - signal_generator.py      -- final_score 計算・BUY/SELL 判定・signals 保存
  - execution/
    - __init__.py              -- （発注 / execution 層は別途実装）
  - monitoring/                -- 監視周り（/monitoring モジュール想定）

（上記はコードベースから抜粋した主なファイル群です）

## トラブルシューティング

- .env が読み込まれない / テストで制御したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（config.py の自動ロードを抑止）
- DuckDB 接続エラー:
  - パスにディレクトリが存在しない場合、init_schema が親ディレクトリを作成します。get_connection はスキーマ初期化を行わないため初回は init_schema を利用してください。
- API 呼び出しで 401 が返る:
  - jquants_client は 401 でリフレッシュを試みます。リフレッシュに失敗する場合は JQUANTS_REFRESH_TOKEN を確認してください。
- RSS 取得で XML 解析が失敗する:
  - ログに警告が出力されて空の結果が返ります。フィードの形式やエンコーディングを確認してください。

---

詳細な処理仕様（StrategyModel.md, DataPlatform.md 等）はコード内コメントや docstring に設計意図が書かれています。さらに深い使い方や運用手順が必要であれば、どの機能に焦点を当てたいか教えてください。README を補足して手順や例を追加します。