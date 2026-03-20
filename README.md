# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
本リポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査ログ、発注実行レイヤー等の機能を提供します。

> 注意: 本 README はソースコード（src/kabusys/**）に基づいています。実運用で使用する場合は必ず自己責任で検証・監査を行ってください。

---

## 概要

KabuSys は以下の目的を持つモジュール群から構成されます。

- J-Quants API を利用したデータ取得（価格・財務・市場カレンダー）
- DuckDB を用いたデータベーススキーマ（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・保存・品質チェック）
- 研究用ファクター計算・特徴量エンジニアリング
- シグナル生成（複数ファクター＋AIスコアの統合）
- ニュース収集（RSS）と銘柄紐付け
- マーケットカレンダー管理（営業日判定など）
- 発注・監査ログのスキーマ（発注フローのトレーサビリティ）

設計上の特徴:
- DuckDB を中心とした軽量なオンディスク DB（":memory:" も利用可）
- 冪等（idempotent）保存処理（ON CONFLICT / upsert）
- ルックアヘッドバイアスに配慮した「その時点で利用可能なデータのみ」を使う設計
- 外部ライブラリの過度な依存を避ける（標準ライブラリ中心）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API の取得・保存（レート制御・リトライ・トークンリフレッシュ）
  - schema: DuckDB スキーマ定義と初期化（raw_prices, prices_daily, features, signals, ...）
  - pipeline: 日次 ETL（差分取得、バックフィル、品質チェック）
  - news_collector: RSS 取得・正規化・raw_news 保存・銘柄抽出
  - calendar_management: market_calendar の更新と営業日判定ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリー
- strategy/
  - feature_engineering.build_features: ファクター統合・正規化・features テーブルへの書き込み
  - signal_generator.generate_signals: features + ai_scores から BUY/SELL シグナル生成
- execution/（発注関連のプレースホルダ、将来的な実装想定）
- config: 環境変数・設定管理（.env 自動読み込みをサポート）

---

## 要件

- Python 3.10+
- 必要なライブラリ（代表例）
  - duckdb
  - defusedxml
- （実行環境に応じて）J-Quants API 利用のためのネットワークアクセス、Slack など外部サービスの認証情報

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## 環境変数（主なもの）

設定は .env ファイルまたは環境変数で行います。パッケージはプロジェクトルートの `.env` および `.env.local` を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

最低限設定が必要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知チャンネル ID（必須）

任意・デフォルトあり:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- Settings クラスは必須変数が未設定の場合 ValueError を投げます。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を検出して行われます。

---

## セットアップ手順（開発向け）

1. Python と依存ライブラリをインストール
   - Python 3.10+
   - 例: pip install duckdb defusedxml

2. リポジトリをクローンしてプロジェクトルートに移動

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成（上記を参照）

4. DuckDB スキーマを初期化
   - Python REPL やスクリプトで以下を実行:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # パスは DUCKDB_PATH に合わせてください
```

5. （任意）市場カレンダーの先読みや価格データの初回ロードは ETL を実行して行います（次節参照）。

---

## 使い方（主な操作サンプル）

以下は Python スクリプトからの利用例です。すべて duckdb 接続（kabusys.data.schema.get_connection / init_schema）を渡して操作します。

- 初期化 & ETL（日次パイプライン）:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると today が使われます
print(result.to_dict())
```

- 特徴量構築（build_features）:
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 1))
print("upserted features:", count)
```

- シグナル生成（generate_signals）:
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date(2024, 1, 1))
print("signals generated:", n)
```

- ニュース収集ジョブ（RSS 収集 → raw_news 保存 → 銘柄紐付け）:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "6501"}  # 既知銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar rows saved:", saved)
```

---

## 開発時のヒント

- テストや CI 等で自動的な .env 読み込みを無効にしたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のテーブル作成は idempotent（既存テーブルがあればスキップ）です。init_schema を安全に複数回呼べます。
- J-Quants API 呼び出しはレート制限（120 req/min）に従い自動でスロットリングされます。大量バックフィル時は制限に注意。
- RSS 収集においては SSRF / XML Bomb 等の対策が実装されています（defusedxml、ホストチェック、最大レスポンスサイズ等）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル/ディレクトリ構成（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                          -- 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py                 -- J-Quants API クライアント + 保存
    - schema.py                         -- DuckDB スキーマ定義・init_schema
    - pipeline.py                       -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py                 -- RSS 収集・保存・銘柄抽出
    - calendar_management.py            -- 市場カレンダー管理
    - stats.py                          -- zscore_normalize 等
    - features.py                       -- 再エクスポート
  - research/
    - __init__.py
    - factor_research.py                -- momentum/volatility/value 等
    - feature_exploration.py            -- 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py            -- build_features
    - signal_generator.py               -- generate_signals
  - execution/                          -- 発注層（空の __init__ 等）
  - monitoring/                         -- 監視用コード（DB/Slack 連携などを想定）
  - その他ドキュメント・設計書参照ファイル（DataPlatform.md / StrategyModel.md 等を参照）

簡易ツリー（例）
```
src/kabusys/
├─ config.py
├─ data/
│  ├─ jquants_client.py
│  ├─ schema.py
│  ├─ pipeline.py
│  ├─ news_collector.py
│  └─ ...
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ strategy/
│  ├─ feature_engineering.py
│  └─ signal_generator.py
└─ execution/
```

---

## 注意事項 / 今後の留意点

- 実発注周り（execution レイヤー）や外部ブローカー連携は慎重にテスト・監査を行ってください。二重発注・金銭的リスクが伴います。
- 本コードベースには設計ドキュメント（DataPlatform.md, StrategyModel.md 等）への依存記述があります。運用前に仕様や期待挙動を必ず理解してください。
- 本 README はコードの抜粋に基づく概要です。詳細な挙動（品質チェックのルール、AI スコアの取り扱い、重みのチューニング等）は該当ソースコード・ドキュメントを参照してください。

---

もし README に追加したい具体的な利用例（cron ジョブ設定、Docker 化、CI 設定、Slack 通知の具体的な実装例など）があれば教えてください。必要に応じてサンプルを追記します。