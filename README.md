# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
DuckDB をデータレイヤに使い、J-Quants からのデータ取得、ETL、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどの機能を提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - `.env` / 環境変数から設定を自動読み込み（プロジェクトルートを検出）
  - 必須環境変数チェックと便利なプロパティ（KABUSYS_ENV / LOG_LEVEL 等）

- データ取得・保存（J-Quants）
  - 日足（OHLCV）、四半期財務、マーケットカレンダーの取得（ページネーション対応）
  - レートリミット・リトライ・401 自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT 処理）

- ETL パイプライン
  - 差分更新、バックフィル、品質チェックを備えた日次 ETL（run_daily_etl）
  - 市場カレンダー先読み、営業日補正

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）

- ニュース収集
  - RSS フィード収集（SSRF 対策、gzip 対応、トラッキングパラメータ除去）
  - 記事ID は正規化 URL の SHA-256 を利用して冪等に保存
  - 銘柄コード抽出・news_symbols への紐付け

- 研究用ファクター計算（research）
  - Momentum / Volatility / Value 等のファクター計算と探索用ユーティリティ（IC, forward returns, summary）

- 特徴量生成（strategy）
  - research の生ファクターを正規化・合成して `features` テーブルへ保存（build_features）
  - Z スコア正規化、ユニバースフィルタ（価格・流動性）

- シグナル生成（strategy）
  - features と AI スコアを統合して final_score を計算、BUY/SELL シグナルを作成して `signals` テーブルへ保存（generate_signals）
  - Bear レジーム抑制、エグジット（ストップロス等）判定

- 監査ログ（audit）
  - シグナル → 発注 → 約定 のトレーサビリティを確保する監査テーブル定義

---

## 前提

- Python 3.10+
- 主なランタイム依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク経由で J-Quants 等へアクセスするため、対応する API トークンが必要

（プロジェクトルートに `pyproject.toml` / `requirements.txt` がある想定でセットアップしてください）

---

## セットアップ手順

1. Python 環境を準備（推奨: 仮想環境）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. 必要パッケージをインストール
   （実際のプロジェクトに requirements.txt があればそちらを使ってください。最低限の例を示します）
   ```bash
   pip install duckdb defusedxml
   ```

3. パッケージをインストール（開発モード）
   プロジェクトルートに `pyproject.toml` / `setup.py` がある場合:
   ```bash
   pip install -e .
   ```

4. 環境変数を設定
   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN（J-Quants リフレッシュトークン）
   - KABU_API_PASSWORD（kabuステーション API パスワード）
   - SLACK_BOT_TOKEN（Slack 通知用）
   - SLACK_CHANNEL_ID

   任意 / デフォルトあり:
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

   例 `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   備考:
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env` / `.env.local` を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DB スキーマ初期化
   DuckDB ファイルを初期化してテーブルを作成します:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   あるいはコマンドラインで:
   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

---

## 使い方（代表的な例）

以下は Python REPL やスクリプト内での利用例です。

- DuckDB 接続の取得（初回は init_schema を推奨）
  ```python
  from kabusys.data.schema import init_schema, get_connection

  conn = init_schema("data/kabusys.duckdb")  # テーブル作成 + 接続を返す
  # or 既存 DB に接続する場合:
  # conn = get_connection("data/kabusys.duckdb")
  ```

- 日次 ETL の実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量作成（build_features）
  ```python
  from kabusys.strategy import build_features
  from datetime import date

  n = build_features(conn, target_date=date(2025, 1, 15))
  print(f"features updated: {n}")
  ```

- シグナル生成（generate_signals）
  ```python
  from kabusys.strategy import generate_signals
  from datetime import date

  total = generate_signals(conn, target_date=date(2025, 1, 15))
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
  print(results)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants からの直接取得（トークンは settings 経由で自動取得）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  from datetime import date

  rows = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
  print(len(rows))
  ```

---

## 環境設定（重要な変数）

- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用（必須）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : ログレベル（例: INFO）

settings モジュール経由でプロパティとして取得できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、自動ロードロジック、settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - schema.py
      - DuckDB スキーマ定義と初期化（init_schema, get_connection）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - zscore_normalize の再エクスポート
    - news_collector.py
      - RSS 取得・記事保存・銘柄抽出
    - calendar_management.py
      - マーケットカレンダーの管理とユーティリティ（is_trading_day, next_trading_day 等）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions 等）
    - (その他: quality.py 等が想定される)
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等の生ファクター計算
    - feature_exploration.py
      - forward returns, IC, factor_summary, rank
  - strategy/
    - __init__.py
      - build_features, generate_signals を公開
    - feature_engineering.py
      - features テーブル生成ロジック（正規化・ユニバースフィルタ）
    - signal_generator.py
      - final_score 計算、BUY/SELL ロジック、signals テーブルへの書き込み
  - execution/
    - __init__.py
    - （発注・ブローカー連携用コードを収める想定）
  - monitoring/
    - （監視・メトリクス・アラート用コードを収める想定）

---

## 開発・運用上の注意

- Python バージョンは 3.10 以上を推奨（型ヒントに `X | Y` を使用）。
- DuckDB の特性上、大量のバルク INSERT を行うことがあるため、適切な DB ファイルのバックアップやディスク管理を行ってください。
- ニュース収集や外部 API 呼び出しでは SSRF 対策や受信サイズ制限が実装されていますが、運用環境ではネットワーク ACL やプロキシ設定も検討してください。
- KABUSYS_ENV による「本番 / ペーパー / 開発」設定を使って、実際の発注や通知の振る舞いを切り替える運用を行ってください。

---

## 貢献・ライセンス

本リポジトリにはライセンスファイルが存在する想定です。貢献する場合はコントリビューションガイドラインに従ってください（PR / Issue を作成）。

---

README は簡潔に主要な使用方法と構成をまとめています。追加の詳細（DataModel.md / StrategyModel.md / DataPlatform.md 等）やサンプルスクリプトがある場合、それらを参照して運用手順や設定を補完してください。