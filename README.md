# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に使い、J-Quants から市場データ・財務データ・カレンダー・RSS ニュースを取得して保存、特徴量作成・シグナル生成・発注監査までを想定したモジュール群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つ Python モジュール群で構成されています。

- データ取得 (J-Quants API)、ニュース収集（RSS）
- DuckDB スキーマ定義と ETL パイプライン
- 研究（research）向けのファクター計算・特徴量探索ユーティリティ
- 戦略層: 特徴量の正規化・合成（feature engineering）とシグナル生成
- 実行／監査レイヤー（スキーマ／テーブル定義を含む）
- 環境変数管理（.env 自動ロード）および設定取得

設計上のポイント:
- ルックアヘッドバイアスの排除を重視（target_date 時点のデータのみ使用）
- DuckDB を中心とした冪等保存（ON CONFLICT / トランザクション）
- 外部 API 呼び出しにはレートリミッティング・リトライ・自動トークン更新を実装
- セキュリティ対策（RSS の SSRF 防止・XML の安全パース等）

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（株価日足、財務、マーケットカレンダー）
  - 保存用関数（DuckDB への冪等保存: raw_prices, raw_financials, market_calendar 等）
- ETL パイプライン
  - run_daily_etl: カレンダー・株価・財務の差分取得 + 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL
- データスキーマ
  - DuckDB スキーマ初期化（init_schema）: raw / processed / feature / execution レイヤ
- 研究用ファクター計算
  - calc_momentum / calc_volatility / calc_value（research/factor_research）
  - calc_forward_returns / calc_ic / factor_summary（feature_exploration）
  - zscore_normalize（data.stats）
- 特徴量生成 / シグナル生成
  - build_features: raw ファクターを合成・正規化して features テーブルへ
  - generate_signals: features と ai_scores を統合して signals テーブルを更新
- ニュース収集
  - fetch_rss / run_news_collection / save_raw_news / extract_stock_codes（RSS → raw_news）
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip/サイズ制限
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）、必須環境変数取得（settings オブジェクト）

---

## セットアップ手順（ローカル開発 / 実行）

以下は推奨手順の一例です。プロジェクトに setup.py / requirements.txt がある場合はそちらに従ってください。

1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

2. 必要な依存パッケージをインストール（最低限）
   - duckdb
   - defusedxml
   - （標準ライブラリ以外は環境に応じて追加してください）
   例:
   ```
   pip install duckdb defusedxml
   ```
   ※ 他に urllib/標準モジュールを使用しているため追加のパッケージは最小限です。運用時は Slack クライアント等が必要になります。

3. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと、自動でロードされます（ただしテスト等で無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（settings が _require しているもの）:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - KABU_API_PASSWORD=xxxxx
     - SLACK_BOT_TOKEN=xxxxx
     - SLACK_CHANNEL_ID=xxxxx
   - 任意:
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（簡単なコード例）

以下は基本的なワークフローの例です。

1) DuckDB スキーマ初期化（初回のみ）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL（市場カレンダー・株価・財務の取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（feature 作成）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

備考:
- jquants_client は内部でトークンを自動リフレッシュします。必要なら get_id_token を直接呼べます。
- ETL や保存関数は冪等設計（ON CONFLICT / トランザクション）です。何度実行しても重複しません。

---

## 環境変数 / 設定の説明（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / …）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化

settings = kabusys.config.settings を利用してコード内で設定を取得できます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                # .env 自動ロードと Settings
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API client + save_* 関数
    - news_collector.py      # RSS 収集・保存・銘柄抽出
    - schema.py              # DuckDB スキーマ定義・init_schema
    - stats.py               # zscore_normalize 等統計ユーティリティ
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py # market_calendar 管理、営業日関数
    - features.py            # data.stats の再エクスポート
    - audit.py               # 監査ログ用スキーマ DDL など
  - research/
    - __init__.py
    - factor_research.py     # calc_momentum / calc_volatility / calc_value
    - feature_exploration.py # calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py # build_features
    - signal_generator.py    # generate_signals
  - execution/
    - __init__.py            # (発注層用プレースホルダ)
  - monitoring/              # （モジュールは存在する想定、リポジトリに応じて存在）
  - その他（ドキュメント参照）

各ファイルには詳細な docstring と設計ノートが含まれており、内部実装の意図や制約（例: ルックアヘッド回避、トランザクションによる原子性、サイズ制限など）が明記されています。

---

## 運用上の注意 / ベストプラクティス

- 環境: 本番では KABUSYS_ENV=live を設定し、実行前に十分なテストを行ってください。
- API レート: J-Quants API はレート制限（120 req/min）があります。jquants_client 内で制御していますが、バルクリクエスト設計にも注意してください。
- DB バックアップ: DuckDB ファイルは定期バックアップを推奨します。
- セキュリティ: .env に機密情報を保存する場合、ファイルのアクセス制御を行ってください。
- テスト: settings の自動ロードはテスト時にオフにする（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）と便利です。

---

## 参考 / 次にやること

- 実際の運用では、Slack 通知・監視ジョブ・発注ブリッジ（kabu API 呼び出し）を実装して統合してください。
- テストデータ / モックを用意し、ETL・特徴量計算・シグナル生成の一貫テストを作成してください。
- 必要に応じて requirements.txt / CI 設定を追加してください。

---

必要であれば README に含めるサンプル .env.example や簡易 CLI（例: scripts/run_etl.py）を追加する README 拡張も作成できます。どの情報をより詳しく載せたいか教えてください。