# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（データ収集・ETL・特徴量生成・シグナル生成・監査／実行レイヤの骨組み）

このリポジトリは、J-Quants API 等からのデータ取得、DuckDB を用いたデータ基盤、特徴量計算・正規化、戦略シグナル生成、ニュース収集、監査ログのスキーマなどを提供するモジュール群を含みます。実際のブローカー接続（発注処理）や運用ジョブは別途実装して組み合わせて使用します。

## 主要機能（抜粋）

- データ取得 / 保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）／ページネーション・リトライ・レートリミット対応
  - RSS ニュース収集（正規化、SSRF対策、サイズ制限、DOM安全対策）
  - DuckDB へ冪等保存（ON CONFLICT / トランザクション処理）
- ETL パイプライン
  - 日次の差分取得（backfill 対応）と品質チェックを含む統合 ETL（run_daily_etl）
  - 市場カレンダーの先読み更新、トレーディングデイ判定ユーティリティ
- 研究 / 戦略
  - ファクター計算（momentum / volatility / value）
  - 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
  - シグナル生成（ファクター + AI スコアの統合、BUY/SELL 生成、Bear レジーム抑制、エグジット判定）
- データ層 / スキーマ
  - Raw / Processed / Feature / Execution 層を含む DuckDB スキーマ、インデックス、初期化ユーティリティ
- 監査（audit）
  - signal -> order_request -> executions のトレーサビリティを想定した監査テーブル定義

## 要件

- Python 3.10 以上（型ヒントに | None などの構文を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- （任意）J-Quants API 利用時にネットワークアクセスが必要
- （任意）Slack 等の外部通知を使う場合は該当トークンが必要

インストール例（仮想環境を推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# プロジェクトの setup がある場合は pip install -e . を利用
```

## 環境変数 / 設定

このプロジェクトは環境変数（または .env/.env.local）から設定を読み込みます（kabusys.config.Settings）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション等の API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動で .env/.env.local をプロジェクトルートから読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

Settings は必須項目が未設定の場合に例外を投げますので、実行前に必要な環境変数を設定してください。

## セットアップ手順（簡易）

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
3. 依存パッケージをインストール
   - 例: pip install duckdb defusedxml
4. 環境変数（.env）を作成
   - リポジトリに `.env.example` がある想定でそれを参考に作成してください（本コードでは例示ファイルは提示されていません）。
5. DuckDB スキーマ初期化

```python
# 例: Python シェル / スクリプト
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

## 使い方（よく使うエントリポイント例）

以下は簡単な実行例。実際の運用ではログ設定・エラーハンドリング・ジョブスケジューラなどを組み合わせます。

- DuckDB スキーマ初期化（上記参照）:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得＋品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）作成

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"upserted features: {n}")
```

- シグナル生成

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS 取得 → DB 保存 → 銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードの集合 (例: {'7203', '6758', ...})
res = run_news_collection(conn, known_codes=set(), sources=None)
print(res)
```

- J-Quants データ取得（個別呼出し）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements, get_id_token

token = get_id_token()  # settings からトークンを取得している
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

## 注意事項 / 実運用上のポイント

- Settings は必須環境変数が未設定だと ValueError を投げます。ローカル実行時は .env に必要なキーを忘れずに設定してください。
- J-Quants の API レート制限（120 req/min）や HTTP エラーに対するリトライ・バックオフロジックが実装されています。大量の同時リクエストは避けてください。
- RSS フェッチには SSRF 対策、レスポンスサイズ制限、XML パースの安全ライブラリ（defusedxml）を使用していますが、外部フィードを追加する際は注意してください。
- DuckDB のスキーマ初期化は冪等です。既存テーブルがある場合は上書きされません。
- 戦略ロジックはルックアヘッドバイアスを避ける設計方針が取られており、target_date 時点で利用可能なデータのみを参照する実装になっています。
- 実際の証券会社への注文送信処理や Slack 通知などは、このコードベースに依存せずに別モジュールとして実装して統合することを想定しています。

## 主要なディレクトリ構成

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込み（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存ユーティリティ）
    - news_collector.py — RSS ニュース取得・正規化・保存
    - schema.py — DuckDB スキーマ定義・初期化
    - stats.py — 共通統計ユーティリティ（zscore_normalize 等）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・営業日ユーティリティ
    - audit.py — 監査ログ用スキーマ（signal / order / execution トレース）
    - features.py — data.stats のリエクスポート
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value のファクター計算
    - feature_exploration.py — forward returns / IC / summary 等の研究ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成（正規化・ユニバースフィルタ）
    - signal_generator.py — final_score 計算と BUY/SELL シグナル生成
  - execution/  (空の __init__ が存在。発注・実行レイヤはここに追加想定)
  - monitoring/ (監視用 DB 接続等を想定するモジュールを配置予定)

（上記はコードベースに含まれるファイルの主な一覧です）

## 開発 / 貢献

- 型アノテーション、ログ、冪等性、トランザクションを重視した設計になっています。新機能を追加する場合は既存の設計方針（look-ahead 回避、トランザクションの原子性、外部 API のリトライ／レート制御等）を踏襲してください。
- テストを書く際は環境変数自動ロードを無効化するため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると便利です。
- DuckDB のインメモリ接続（db_path=":memory:"）を使うとユニットテストが容易です。

---

不明点や README に追加してほしい具体的なサンプル（例: systemd タイマーでのジョブ実行例、CI ワークフロー、より詳細な .env.example など）があれば教えてください。必要に応じて追記・改善します。