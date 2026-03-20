# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群。  
J-Quants からの市場データ取得、DuckDB によるデータ保存・スキーマ管理、研究用ファクター計算、特徴量生成、シグナル作成、ニュース収集などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は次のレイヤーで構成された日本株向け自動売買基盤のコアコンポーネント群です。

- Data Layer: J-Quants からの生データ取得、DuckDB スキーマ定義、ETL パイプライン、品質チェック
- Research Layer: ファクター計算・特徴量解析（IC/リターン計算等）
- Strategy Layer: 特徴量の正規化・合成、最終スコアからの買い/売りシグナル生成
- Execution / Audit: 発注・約定・ポジション管理や監査ログ用のスキーマ（発注クライアント実装は別）

設計上の特徴:
- DuckDB を中心としたローカルデータベース（軽量かつ高速）
- J-Quants API 用のレート制御・リトライ・トークン自動更新対応
- 研究・本番を分離（ルックアヘッドバイアス防止のため日付ベースでデータ参照）
- 冪等な DB 保存（ON CONFLICT を使用）

---

## 主な機能一覧

- J-Quants クライアント（jquants_client）
  - 日足 (OHLCV)、財務データ、JPX カレンダーの取得
  - レートリミット管理、リトライ、トークン自動更新
  - DuckDB への冪等保存ユーティリティ

- データスキーマ（data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB テーブル定義と初期化
  - インデックス定義やテーブル作成順の考慮済み

- ETL パイプライン（data.pipeline）
  - 差分取得、backfill、カレンダー前読み込み、品質チェックの統合
  - 日次 ETL 実行エントリポイント（run_daily_etl）

- ニュース収集（data.news_collector）
  - RSS フィード取得（SSRF・gzip・XML 攻撃対策）、記事正規化、銘柄抽出、DB 保存

- カレンダー管理（data.calendar_management）
  - JPX カレンダーの差分更新、営業日判定、next/prev 営業日計算

- 研究用ファクター（research.factor_research / research.feature_exploration）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算（fwd returns）、IC（Spearman）や統計サマリ

- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターのユニバースフィルタ、Zスコア正規化、features テーブルへ UPSERT

- シグナル生成（strategy.signal_generator）
  - 正規化済みファクター + AI スコアを統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL ルール、signals テーブルへの書き込み

- 統計ユーティリティ（data.stats）
  - クロスセクション Z スコア正規化等

---

## 要件

- Python 3.10 以上（型注釈で PEP 604 の `X | None` を使用）
- 必要な主なパッケージ:
  - duckdb
  - defusedxml
- （その他の依存は利用する機能により追加で必要になる可能性があります）

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクトに requirements.txt がある場合はそれを使ってください。

---

## セットアップ手順

1. リポジトリをクローン／取得

2. Python 仮想環境を作成・有効化（任意）
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 必要パッケージをインストール
```bash
pip install duckdb defusedxml
```

4. 環境変数の設定
リポジトリルートに `.env`（または `.env.local`）を配置して環境変数を定義できます。自動ロードは `kabusys.config` により行われます（CWD ではなくパッケージファイル位置からプロジェクトルートを探索）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須, 発注機能使用時）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須なら）
- DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: monitoring 用 sqlite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

自動 env 読み込みを無効化する場合:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

5. DuckDB スキーマ初期化
Python REPL やスクリプトで初期化します。

例:
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```
これにより必要なテーブルとインデックスが作成されます。

---

## 使い方（主要ワークフローの例）

以下は代表的な操作例です。実運用では監視・ログ・エラーハンドリングを追加してください。

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
```python
from kabusys.data import schema, pipeline
from kabusys.config import settings
from datetime import date

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブルに UPSERT）
```python
from kabusys.strategy import build_features
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.strategy import generate_signals
from kabusys.data import schema
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)
num_signals = generate_signals(conn, target_date=date.today())
print(f"signals written: {num_signals}")
```

- ニュース収集（RSS から raw_news 保存と銘柄紐付け）
```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 事前に取得した有効銘柄コードセットなど
results = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 開発・テスト時の注意

- DuckDB の初期化は `init_schema()` を一度呼ぶこと（既存 DB に対してはスキップして接続を返す get_connection() を利用可能）。
- J-Quants API 呼び出し部分はネットワーク依存・レート制限のため、テスト時にはモックすることを推奨します。`jquants_client._rate_limiter` や HTTP 呼び出し部分をモックできるように設計されています。
- RSS フェッチは外部 URL へのアクセスが発生するため、ユニットテストでは `news_collector._urlopen` を差し替えることができます。
- 自動環境変数ロードはテストで邪魔な場合 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

リポジトリの主要モジュール構造（提供コードに基づく）:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（取得/保存）
    - news_collector.py             # RSS ニュース収集
    - schema.py                     # DuckDB スキーマ定義と初期化
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - stats.py                      # 統計ユーティリティ（zscore_normalize 等）
    - features.py                   # features 再エクスポート
    - calendar_management.py        # 市場カレンダー更新 / 営業日判定
    - audit.py                      # 監査ログ用スキーマ
    - (その他: quality, monitoring 等が別ファイルとして存在する想定)
  - research/
    - __init__.py
    - factor_research.py            # Momentum/Volatility/Value 等の計算
    - feature_exploration.py        # 将来リターン/IC/summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py        # features テーブル構築
    - signal_generator.py           # final_score とシグナル生成
  - execution/
    - __init__.py
  - monitoring/                      # （__all__ に含むが詳細実装は別途）
  - その他のユーティリティモジュール

---

## 設計上の注意点 / 既知の制約

- DuckDB の外部キー制約や ON DELETE 動作はバージョン差で制限があるため、DDL に注釈を残しつつアプリ側で一貫性を保つ設計にしています（例: ON DELETE CASCADE を省略）。
- ニュースの ID は URL 正規化後の SHA-256 の先頭 32 文字を使用して冪等性を担保します。
- J-Quants のレートリミット（120 req/min）や 401 の自動リフレッシュ、リトライロジックなどは jquants_client に実装済みです。
- strategy 層は発注 API へ直接アクセスしません（signals テーブルまでの出力を想定）。発注は execution 層や外部コンポーネントで安全に行ってください。
- Python 3.10+ を要求します（型注釈に依存）。

---

もし README に追加したい内容（例: サンプルスクリプト、CI 設定、より詳細な環境変数一覧、運用ガイド）があれば教えてください。必要に応じて README を拡張します。