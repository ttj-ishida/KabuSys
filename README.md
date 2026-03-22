# KabuSys

日本株向けの自動売買システム用ライブラリ / フレームワークです。  
データ収集（J-Quants）、ETL、特徴量計算、シグナル生成、バックテスト、ニュース収集などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の機能をレイヤ化して提供します。

- データ収集（J-Quants API 経由の株価・財務・市場カレンダー）
- ETL（差分更新・品質チェックを想定）
- DuckDB ベースのスキーマ定義・初期化
- 研究向けファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量の正規化（Z スコア）と features テーブルへの書き込み
- シグナル生成（複数コンポーネントを合成して BUY/SELL を生成）
- バックテストフレームワーク（擬似約定・ポートフォリオシミュレータ・評価指標）
- ニュース収集（RSS）および記事と銘柄の紐付け
- 設定管理（.env 自動読み込み）

設計方針として「ルックアヘッドバイアスを避ける」「冪等性」「外部発注層への依存排除（戦略層は発注層へ直結しない）」などを重視しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
  - raw_prices / raw_financials / market_calendar の保存関数
- データベース
  - DuckDB 用スキーマ定義と初期化（init_schema）
- 研究 / 特徴量
  - calc_momentum / calc_volatility / calc_value
  - zscore_normalize（クロスセクション Z スコア）
  - 特徴量合成（build_features）
- 戦略 / シグナル
  - 複数コンポーネント（momentum/value/volatility/liquidity/news）による final_score 計算
  - Bear レジーム抑制、売買シグナルの冪等保存（generate_signals）
- バックテスト
  - 日次ループでの擬似約定（スリッページ・手数料モデル）
  - ポートフォリオシミュレータ、バックテスト指標計算（CAGR, Sharpe, MaxDD, WinRate, Payoff）
  - CLI 実行可能スクリプト（kabusys.backtest.run）
- ニュース収集
  - RSS フィード取得、前処理、raw_news への冪等保存
  - 記事IDのハッシュ生成、銘柄コード抽出と紐付け
- 設定管理
  - .env ファイル自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（Settings クラス）

---

## セットアップ手順

前提: Python 3.10+ を推奨（type union などを利用しているため）。

1. リポジトリのクローン（ローカル開発用）
   ```
   git clone <リポジトリURL>
   cd <リポジトリ>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール  
   本コードベースで明示的に使用されている主要ライブラリ:
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. パッケージを編集可能インストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数の準備  
   プロジェクトルートに `.env` を置くと自動で読み込まれます（読み込みは __file__ を基準にルートを検出）。  
   例（.env.example）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで便利です）。

6. DuckDB スキーマの初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # data ディレクトリがなければ自動作成されます
   ```

---

## 使い方

以下は主要なユースケースのサンプルです。

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db data/kabusys.duckdb
  ```
  実行前に DB に prices_daily / features / ai_scores / market_regime / market_calendar が存在するか確認してください。run_backtest は指定 DB から必要なテーブルをコピーしてインメモリでバックテストを行います。

- DuckDB スキーマ初期化（サンプル）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()
  ```

- J-Quants データ取得 & 保存（例）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  quotes = jq.fetch_daily_quotes(date_from=..., date_to=...)
  jq.save_daily_quotes(conn, quotes)
  conn.close()
  ```

- ETL の個別実行（パイプラインの一部を呼ぶ）
  - run_prices_etl / run_news_collection / run_financials_etl 等を組み合わせて利用します（pipeline.run_* 系関数にトークン注入可）。
  - 例: ニュース収集
    ```python
    from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")
    res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
    conn.close()
    print(res)
    ```

- 特徴量構築・シグナル生成（研究→運用のワークフロー）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features, generate_signals
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 3, 1)
  build_features(conn, target)
  generate_signals(conn, target)
  conn.close()
  ```

- バックテストを Python 呼び出しで行う
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

  print(result.metrics)
  ```

注意:
- 各モジュールは「当日までにシステムが知り得るデータのみ」を使う設計（ルックアヘッド防止）。
- generate_signals / build_features は DuckDB のテーブル（features, prices_daily, ai_scores, positions 等）を参照・更新します。テーブルスキーマは data/schema.py を参照してください。

---

## 環境変数（主な必須 / 推奨）

- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（data.jquants_client が使用）
  - SLACK_BOT_TOKEN : Slack 通知用（本コードでは Settings で必須扱い）
  - SLACK_CHANNEL_ID : Slack 通知先チャンネルID
  - KABU_API_PASSWORD : kabuステーション API 連携用パスワード

- 任意
  - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH : 監視用 sqlite パス デフォルト "data/monitoring.db"
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化（値を設定すると無効）

.settings は kabusys.config.Settings で参照可能です。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py : パッケージ定義、バージョン
  - config.py : 環境変数/.env 管理と Settings クラス
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント、取得・保存ロジック
    - news_collector.py : RSS 取得・前処理・raw_news 保存・銘柄抽出
    - schema.py : DuckDB スキーマ定義と init_schema / get_connection
    - stats.py : zscore_normalize 等の統計ユーティリティ
    - pipeline.py : ETL パイプライン（差分更新や get_last_* ヘルパー等）
  - research/
    - __init__.py
    - factor_research.py : モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py : 将来リターン / IC / 統計サマリー等の分析ツール
  - strategy/
    - __init__.py
    - feature_engineering.py : features テーブル構築（正規化・フィルタ）
    - signal_generator.py : final_score 計算・BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py : run_backtest の実装（インメモリコピー・ループ）
    - simulator.py : PortfolioSimulator（擬似約定・history/trades 管理）
    - metrics.py : バックテストメトリクス計算（CAGR, Sharpe, MaxDD, 等）
    - run.py : CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py : SimulatedClock（将来拡張用）
  - execution/ : 発注周り（現状空の __init__、発展予定）
  - monitoring/ : 監視・アラート機能（実装は今後）
  - backtest/*.py, strategy/*.py 等に戦略ロジックとバックテスト接続

---

## 開発上の注意点 / ベストプラクティス

- ルックアヘッドバイアス回避のため、各処理は target_date 時点で利用可能なデータのみを参照します。
- DB 操作は可能な限りトランザクションやバルク挿入で原子性・効率を確保しています（DuckDB の制約に配慮）。
- ニュース取得では SSRF・XML Bomb 対策（defusedxml, レスポンスサイズ制限, プライベートホスト除外）を実装しています。
- テスト時は .env 自動読み込みを無効にする（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）ことで環境依存を排除できます。

---

もし README に追加したい具体的な例（.env.example の詳細、CI 実行手順、Dockerfile、依存の固定バージョンなど）があれば教えてください。必要に応じて追記します。