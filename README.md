# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（モジュール群）です。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含むデータ/戦略基盤を提供します。

## 概要
KabuSys は DuckDB をバックエンドに用い、J-Quants API からマーケットデータと財務データを取得して整備し、研究（research）→ 戦略（strategy）→ 発注（execution）へとつなぐための共通ユーティリティ群を実装した Python パッケージです。  
設計上の重点は次の点です。

- 冪等性（DB 保存は ON CONFLICT/トランザクションで安全に）
- ルックアヘッドバイアス回避（対象日までのデータのみ使用）
- API レート制御・リトライ・トークン自動更新
- ニュース収集時の SSRF/ZIP bomb 等のセキュリティ考慮
- DuckDB スキーマによる明示的な Raw / Processed / Feature / Execution 層

バージョン: 0.1.0

---

## 機能一覧
主な機能（モジュール）と役割：

- kabusys.config
  - .env または OS 環境変数から設定を読み込む（自動ロード機能あり）。
  - 必須設定値の検証（未設定時はエラー）。
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション、レート制御、リトライ、トークン自動更新）
  - schema: DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: ETL 実行（差分取得、保存、品質チェック呼び出し）
  - news_collector: RSS からニュース取得・前処理・DB 保存・銘柄抽出
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev 等）
  - stats: 汎用統計ユーティリティ（z-score 正規化など）
  - その他: features（再エクスポート）等
- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: raw ファクターを正規化し features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを生成
- kabusys.execution / monitoring（基盤用名前空間、実装はモジュールに依存）

---

## セットアップ手順

環境やパッケージ管理はプロジェクトの方針に合わせてください。ここでは一般的な手順例を示します。

1. Python 環境を作成（推奨: venv / pyenv / conda 等）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. パッケージ依存 (最小限)
   - 本コードで直接利用されている代表的依存: duckdb, defusedxml
   - 実運用では HTTP クライアントやロギング/監視ライブラリなどを追加する可能性あり

   例:

   ```bash
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt/pyproject.toml があればそちらを使用してください）

3. パッケージをインストール（開発モード推奨）

   ```bash
   pip install -e .
   ```

4. 環境変数の設定
   必須環境変数（settings で参照）：

   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携に使用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot Token
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意/デフォルト（例）:
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）

   .env ファイルをプロジェクトルートに置くと自動で読み込まれます（プロジェクトルートは .git または pyproject.toml を基準に検出）。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   例 .env:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（簡単な例）

以下は代表的な操作のサンプルコード（Python）です。DuckDB 接続を使ってスキーマ作成 → ETL → 特徴量生成 → シグナル生成 を順に実行する例です。

- データベース初期化（スキーマ作成）

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants から差分を取得して保存）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量作成（strategy.feature_engineering.build_features）

```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（strategy.signal_generator.generate_signals）

```python
from datetime import date
from kabusys.strategy import generate_signals

n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n}")
```

- ニュース収集ジョブ実行（RSS から raw_news を保存し銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードのセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- JPX カレンダー更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- 各処理はトランザクションで日付単位の置換（DELETE+INSERT 等）を行うため冪等的に実行できます。
- 実運用ではログ・例外ハンドリングやトークン管理（get_id_token）周りを監視すること。

---

## 開発向け & 運用メモ

- 自動 .env 読み込みはプロジェクトのルート（.git または pyproject.toml）を起点に探索します。CI/テスト等で自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings で KABUSYS_ENV（development / paper_trading / live）を指定して環境毎の挙動分岐に利用します。is_live / is_paper / is_dev のプロパティを参照できます。
- J-Quants クライアントは内部でレート制御（120 req/min）、指数バックオフ、401 のトークン自動更新を備えています。
- ニュース収集モジュールは SSRF 防止、XML の安全パース（defusedxml）、Gzip / レスポンスサイズ上限などの安全対策を組み込んでいます。
- DuckDB スキーマは data/schema.py で定義しており、init_schema() により必要なテーブルとインデックスが作成されます。既存テーブルはスキップされるため安全に再実行できます。

---

## ディレクトリ構成

主要ファイル・モジュールの構成は以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py           # RSS ニュース取得・保存
    - schema.py                   # DuckDB スキーマ定義・初期化
    - pipeline.py                 # ETL パイプライン実装
    - stats.py                    # 統計ユーティリティ（zscore 等）
    - calendar_management.py      # カレンダー更新・営業日判定
    - features.py                 # data -> features インターフェース
    - audit.py                    # 監査ログ（signal/order/execution のトレース）
    - (その他)
  - research/
    - __init__.py
    - factor_research.py          # ファクター計算（momentum/volatility/value）
    - feature_exploration.py      # IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py      # features の生成 / 正規化
    - signal_generator.py         # final_score 計算と signals テーブル生成
  - execution/                     # 発注/実行管理（パッケージ領域）
  - monitoring/                    # 監視/メトリクス（パッケージ領域）

---

## よくある質問 / 注意事項

- Q: データベースのデフォルトパスはどこですか？  
  A: settings.duckdb_path のデフォルトは data/kabusys.duckdb です。環境変数 DUCKDB_PATH で変更できます。

- Q: テスト実行時に .env の自動読み込みを無効にしたい。  
  A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みをスキップします。

- Q: J-Quants の認証トークンはどのように扱われますか？  
  A: settings.jquants_refresh_token を利用し、get_id_token() で ID トークンを取得します。jquants_client は 401 時にリフレッシュを自動で試みます。

---

この README はコードベースの主要な使い方と構成をまとめたものです。詳細な実装仕様や設計ドキュメント（StrategyModel.md、DataPlatform.md 等）がプロジェクト内にある前提で、本 README は入門的な導入ガイドを目的としています。追加のチュートリアルや運用手順はプロジェクトのドキュメントに随時追加してください。