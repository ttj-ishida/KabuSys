# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
データ取得（J-Quants）, ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集、バックテスト用シミュレータなどを含むモジュール群を提供します。

主な想定用途:
- 市場データの差分取得・保存
- 研究用ファクター計算・特徴量生成
- 戦略のシグナル生成（features + AI スコア統合）
- 発注を模したバックテスト（シミュレーション）
- RSS ベースのニュース収集と銘柄紐付け

---

## 機能一覧

- 環境設定管理（.env 自動読み込み、必須環境変数の検査）
- J-Quants API クライアント
  - 日足（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション・レートリミット・リトライ・トークン自動リフレッシュ対応）
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT を使用）
- ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- データスキーマ初期化（DuckDB 用 DDL を定義する init_schema）
- 研究用モジュール
  - ファクター計算（momentum / volatility / value）
  - ファクター探索（将来リターン計算、IC 計算、統計サマリ）
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（build_features）
  - ユニバースフィルタ、Z スコア正規化、features テーブルへの日付単位 UPSERT
- シグナル生成（generate_signals）
  - features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成し signals テーブルへ保存
  - Bear レジーム抑制、エグジット条件（ストップロス等）
- バックテストフレームワーク
  - インメモリで本番 DB をコピーして日次ループでシミュレーション
  - PortfolioSimulator（スリッページ・手数料を考慮した擬似約定）
  - 評価指標（CAGR、Sharpe、MaxDrawdown、勝率、Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ニュース収集（RSS ）
  - RSS 取得（SSRF 対策・gzip 対応・サイズ制限）、記事正規化、記事ID生成、raw_news 保存、銘柄抽出・紐付け

---

## 動作環境 / 必須要件

- Python 3.10 以上（型ヒントに `X | None` を使用しているため）
- 推奨パッケージ（最低限必要なもの）
  - duckdb
  - defusedxml

（実行環境に応じて追加パッケージが必要になる場合があります）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb defusedxml
     ```
   - 開発インストール（パッケージ化されている場合）:
     ```
     pip install -e .
     ```
   - その他、プロジェクト用の依存があれば requirements.txt / pyproject.toml を参照して追加してください。

4. 環境変数（.env）の準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須環境変数（Settings が参照するもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（execution 層利用時）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（通知機能を使う場合）
     - SLACK_CHANNEL_ID: Slack 通知先チャンネルID
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト：development）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト：INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマの初期化
   - Python から:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
   - これにより必要なテーブル（raw_prices, prices_daily, features, signals, positions 等）が作成されます。

---

## 使い方（主要ワークフロー例）

以下は代表的な利用方法の例です。

1. データ取得（J-Quants） → 保存
   ```python
   import datetime
   import duckdb
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   id_token = jq.get_id_token()  # settings から自動取得することも可能

   # 日足取得（差分は pipeline が便利）
   records = jq.fetch_daily_quotes(id_token=id_token, date_from=datetime.date(2024, 1, 1), date_to=datetime.date(2024, 1, 31))
   jq.save_daily_quotes(conn, records)
   conn.close()
   ```

2. ETL（差分取得）: pipeline 例（株価）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_prices_etl
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   target = date.today()
   fetched, saved = run_prices_etl(conn=conn, target_date=target)
   conn.close()
   ```

3. 特徴量（features）生成
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   cnt = build_features(conn, target_date=date(2024, 02, 01))
   print("upserted:", cnt)
   conn.close()
   ```

4. シグナル生成
   ```python
   import duckdb
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024, 02, 01))
   print("signals:", total)
   conn.close()
   ```

5. バックテスト（CLI）
   - 付属の CLI entrypoint を使ってバックテストを実行できます。
   ```
   python -m kabusys.backtest.run \
     --start 2023-01-01 --end 2023-12-31 \
     --cash 10000000 \
     --slippage 0.001 \
     --commission 0.00055 \
     --max-position-pct 0.20 \
     --db data/kabusys.duckdb
   ```
   - 事前にデータベースに prices_daily, features, ai_scores, market_regime, market_calendar が整っている必要があります。

6. ニュース収集（RSS）
   ```python
   import duckdb
   from kabusys.data.schema import init_schema
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   conn.close()
   ```

---

## 設計上の注意点 / ポイント

- ルックアヘッドバイアス防止: 特徴量・シグナル生成・データ取得は「target_date 時点で実際に利用可能だったデータ」だけを参照するよう設計されています（fetched_at の記録等）。
- 冪等性: 多くの保存関数は ON CONFLICT（UPSERT）や DO NOTHING を使い、繰り返し実行しても整合性が保たれます。
- エラー処理: API 呼び出しはリトライ・指数バックオフを持ち、401 はトークンリフレッシュを行う設計です。
- セキュリティ: RSS の取得は SSRF 対策（リダイレクト先の検査や private IP 拒否）や XML 関連の安全ライブラリ（defusedxml）を利用しています。
- テスト容易性: pipeline / jquants_client 等は id_token 注入や内部関数のモックを想定した設計になっています。

---

## ディレクトリ構成

主要ファイル・モジュールの概観（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント + 保存関数
    - news_collector.py  -- RSS 取得・記事処理・DB 保存
    - pipeline.py        -- ETL 管理・差分更新ロジック
    - schema.py          -- DuckDB スキーマ定義・init_schema
    - stats.py           -- zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     -- momentum/volatility/value 計算
    - feature_exploration.py -- 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py -- build_features
    - signal_generator.py    -- generate_signals
  - backtest/
    - __init__.py
    - engine.py            -- run_backtest（全体ループ）
    - simulator.py         -- PortfolioSimulator, DailySnapshot, TradeRecord
    - metrics.py           -- バックテスト評価指標計算
    - run.py               -- CLI entrypoint for backtest
    - clock.py             -- SimulatedClock（将来用途）
  - execution/             -- 発注層（現状空の __init__）
  - monitoring/            -- 監視・メトリクス用（未実装領域）

（各モジュール内に詳細な docstring / 設計メモを含みます）

---

## よくある運用フロー（例）

1. init_schema で DB を初期化
2. 日次 ETL を実行して raw_prices / raw_financials / market_calendar を更新
3. processed 層（prices_daily 等）の生成・整形（ETL 内で実施）
4. 研究側で factor を検証し、build_features を実行して features を更新
5. generate_signals を実行して signals を生成
6. バックテストは run_backtest で過去の期間を再現
7. 運用での自動発注を行う場合は execution 層を実装して kabu API と連携

---

## トラブルシューティング

- 環境変数が不足していると Settings のプロパティで ValueError が投げられます。エラーメッセージに従って .env を確認してください。
- DuckDB の DDL 実行で失敗する場合はログを確認し、ディスクの書き込み権限やファイルパスを確認してください。
- J-Quants API の 401 や rate limit は jquants_client のログ（警告／リトライ情報）を参照してください。

---

必要であれば、README に以下を追加できます:
- .env.example のテンプレートファイル
- CI 用のセットアップ手順（lint, tests）
- 実運用における運用チェックリスト（DB バックアップ、監視設定、Slack 通知設定例）
- 各モジュールの詳細な API リファレンス（関数ごとの引数・戻り値・例）

追加で入れたい項目があれば教えてください。