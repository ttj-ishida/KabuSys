# KabuSys

日本株向けの自動売買フレームワーク（データ収集・ETL・特徴量生成・シグナル生成・発注監査）です。  
本リポジトリは研究（research）と本番（execution）両方のワークフローを想定したモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群から構成されています。

- J-Quants API から市場データ・財務データ・カレンダーを取得し DuckDB に保存する ETL（差分更新・後出し修正吸収）  
- RSS を用いたニュース収集と記事 → 銘柄コードの紐付け  
- ファクター（Momentum / Volatility / Value / Liquidity 等）の計算とクロスセクション正規化（Z スコア）  
- 正規化済みファクターおよび AI スコアを統合して売買シグナル（BUY / SELL）を生成  
- DuckDB 上のスキーマ定義、監査ログ（発注→約定のトレーサビリティ）  
- kabuステーション等の実際の発注レイヤ（execution）を置くための土台  

設計上のポイント：
- ルックアヘッドバイアスを防ぐ（計算は target_date 時点の情報のみを使用）  
- DuckDB による冪等保存（ON CONFLICT / トランザクション）  
- API レート制御・リトライ・トークン自動リフレッシュなどの堅牢化

---

## 主な機能一覧

- データ取得・保存（J-Quants）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- ETL パイプライン
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
- DuckDB スキーマ管理
  - init_schema, get_connection
- ニュース収集
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- ファクター計算（research）
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary
- 特徴量生成（strategy）
  - build_features（features テーブルへ保存）
- シグナル生成（strategy）
  - generate_signals（signals テーブルへ保存）
- 統計ユーティリティ
  - zscore_normalize
- 環境設定管理
  - Settings（環境変数・.env 自動ロード）

---

## セットアップ手順

以下はローカル開発環境の最小セットアップ例です。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # Unix/macOS
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージをインストール  
   主要依存（抜粋）:
   - duckdb
   - defusedxml
   もし requirements.txt があれば:
   ```
   pip install -r requirements.txt
   ```
   もしくは最低限:
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を準備  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   注意: Settings プロパティは必須変数がない場合 ValueError を送出します。

---

## 使い方（簡単な例）

以下は主要操作のサンプルコード例（Python REPL またはスクリプトで実行）。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成
   ```

2. 日次 ETL を実行（J-Quants トークンは環境変数から取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. ニュース収集（既知銘柄リストを与えて紐付け）
   ```python
   from kabusys.data.news_collector import run_news_collection
   known_codes = {"7203","6758","9432"}  # 例: 有効な銘柄コードセット
   stats = run_news_collection(conn, known_codes=known_codes)
   print(stats)
   ```

4. ファクター計算 → 特徴量構築
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   # conn は DuckDB 接続、target_date は計算基準日
   count = build_features(conn, date(2024, 1, 31))
   print(f"features upserted: {count}")
   ```

5. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   total_signals = generate_signals(conn, date(2024, 1, 31))
   print(f"signals written: {total_signals}")
   ```

6. J-Quants からの直接データ取得（テスト用途）
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
   token = get_id_token()  # settings.jquants_refresh_token を使用して取得
   rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

注意事項:
- run_daily_etl は市場カレンダーを確認し、target_date を営業日に調整して処理します。
- features / signals などへの書き込みは日付単位で置換（DELETE -> INSERT）するため冪等です。
- generate_signals はデフォルトで threshold=0.60、weights は StrategyModel.md のデフォルトに従って正規化・再スケールされます。

---

## 環境変数自動ロードの挙動

- config.Settings モジュールは、プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` および `.env.local` を自動で読み込みます。OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- 自動読み込みを無効化したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主要ファイル）

src/ 以下にパッケージが配置されています。主要な構成は以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント + 保存関数
    - news_collector.py        -- RSS 収集・保存・銘柄抽出
    - schema.py                -- DuckDB スキーマ定義・init_schema
    - stats.py                 -- zscore_normalize 等統計ユーティリティ
    - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   -- 市場カレンダー管理（is_trading_day 等）
    - features.py              -- 公開インターフェース（zscore_normalize の再エクスポート）
    - audit.py                 -- 監査ログ（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py       -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py   -- calc_forward_returns / calc_ic / factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py   -- build_features
    - signal_generator.py      -- generate_signals
  - execution/                 -- 発注層（空ファイルや将来実装想定）
  - monitoring/                -- 監視モジュール（将来実装想定）

---

## 運用上の注意・ベストプラクティス

- KABUSYS_ENV を正しく設定（development / paper_trading / live）して本番の挙動を切り替える。live 環境では特に発注フローの確認を厳格に。
- J-Quants API のレート制限（120 req/min）を順守するため、jquants_client 内で RateLimiter を実装済みです。過負荷や大量の同時リクエストは避けてください。
- トークン・パスワード等の機密情報は .env ファイルに保存する場合、アクセス制御（gitignore、シークレット管理）に注意してください。
- DuckDB によるトランザクション管理・ON CONFLICT を利用しているため、再実行時の安全性は高い設計になっています。
- ニュース収集では SSRF 対策・サイズ制限・XML パース対策（defusedxml）を実装していますが、外部フィードへの依存を運用上で監視してください。

---

## トラブルシューティング

- Settings が必須変数の未設定で失敗する:
  - ValueError が発生します。ログに表示されるキー（例: JQUANTS_REFRESH_TOKEN）を .env に設定してください。
- DuckDB に接続できない／ファイル作成権限エラー:
  - 指定した DUCKDB_PATH のディレクトリに書き込み権限があるか確認してください。
- J-Quants API の 401 が頻発する:
  - refresh token の有効期限切れや誤設定の可能性があります。get_id_token のログを確認し、refresh token を更新してください。

---

## ライセンス / 責任範囲

本 README はコードベースの概要・使い方説明にのみ焦点を当てています。実際の取引で利用する場合は、法令遵守、証券会社の取引ルール、リスク管理、および十分なバックテストと監査を行ってください。実運用に移す前に paper_trading 環境で十分に検証してください。

---

必要であれば、README に含めるサンプル .env.example、詳細な API 使用例、CI/CD の設定例、または各モジュール（strategy, research, data）の UML 図や処理フロー図を作成します。どれを追加しますか？