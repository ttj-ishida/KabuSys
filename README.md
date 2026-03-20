# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム基盤ライブラリです。  
データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ／スキーマ管理など、戦略実装と運用に必要となる主要コンポーネントを提供します。

> 現在のバージョン: 0.1.0

## 主な特徴
- J-Quants API クライアント（ページネーション、レート制御、トークン自動リフレッシュ、リトライ）
- DuckDB ベースのスキーマ定義と冪等な保存（ON CONFLICT / トランザクション）
- ETL パイプライン（差分更新、バックフィル、品質チェックフック）
- ファクター計算（Momentum / Volatility / Value 等）および Z スコア正規化ユーティリティ
- 特徴量ビルド（ユニバースフィルタ、正規化、±3 クリップ、features テーブルへの UPSERT）
- シグナル生成（ファクター + AI スコア統合、Bear レジーム抑制、BUY/SELL の日次置換）
- ニュース収集（RSS フィード、SSRF 対策、記事正規化、銘柄抽出、raw_news / news_symbols への保存）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days、カレンダー更新ジョブ）
- 監査ログ・トレーサビリティ（signal_events / order_requests / executions 等の監査テーブル）

## 必要な環境変数（主要）
以下は必須またはよく使う設定です。`.env` ファイルまたは OS 環境変数で指定します（config モジュールが自動で .env / .env.local を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`）。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン（通知を利用する場合）
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID（通知を利用する場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順（ローカル開発向け）
1. Python 3.9+ をインストールしてください（コードは typing の組み込み型注釈を利用）。
2. リポジトリをクローンしてインストール（プロジェクトに requirements.txt があればそれに従ってください）。必要な主要パッケージ:
   - duckdb
   - defusedxml
   - （その他、戦略や通知に応じて追加パッケージが必要になる可能性があります）
3. 仮想環境を作る例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # もしパッケージ化済みであれば:
   # pip install -e .
   ```
4. プロジェクトルートに `.env` を作成し、上記の必須変数を設定します。
   - テスト等で自動 .env 読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

## 基本的な使い方（コード例）
以下はライブラリの主要な流れを示す最小例です。DuckDB を初期化し、日次 ETL、特徴量構築、シグナル生成を実行する例です。

Python REPL / スクリプト例:
```python
from datetime import date
import kabusys
from kabusys.data import schema, pipeline
from kabusys.strategy import build_features, generate_signals

# 1. DuckDB スキーマ初期化（ファイル DB）
conn = schema.init_schema("data/kabusys.duckdb")

# 2. 日次 ETL を実行（J-Quants トークンは環境変数から取得される）
etl_result = pipeline.run_daily_etl(conn, target_date=date.today())
print(etl_result.to_dict())

# 3. 特徴量を生成（features テーブルへ書き込み）
n_features = build_features(conn, target_date=date.today())
print(f"features built: {n_features}")

# 4. シグナルを生成（signals テーブルへ書き込み）
n_signals = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals created: {n_signals}")
```

ニュース収集の例:
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は有効な銘柄コードセット（抽出用）
known_codes = {"7203", "6758", "9984"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

J-Quants API を直接呼ぶ例:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings.jquants_refresh_token を利用して ID トークン取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

注意: 上記関数群は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を必要とするものが多く、トランザクション管理は各関数で行われます。

## 主要モジュールと API（要約）
- kabusys.config
  - settings: 環境変数経由の設定アクセス（例: settings.jquants_refresh_token）
- kabusys.data
  - jquants_client: API 取得・保存関数（fetch_*/save_*）
  - schema: init_schema(db_path), get_connection(db_path)
  - pipeline: run_daily_etl などの ETL ワークフロー
  - news_collector: RSS 収集 / save_raw_news / extract_stock_codes / run_news_collection
  - calendar_management: is_trading_day / next_trading_day / calendar_update_job
  - stats: zscore_normalize
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- (監査 / execution / monitoring 層: スキーマ定義や雛形が含まれます）

## ディレクトリ構成（抜粋）
プロジェクトの主要ファイル・パッケージ構成は以下の通りです（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - pipeline.py
    - stats.py
    - features.py
    - calendar_management.py
    - audit.py
    - ... (raw/processed/feature layer 実装)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - __init__.py
    - feature_engineering.py
    - signal_generator.py
  - execution/  (発注/実行関連の実装が入る想定)
  - monitoring/ (監視・実行状況記録用)
  - ... その他モジュール

（各ファイルの詳しい責務はファイル冒頭の docstring に記載されています）

## 運用上の注意・設計方針（抜粋）
- ルックアヘッドバイアス防止: 計算は target_date 時点で観測可能なデータのみを使用する設計になっています。
- 冪等性: データ挿入は基本的に ON CONFLICT / トランザクションで上書き・重複排除します。
- レート制御: J-Quants クライアントは API 制限を守るための RateLimiter を実装しています。
- セキュリティ:
  - RSS フィード収集は SSRF 対策（スキーム検証、プライベート IP ブロック、リダイレクト検査）を行います。
  - XML パースは defusedxml を使用して脆弱性を緩和します。
- カレンダー未取得時のフォールバック: market_calendar が未取得の場合は曜日ベース（土日除外）で営業日判定を行います。

## 開発・貢献
- コードスタイル、追加のテスト、CI の導入を歓迎します。  
- 新しい ETL ステップや外部データソースを追加する場合は、既存のスキーマや冪等性設計（ON CONFLICT）に従ってください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行います。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定して自動読み込みを抑制できます。

---

README に記載して欲しい追加の使い方（例: CI 実行、Dockers、実運用ガイド、Slack 通知連携等）があれば教えてください。必要に応じてサンプルスクリプトや systemd / cron ジョブの例も用意します。