# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
DuckDB をデータレイヤに用い、J-Quants API から市場データ・財務データ・カレンダーを取得して ETL → 特徴量作成 → シグナル生成 → 発注監査までを想定したモジュール群を提供します。

主な設計思想
- 研究（research）と運用（strategy / execution）を分離
- ルックアヘッドバイアスを防ぐことを重視（取得時刻の記録・target_date ベース処理）
- DB 保存は冪等（ON CONFLICT / トランザクション）で実装
- 外部依存は最小限（duckdb, defusedxml 等）

バージョン: 0.1.0

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（jquants_client）
    - 日足価格（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
    - トークン自動リフレッシュ、リトライ、レートリミット制御
  - raw データの DuckDB への冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）
- ETL パイプライン（data.pipeline）
  - 差分取得、backfill、品質チェック（quality モジュールを呼び出す想定）
  - run_daily_etl で日次 ETL を実行
- スキーマ管理（data.schema）
  - DuckDB のテーブル定義と初期化（init_schema）
  - 各レイヤ（raw / processed / feature / execution）を定義
- 特徴量計算（research.factor_research / strategy.feature_engineering）
  - Momentum / Volatility / Value 等のファクター計算
  - クロスセクション Z スコア正規化（data.stats.zscore_normalize）
  - features テーブルへの日付単位の UPSERT（冪等）
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL の生成、signals テーブルへの書き込み
- ニュース収集（data.news_collector）
  - RSS フィード取得（SSRF 対策、サイズ制限、XML 安全パーサ）
  - raw_news / news_symbols への保存、銘柄コード抽出
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、next/prev_trading_day、calendar_update_job
- 監査ログ（data.audit）
  - シグナル→注文→約定のトレーサビリティを保持するテーブル群

---

## セットアップ手順

前提
- Python 3.9+ を推奨（typing の union 型などを利用）
- システムに pip がインストール済み

1. リポジトリをクローン / コピー

2. 仮想環境を作成・有効化（任意）
   - macOS / Linux:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール
   - 最低限:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成することで自動ロードされます（既定で OS 環境 > .env.local > .env の順）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   必須環境変数（コードで _require() により参照されます）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu API のパスワード（execution 層利用時）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（通知機能を使う場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   省略可能（デフォルト値を持つもの）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化
   - Python REPL またはスクリプトで DuckDB スキーマを作成します。
   - 例:
     - python - <<'PY'
       from kabusys.data.schema import init_schema
       init_schema("data/kabusys.duckdb")
       PY

---

## 使い方（主要な API と実行例）

以下はライブラリを直接インポートして操作する簡単な例です。実運用ではこれらをラッパー CLI / ジョブスケジューラに組み込むことを想定しています。

1. DuckDB 接続とスキーマ初期化
   ```
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルがない場合は作成されます
   ```

2. 日次 ETL を実行（J-Quants から差分取得して保存）
   ```
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を渡さないと今日を使用
   print(result.to_dict())
   ```

3. 市場カレンダーの夜間更新ジョブ
   ```
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print("calendar saved:", saved)
   ```

4. ニュース収集ジョブ
   ```
   from kabusys.data.news_collector import run_news_collection
   # known_codes は銘柄抽出に使う既知コードの集合（例: {'7203','6758',...}）
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)
   ```

5. 特徴量作成（strategy.feature_engineering）
   ```
   from kabusys.strategy import build_features
   from datetime import date
   n = build_features(conn, target_date=date(2024, 1, 10))
   print("features upserted:", n)
   ```

6. シグナル生成（strategy.signal_generator）
   ```
   from kabusys.strategy import generate_signals
   from datetime import date
   total = generate_signals(conn, target_date=date(2024,1,10))
   print("signals generated:", total)
   ```

7. J-Quants API を直接使う（単発取得）
   ```
   from kabusys.data.jquants_client import fetch_daily_quotes
   quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
   print(len(quotes))
   ```

注意点
- run_daily_etl では内部で calendar 更新 → prices/fins ETL → 品質チェックの順で処理します。各ステップは独立してエラーハンドリングされ、完了後 ETLResult を返します。
- generate_signals / build_features は target_date ベースで過去データのみを参照するよう設計されています（ルックアヘッド防止）。

---

## 環境変数（まとめ）

必須
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | ...)

自動 .env ロードを無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py              # J-Quants API クライアント（取得 + 保存ユーティリティ）
  - news_collector.py             # RSS ニュース収集・保存
  - schema.py                     # DuckDB スキーマ定義・初期化
  - stats.py                      # 汎用統計ユーティリティ（zscore_normalize 等）
  - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
  - features.py                   # zscore_normalize の再エクスポートインターフェース
  - calendar_management.py        # マーケットカレンダー操作・更新ジョブ
  - audit.py                      # 監査ログ用テーブル定義
- research/
  - __init__.py
  - factor_research.py            # Momentum / Volatility / Value の計算
  - feature_exploration.py        # IC / forward returns / summary 等（research 用）
- strategy/
  - __init__.py
  - feature_engineering.py        # 生ファクターの正規化・features テーブルへの保存
  - signal_generator.py           # final_score 計算・BUY/SELL シグナル生成
- execution/                       # 発注関連モジュール（空ファイルが含まれている）
  - __init__.py
- monitoring/                      # 監視・アラート用（SQLite/外部連携想定）

補足: 各モジュールは README 中の API 名でインポート可能です（例: from kabusys.data.schema import init_schema）。

---

## 開発メモ / 注意事項

- DB 初期化: init_schema はテーブル作成を行い、既存テーブルがある場合はスキップします（冪等）。
- J-Quants のレート制限: 120 req/min を守るためモジュール内で固定間隔スロットリングを実装しています。
- ニュース収集: defusedxml を利用し XML 攻撃を防止、SSRF 対策のためリダイレクト先の検査やプライベート IP ブロックを実装しています。
- 品質チェック: pipeline.run_daily_etl は quality モジュール（別途実装想定）を呼び出します。品質チェックはエラーを集約し呼び出し側で対処する設計です。
- 実運用時は KABUSYS_ENV を正しく設定（paper_trading / live）し、ログレベルと通知設定を確認してください。

---

必要に応じて、README に CI / packaging / デプロイ手順やサンプル .env.example、運用オペレーション（ジョブスケジューリング例: cron / systemd / Airflow）の追記が可能です。追加したい項目があれば教えてください。