# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル作成、ニュース収集、監査ログ・スキーマなどを含むモジュール群を提供します。

主な目的は「研究 → バックテスト → 本番運用」への橋渡しで、DuckDB を中心に冪等性・トレーサビリティ・ルックアヘッドバイアス対策を考慮して設計されています。

## 特徴（機能一覧）

- データ取得（J-Quants API）と保存
  - 株価日足（OHLCV） / 財務データ / マーケットカレンダー の取得と DuckDB への冪等保存
  - レート制御・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層を含む完全なスキーマ定義（init_schema）
- 研究用ファクター計算（research）
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials に依存）
  - 将来リターン（forward returns）、IC（Information Coefficient）計算、統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - ファクターの正規化（Z スコア）・ユニバースフィルタ適用・features テーブルへの UPSERT（build_features）
- シグナル生成（strategy.signal_generator）
  - features と AI スコアを統合して final_score を計算、BUY/SELL シグナル生成（generate_signals）
  - Bear レジーム抑制、エグジット（ストップロス等）判定
- ニュース収集（data.news_collector）
  - RSS 取得・前処理・記事ID生成（正規化 URL の SHA-256）・raw_news への冪等保存
  - SSRF 対策、gzip 上限、トラッキングパラメータ除去、銘柄コード抽出
- 監査ログ（data.audit）
  - signal → order → execution までのトレース可能な監査テーブル群
- 汎用統計ユーティリティ（data.stats）
  - クロスセクション Z スコア正規化など

## 動作要件

- Python 3.10 以上（PEP 604 の型（A | B）を使用）
- 必要なライブラリ（例）:
  - duckdb
  - defusedxml
  - これ以外は標準ライブラリ（urllib 等）を利用

推奨: 仮想環境（venv / pyenv）を利用してください。

## セットアップ手順

1. リポジトリをクローン / チェックアウト

   ```bash
   git clone <repository-url>
   cd <repository>
   ```

2. Python 仮想環境を作成・有効化（例）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール（例）

   ```bash
   pip install duckdb defusedxml
   ```

   ※プロジェクトに requirements.txt があればそれを利用してください。

4. 環境変数設定

   プロジェクトルートに `.env` / `.env.local` を置くことで自動ロードされます（優先: OS 環境 > .env.local > .env）。  
   自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用）。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト data/monitoring.db）

   .env の最小例:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```

## 使い方（クイックスタート）

以下は Python スクリプトからの利用例です。DuckDB 接続を作成し、スキーマ初期化 → ETL → 特徴量生成 → シグナル生成 の流れを示します。

1. スキーマ初期化（DuckDB の作成）

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB も可
   ```

2. 日次 ETL の実行（J-Quants からデータ取得して保存）

   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   conn = schema.get_connection("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量の構築（strategy 層に渡す features テーブルを作る）

   ```python
   from kabusys.strategy import build_features
   from datetime import date

   conn = schema.get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date.today())
   print(f"features updated: {count}")
   ```

4. シグナル生成

   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   conn = schema.get_connection("data/kabusys.duckdb")
   total_signals = generate_signals(conn, target_date=date.today())
   print(f"signals written: {total_signals}")
   ```

5. ニュース収集ジョブの例

   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   conn = schema.get_connection("data/kabusys.duckdb")
   # known_codes は銘柄コードの集合（抽出に使用）
   known_codes = {"7203", "6758", "9984", ...}
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(res)
   ```

6. J-Quants から生データを直接フェッチして保存する例

   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data import schema
   from datetime import date

   conn = schema.get_connection("data/kabusys.duckdb")
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)
   print(f"saved: {saved}")
   ```

## 主要モジュールと役割

- kabusys.config
  - 環境変数の自動ロード（.env/.env.local）と Settings クラスを提供
- kabusys.data
  - jquants_client.py : API クライアント（取得 + 保存ユーティリティ）
  - schema.py         : DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - pipeline.py       : ETL パイプライン（run_daily_etl 他）
  - news_collector.py : RSS 取得・記事保存・銘柄紐付け
  - calendar_management.py : JPX カレンダー管理ユーティリティ
  - stats.py          : zscore_normalize などの統計関数
  - features.py       : data.stats の公開再エクスポート
  - audit.py          : 発注〜約定までの監査テーブル DDL と初期化ロジック
- kabusys.research
  - factor_research.py : Momentum / Volatility / Value の計算
  - feature_exploration.py : forward returns / IC / summary / rank 等
- kabusys.strategy
  - feature_engineering.py : features の構築（build_features）
  - signal_generator.py    : generate_signals（final_score 計算・BUY/SELL 判定）
- kabusys.execution
  - （発注・注文処理層 — current tree に初期空ファイルあり。発注ロジックはここに実装）
- kabusys.monitoring
  - （監視・アラート用モジュール — 監視データベースや Slack 通知などを実装想定）

## ディレクトリ構成

プロジェクトの主要ファイル/ディレクトリ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - stats.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/
    - __init__.py
  - monitoring/
    - (監視関連モジュール)
- pyproject.toml / setup.cfg / requirements.txt (プロジェクト管理ファイル、必要に応じて追加)
- .env.example (プロジェクトルートに例を置くことを推奨)

（各モジュール内に詳細な docstring があり、関数単位で使用方法・設計方針が記載されています。まずは上記の主要関数を呼び出すことで基本動作を試せます。）

## 運用時の注意点

- DuckDB のファイルはバックアップを検討してください（履歴が重要な場合）。
- J-Quants の API レート制限（120 req/min）を遵守する設計ですが、運用側でも過度な同時実行は避けてください。
- 環境変数（トークン類）は安全に管理してください（Vault / secret manager 推奨）。
- 本番（live）環境に切り替える際は KABUSYS_ENV を `live` に設定し、紙（paper_trading）環境で十分テストしてください。
- news_collector の RSS 取得は外部ネットワーク依存です。SSRF 対策やサイズ上限が組み込まれていますが、運用で監視してください。

---

詳細な API（関数の引数・返り値・例外）は各モジュールの docstring を参照してください。必要であれば README を拡張して CLI 例・運用ガイド・テスト手順を追加します。