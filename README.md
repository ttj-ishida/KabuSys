# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
データ収集（J-Quants）、ETL、マーケットカレンダー管理、ニュース収集、ファクター計算、特徴量生成、シグナル生成、発注履歴/監査スキーマなどを含むワンストップの基盤を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための内部ライブラリ群です。設計方針として以下を重視しています。

- データ取得の冪等性（DuckDB への ON CONFLICT / トランザクション）
- ルックアヘッドバイアスの排除（target_date 時点のデータのみ参照）
- API リトライ・レート制限・トークンリフレッシュ対応（J-Quants）
- ニュース収集の安全対策（SSRF対策、XML安全パーサ）
- テストしやすい分離（ETL は id_token 注入可 等）

主な利用対象：
- データエンジニア：J-Quants からの差分取得・品質チェック
- リサーチャー：ファクター計算 / IC 計測
- 戦略開発者：特徴量の正規化・シグナル生成
- 運用者：マーケットカレンダー・ニュース収集・監査ログ

---

## 主な機能一覧

- 環境設定管理（.env / 環境変数自動ロード、必須チェック）
- J-Quants API クライアント
  - 日足、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レート制御・リトライ・トークンリフレッシュ
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution / audit 層）
- ETL パイプライン（日次差分取得、バックフィル、品質チェック）
- 市場カレンダー管理（営業日判定・next/prev 営業日取得・更新バッチ）
- ニュース収集（RSS から記事抽出、正規化、銘柄抽出）
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（コンポーネントスコア統合、BUY/SELL 生成、売却ルール）
- 発注/監査スキーマ（注文/約定/監査ログ用DDL）
- 汎用統計ユーティリティ（Zスコア正規化、IC/ランク/サマリー等）

---

## 必要な依存関係

主要な実行時依存（プロジェクト側で適宜管理してください）：
- Python 3.9+
- duckdb
- defusedxml

（その他、標準ライブラリのみで実装されているモジュールも多いです。パッケージ化時に requirements を用意してください）

---

## セットアップ手順

1. リポジトリをクローン／プロジェクトディレクトリへ移動。

2. Python 仮想環境作成（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール（例）:
   - pip install duckdb defusedxml

   ※ 実際はパッケージ化している場合は pip install -e . や requirements.txt を使用してください。

4. 環境変数設定:
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト時等に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層で使用）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
   - その他:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/...

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化（最初に一度）:
   - Python から:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

---

## 簡単な使い方（例）

以下は最小限の Python 呼び出し例です。実運用ではログ管理や例外処理、監査ログ等を追加してください。

- DB 初期化（上記）:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次ETL（J-Quants からの差分取得 + 品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  # conn は init_schema または get_connection で得た DuckDB 接続
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 市場カレンダー更新ジョブ（夜間バッチ）:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- ニュース収集（RSS）:
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄抽出用の有効銘柄コードセット（例: {'7203','6758',...}）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 特徴量（features）生成:
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  # conn は DuckDB 接続
  n = build_features(conn, target_date=date(2025, 3, 1))
  print(f"upserted features: {n}")
  ```

- シグナル生成:
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2025, 3, 1))
  print("signals written:", total)
  ```

- J-Quants からの直接データ取得（低レベル API）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
  ```

---

## よく使う API / モジュール一覧

- kabusys.config
  - settings: 環境変数から設定値を取得（必須項目は取得時に存在チェック）
  - 自動 .env ロード機能（プロジェクトルートの .git / pyproject.toml を基準に探索）

- kabusys.data
  - schema.init_schema(db_path) / get_connection(db_path)
  - jquants_client: fetch_*/save_*（API 通信 & DuckDB 保存）
  - pipeline.run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - news_collector.run_news_collection / fetch_rss / save_raw_news
  - calendar_management: is_trading_day / next_trading_day / calendar_update_job
  - stats.zscore_normalize

- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

---

## 運用上の注意・ヒント

- 環境変数管理
  - プロジェクトルートに `.env`/.env.local を設置すると自動的に読み込まれます。テストや CI で自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB バックアップと耐障害性
  - DuckDB ファイルは定期バックアップを推奨。大規模データではファイルサイズに注意。
- レート制御
  - J-Quants API はレート制限（120 req/min）を想定。jquants_client 内で固定間隔スロットリングを実装済みですが、外部から頻繁に叩く場合はさらに配慮してください。
- ログレベル・環境
  - KABUSYS_ENV は development / paper_trading / live のいずれか。ログレベルは LOG_LEVEL で制御します。
- セキュリティ
  - news_collector は SSRF / XML Bomb 等に対策を実装していますが、RSS ソースの管理やタイムアウト等の運用設定は適切に行ってください。
- テスト
  - モジュールは外部依存（HTTP クライアント、DB）を注入可能な実装になっています。ユニットテストでは ID トークンや HTTP 層をモックしてください。

---

## ディレクトリ構成（主要ファイル）

（抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py  — RSS 収集 / 前処理 / DB 保存
    - schema.py  — DuckDB スキーマ定義 & init_schema
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - features.py, stats.py — 統計ユーティリティ
    - audit.py — 監査ログスキーマ
    - execution/ (フォルダ)
  - research/
    - __init__.py
    - factor_research.py  — momentum/volatility/value の計算
    - feature_exploration.py — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成（Zスコア正規化等）
    - signal_generator.py — final_score 計算と signals テーブル書き込み
  - execution/ (発注層用モジュール群、未実装箇所あり)
  - monitoring/ (監視関連モジュール)

---

## 開発者向けメモ

- 設計は各層（data / research / strategy / execution）を疎結合に保ち、発注層への直接依存を避けています。これによりシミュレーションやバックテストが容易です。
- 各種保存関数は冪等 (ON CONFLICT DO UPDATE / DO NOTHING) を基本としているので、再実行に安全です。
- エラー処理: ETL は Fail-Fast ではなく、各ステップを独立して継続する方針（処理中のエラーは結果オブジェクトに集約）。
- 時刻は基本的に UTC を使用して保存（jquants_client の fetched_at 等）。

---

この README はコードベースの主要機能と基本的な使い方をまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md / その他設計文書）はリポジトリ内の設計ドキュメントを参照してください。必要であれば利用例（運用スクリプト / crontab / systemd ユニット）や CI 設定のテンプレートも追加できます。