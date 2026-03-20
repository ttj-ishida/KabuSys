# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログ／スキーマ管理などを含むモジュール群を提供します。

---

## 概要

KabuSys は以下のレイヤーを想定したモジュール群で構成されています。

- Data Layer: J-Quants からのデータ取得、DuckDB スキーマ定義、ETL パイプライン、ニュース収集、カレンダー管理
- Research / Feature: ファクター計算（モメンタム、ボラティリティ、バリュー等）、特徴量探索ツール
- Strategy: 正規化済み特徴量から戦略用の特徴量作成（build_features）、最終スコア計算と売買シグナル生成（generate_signals）
- Execution / Monitoring: 発注や監査ログのためのスキーマ・基盤（発注クライアント実装は別層で想定）

設計上の特徴:
- DuckDB を中心としたローカルデータベース設計（冪等保存、トランザクション）
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- API 呼び出しに対するレート制御・リトライ・トークン自動更新
- XML / HTTP の安全対策（SSRF対策、defusedxml等）
- 外部依存を最小化し、標準ライブラリ中心で実装

---

## 主な機能一覧

- 環境設定読み込み・管理（kabusys.config）
  - .env / .env.local の自動ロード（無効化可能）
  - 必須環境変数の検証（JQUANTS_REFRESH_TOKEN 等）
- DuckDB スキーマ定義・初期化（kabusys.data.schema.init_schema）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価、財務データ、カレンダー取得
  - レートリミット、リトライ、トークン自動リフレッシュ
  - 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - 差分フェッチ、バックフィル、品質チェック呼び出し
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、記事保存、銘柄コード抽出
  - SSRF 防止、レスポンスサイズ制限、重複排除
- ファクター計算（kabusys.research.factor_research）
  - モメンタム（1/3/6M 等）、ATR、出来高/売買代金、PER/ROE
- 特徴量作成（kabusys.strategy.feature_engineering）
  - 生ファクターの統合、ユニバースフィルタ、Zスコア正規化、features テーブルへの UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - final_score 計算（momentum/value/volatility/liquidity/news の加重和）
  - Bear レジーム検出、BUY / SELL シグナル生成、signals テーブルへの日付単位置換
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions などの監査テーブル定義

---

## セットアップ手順

想定環境: Python 3.9+（typing の union 記法を利用）、仮想環境推奨。

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール（最小）
   ```bash
   pip install duckdb defusedxml
   ```
   - 他にプロジェクトの pyproject.toml や requirements.txt があればそちらを使用してください。
   - 標準ライブラリで実装されている部分が多く、依存は比較的少なめです。

3. 環境変数設定 (.env)
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を置くと自動で読み込まれます（kabusys.config）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python セッションやスクリプトから init_schema を呼び出します。

   例:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（代表的な例）

以下はライブラリ関数を直接呼ぶサンプルです。実運用ではスケジューラ（cron / Airflow 等）や CLI ラッパーを用いることを推奨します。

- DuckDB 初期化（上記と同様）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 特徴量ビルド（strategy の feature_engineering）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2024, 1, 31))
  print("features upserted:", count)
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 31))
  print("signals written:", total)
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)
  ```

- J-Quants の直接呼び出し（デバッグ向け）
  ```python
  from kabusys.data import jquants_client as jq
  # トークンは settings.jquants_refresh_token を自動利用する
  quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意:
- すべてのデータ操作は DuckDB コネクション上で行われます。init_schema() でスキーマ作成後、get_connection()/duckdb.connect() で接続してください。
- run_daily_etl などは各ステップで独立して例外処理を行い、可能な限り処理を継続する設計です。戻り値（ETLResult）で品質問題やエラーの有無を確認してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 (development / paper_trading / live)（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動ロードを無効化

必須トークンが未設定の場合、kabusys.config.Settings のプロパティアクセス時に ValueError が発生します。

---

## ディレクトリ構成（主要ファイル）

概略ツリー（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch / save）
    - schema.py                      — DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - news_collector.py              — RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py         — market_calendar 管理・営業日判定
    - features.py                    — zscore_normalize の再エクスポート
    - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                       — 監査ログ用スキーマ定義
  - research/
    - __init__.py
    - factor_research.py             — ファクター計算（momentum/volatility/value）
    - feature_exploration.py         — 将来リターン / IC / サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py         — features 作成（build_features）
    - signal_generator.py            — シグナル生成（generate_signals）
  - execution/                       — 発注層（パッケージ空の初期ファイルあり）
  - monitoring/                      — 監視・通知処理（モジュール案内用）

各ファイルや関数は README の各節やコードコメントで詳細を参照できます。

---

## 開発上の注意 / 補助情報

- DB の初期化は一度行えば以降は get_connection() を使って接続してください。init_schema() は冪等です。
- ETL の差分フェッチは internal に保存された最終日付を基に自動算出します（バックフィルにより数日前を再取得して API の後出し修正を吸収します）。
- ニュース RSS の取得では SSRF や XML Bomb、過大レスポンスを防止する実装が含まれます。ユニットテスト時はネットワーク呼び出しをモックしてください。
- シグナル生成では欠損値の扱いに注意（None は中立値 0.5 で補完する等の方針）。weights の合計は自動で正規化されます。
- ロギングは各モジュールで logger を使用しているため、ログ設定（ハンドラ・レベル）はアプリ側で制御してください。

---

必要であれば README に CLI 例や systemd / cron のジョブ設定、より詳細な DB スキーマや SQL サンプルを追加します。どの情報を優先的に追加しますか？