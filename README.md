# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants API を中心に市場データ（株価・財務・カレンダー）・ニュースを収集し、DuckDB に格納、特徴量計算 → シグナル生成 → 発注監査のワークフローを想定したモジュール群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ収集（J-Quants API）
  - 日足（OHLCV）、財務データ、JPX マーケットカレンダーの取得（ページネーション対応）
  - レート制限対応・リトライ・トークン自動更新
- DuckDB スキーマ定義・初期化（冪等）
  - Raw / Processed / Feature / Execution 層のテーブルを定義
- ETL パイプライン
  - 差分取得（最終取得日からの差分）・バックフィル・品質チェック連携
  - 日次 ETL エントリーポイント（run_daily_etl）
- ニュース収集
  - RSS 取得、前処理、記事保存、銘柄抽出（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
- 研究用ファクター計算（research）
  - Momentum / Volatility / Value の計算ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング（strategy）
  - ファクター正規化（Z スコア）、ユニバースフィルタ、features テーブルへの保存
- シグナル生成（strategy）
  - 特徴量・AI スコア統合 → final_score 計算、BUY/SELL シグナルの判定と signals への保存
- 監査・トレーサビリティ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義
- ユーティリティ
  - クロスセクション Z スコア正規化、calendar ヘルパー、その他多数

---

## 要求事項（動作環境・依存）

- Python 3.10 以上（typing における X | None 表記を使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス：J-Quants API（取得にはリフレッシュトークン）と RSS ソース
- 推奨ストレージ：DuckDB ファイル（デフォルト: data/kabusys.duckdb）

実際のインストール時は setup.py / pyproject.toml を参照して pip で依存をインストールしてください。

---

## 環境変数（必須 / 推奨）

config.Settings で参照する主な環境変数:

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード（発注連携時）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動読み込みを無効化
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルトローカル値）

簡単な .env 例（実際は .env.example を参照してください）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

config モジュールはプロジェクトルート（.git または pyproject.toml）を自動検出して `.env` / `.env.local` を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます。

---

## セットアップ手順（開発向け）

1. Python 3.10+ を用意する
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存をインストール（例）
   - pip install duckdb defusedxml
   - pip install -e .   （パッケージが pip install -e 可能な場合）
4. 環境変数を準備
   - リポジトリルートに `.env` を作成して必要なキーをセット
5. DuckDB スキーマ初期化
   - 下記「データベース初期化」を参照

---

## データベース初期化

DuckDB のスキーマを初期化してテーブルを作成します。デフォルトパスは settings.duckdb_path（デフォルト: data/kabusys.duckdb）。

Python REPL / スクリプト例:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

db_path = settings.duckdb_path  # Path オブジェクト
conn = init_schema(db_path)
# conn は duckdb.DuckDBPyConnection
```

メモリ内 DB を試す場合:
```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")
```

---

## 使い方（代表的な操作例）

以下はライブラリ関数を直接呼ぶ最小例です。実運用ではエラーハンドリング・ログ設定・スケジューリングを行ってください。

1) 日次 ETL（市場カレンダー・株価・財務の差分取得）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量構築（feature_engineering）
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features
from datetime import date

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナル生成
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import generate_signals
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
```

4) ニュース収集ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn)  # デフォルト RSS ソースを使用
print(results)
```

5) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## テスト・開発時のヒント

- config はプロジェクトルートの .env / .env.local を自動ロードします。ユニットテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと外部環境の影響を避けられます。
- ネットワーク呼び出し（J-Quants, RSS）を行う関数は id_token 注入や _urlopen のモックでテスト可能です（news_collector._urlopen など）。
- DuckDB への書き込みは多くがトランザクションでまとめられており、冪等性を考慮した実装になっています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要モジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（fetch/save）
    - news_collector.py           — RSS 収集・前処理・保存
    - schema.py                   — DuckDB スキーマ定義と初期化
    - stats.py                    — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py      — 市場カレンダー管理・ジョブ
    - audit.py                    — 発注・約定の監査テーブル定義
    - features.py                 — features の再エクスポート
  - research/
    - __init__.py
    - factor_research.py          — Momentum/Volatility/Value の計算
    - feature_exploration.py      — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py     — ファクター正規化・features 作成
    - signal_generator.py        — final_score 計算・signals 作成
  - execution/                    — 発注実行関連（初期プレースホルダ）
  - monitoring/                   — 監視・アラート関連（プレースホルダ）

各モジュールには docstring と詳細な処理設計（DataPlatform.md / StrategyModel.md 等の参照ドキュメントに準拠）を含みます。

---

## 貢献 / ライセンス

- プロジェクトに貢献する場合は、まず Issue を立てて設計方針を共有してください。テスト・ドキュメントを添えて Pull Request を送ってください。
- ライセンスはリポジトリルートの LICENSE を参照してください（本 README には含まれていません）。

---

不明点や特定機能（例: 発注連携、監査ログの利用方法、運用設計）について詳細が必要であれば教えてください。使用例やスクリプトテンプレートを追加で用意します。