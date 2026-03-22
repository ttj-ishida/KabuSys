# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム基盤です。  
データ取得 (J-Quants)、ETL、特徴量エンジニアリング、シグナル生成、バックテスト、ニュース収集、擬似約定シミュレータ等を含むモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得
  - J-Quants API から日足・財務データ・市場カレンダーを取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- ETL / パイプライン
  - 差分更新、バックフィル、品質チェック機能（DataPlatform 規約に準拠）
- データ層（DuckDB）
  - Raw / Processed / Feature / Execution 層のスキーマ定義と初期化
- 研究（research）
  - モメンタム・ボラティリティ・バリューなどのファクター計算
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターの正規化、ユニバースフィルタリング、features テーブルへの書き込み（冪等）
- シグナル生成（strategy.signal_generator）
  - features と AI スコアを統合して final_score を計算、BUY/SELL シグナルの生成（冪等）
- バックテスト（backtest）
  - 日次ループ型バックテストエンジン、ポートフォリオシミュレータ、評価指標計算（CAGR/Sharpe/MaxDD 等）
  - CLI ランナーを提供
- ニュース収集（data.news_collector）
  - RSS から記事収集、テキスト前処理、記事ID生成、記事と銘柄の紐付け、DB 保存（冪等）
- その他ユーティリティ
  - 統計ユーティリティ（z-score 正規化）、スキーマ初期化、設定管理（環境変数読み込み）

---

## 要件

- Python 3.10+
- 推奨パッケージ（主要な依存のみ記載）
  - duckdb
  - defusedxml

（実行環境に応じて他ライブラリが必要になる場合があります。requirements.txt がある場合はそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージ配布物を取得）
   - git clone ...（プロジェクトルートに移動）

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （もし requirements.txt があれば）pip install -r requirements.txt

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成します。package 起動時に自動読み込みされます（ただしテスト目的で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API パスワード（execution 層利用時）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
   - データベースのパス（任意、デフォルト値あり）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視系 DB。デフォルト: data/monitoring.db）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - Python REPL、スクリプト、または簡単な初期化コマンドでスキーマを作成します：
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

---

## 使い方（主要な操作例）

以下は主要なモジュール／ワークフローの実行例です。実行はプロジェクトの Python パッケージが import 可能な環境で行ってください。

1. ETL（株価取得例）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data import jquants_client as jq
   from kabusys.data.pipeline import run_prices_etl

   conn = init_schema("data/kabusys.duckdb")
   target = date.today()  # 例: 当日まで取得
   # run_prices_etl は差分取得（内部で get_last_price_date を参照）します
   fetched, saved = run_prices_etl(conn, target_date=target)
   conn.close()
   ```

   - J-Quants API 呼び出しには JQUANTS_REFRESH_TOKEN が必要です。
   - jquants_client はレート制限（120 req/min）やリトライ・トークンリフレッシュを自動で扱います。

2. ニュース収集
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # known_codes は記事中の銘柄抽出に使う有効銘柄コード集合
   results = run_news_collection(conn, known_codes={"7203","6758"})
   conn.close()
   ```

3. 特徴量作成（features テーブルへの保存）
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024, 1, 31))
   print(f"features updated: {count}")
   conn.close()
   ```

4. シグナル生成（signals テーブルへの保存）
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   n = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
   print(f"signals inserted: {n}")
   conn.close()
   ```

5. バックテスト（CLI）
   - 提供されている CLI ランナーを使う例：
     ```
     python -m kabusys.backtest.run \
         --start 2023-01-01 --end 2024-12-31 \
         --cash 10000000 --db data/kabusys.duckdb
     ```
   - run.py の引数やデフォルト値:
     - --start / --end: 開始・終了日 (YYYY-MM-DD)
     - --cash: 初期資金（デフォルト 10,000,000）
     - --slippage / --commission / --max-position-pct
     - --db: DuckDB ファイルパス（必須）

   - また Python API として直接呼ぶことも可能：
     ```python
     from datetime import date
     from kabusys.data.schema import get_connection
     from kabusys.backtest.engine import run_backtest

     conn = get_connection("data/kabusys.duckdb")
     result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
     print(result.metrics)
     conn.close()
     ```

6. スキーマ初期化・接続
   - 初回は init_schema() を使ってテーブルを作成
   - 以降は get_connection() で接続するだけ

---

## 設定（Settings）について

- 環境変数は `kabusys.config.Settings` で参照されます。主なプロパティ：
  - jquants_refresh_token (JQUANTS_REFRESH_TOKEN) — 必須
  - kabu_api_password (KABU_API_PASSWORD) — 必須（execution を使う場合）
  - kabu_api_base_url (KABU_API_BASE_URL) — デフォルト "http://localhost:18080/kabusapi"
  - slack_bot_token / slack_channel_id — Slack 通知用（必須とされている箇所があります）
  - duckdb_path / sqlite_path — DB パス（省略時は data/...）
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

- 自動 .env のロード
  - パッケージインポート時にプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動読み込みします。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys） の要約です。実際のファイル数は省略しています。

- src/kabusys/
  - __init__.py — パッケージのバージョンと公開サブパッケージ定義
  - config.py — 環境変数 / 設定管理（自動 .env ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS ニュース収集・保存
    - pipeline.py — ETL パイプライン（差分更新 / バックフィル）
    - schema.py — DuckDB スキーマ定義 / init_schema / get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value 計算
    - feature_exploration.py — 将来リターン／IC／統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターの正規化・features 生成
    - signal_generator.py — final_score 計算と BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py — バックテストの全体ループ（run_backtest）
    - simulator.py — PortfolioSimulator, Mark-to-market, 約定ロジック
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI ランナー
    - clock.py — SimulatedClock（将来拡張用）
  - execution/ — （未実装/プレースホルダ: 発注・接続周りを想定）
  - monitoring/ — （監視・メトリクス・アラート系に使う想定）

---

## 注意事項 / 実装上の設計ノート（抜粋）

- look-ahead bias の防止:
  - 取得時に fetched_at を記録する等、戦略がその時点で利用可能な情報のみを使うよう設計されています。
- 冪等性:
  - DB への保存は ON CONFLICT を用いたアップサートや INSERT ... DO NOTHING を使い、再実行可能な ETL を目指しています。
- API 呼び出し:
  - J-Quants の呼び出しはレート制限（120 req/min）を守るための RateLimiter、リトライロジック、401 の自動リフレッシュに対応しています。
- セキュリティ:
  - RSS 収集時に SSRF 対策、XML パースの安全化（defusedxml）、受信サイズ制限 を実装しています。

---

## 開発時メモ / 貢献

- type ヒント（Python 3.10 の構文）を使用しています。CI/ローカルでの静的解析やユニットテストの追加を歓迎します。
- 実際の取引（kabu ステーション/API 連携）を行う場合は十分な検証・監査・権限管理が必要です（特に live 環境設定）。
- バグ報告・機能追加は Issue / PR でお願いします。

---

README は以上です。特定の操作（ETL の詳細な引数、DB の初期データ準備、実運用のデプロイ手順）についてテンプレートやサンプルが必要であれば、用途に応じた手順や .env.example、簡易スクリプトを追加で作成します。どの部分を詳しくしたいか教えてください。