# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants から市場データを取得して DuckDB に保存し、特徴量計算・品質チェック・監査ログ・ニュース収集などの処理を行うことを目的としています。

主な設計方針：
- DuckDB を中心としたローカルデータレイヤー（Raw / Processed / Feature / Execution）
- API 呼び出しは冪等・レート制限・リトライを備えた実装
- Look-ahead bias 回避のため取得時刻（fetched_at）を記録
- ETL / 品質チェックは Fail-Fast にしない（問題を収集して報告）
- 本番発注は strategy / execution 層で分離（このリポジトリは発注管理も想定）

バージョン: 0.1.0

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価日足 / 財務 / マーケットカレンダー）
  - データ保存（DuckDB）: raw_prices, raw_financials, market_calendar など（冪等）
- ETL パイプライン
  - 差分更新 (backfill 対応)、カレンダー先読み、品質チェック統合
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合 の検出
- ニュース収集
  - RSS フィード収集、前処理、記事ID生成、銘柄コード抽出、DuckDB への冪等保存
  - SSRF 対策 / gzip サイズ制限 / XML 安全パース 等の安全対策
- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- スキーマ管理・監査ログ
  - DuckDB スキーマ初期化（データ層・特徴量層・実行層）
  - 監査ログ（signal_events / order_requests / executions）用の初期化

---

## 必要環境 / インストール

- Python 3.10 以上（Union 表記などの構文を利用）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
```

（プロジェクトで追加パッケージが必要な場合は requirements.txt を用意して pip install -r で導入してください）

---

## 環境変数 / .env

パッケージは起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` および `.env.local` を自動ロードします（OS 環境変数を上書きしない / .env.local は上書き可）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settings で参照される主なもの）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

任意 / デフォルト値あり:

- KABUSYS_ENV: development | paper_trading | live（default: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用途の SQLite（default: data/monitoring.db）
- KABUSYS_API_BASE_URL 等（kabu API ベースURLは Settings での指定可）

サンプル `.env`（リポジトリルートに配置）:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# Optional
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンし仮想環境を作成・有効化
2. 依存パッケージをインストール（上記参照）
3. `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマ初期化

例（Python コンソール / スクリプト）:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は .env の DUCKDB_PATH を参照（未設定なら data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

監査ログテーブルを別に初期化したい場合（または既存の接続に追加する場合）:

```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema() で取得した接続
init_audit_schema(conn, transactional=True)
```

---

## 使い方（主要な例）

以下は代表的な利用例です。詳細は各モジュールを直接参照してください。

- 日次 ETL 実行（株価・財務・カレンダーの差分取得 + 品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（1 回だけ）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ実行（RSS から raw_news に保存し、銘柄紐付け）:

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- ファクター / 研究用ユーティリティ（モメンタム計算・IC 等）:

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary

conn = get_connection("data/kabusys.duckdb")
target = date(2024, 1, 15)

mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

- J-Quants 生データ取得（クライアント利用例）:

```python
from kabusys.data.jquants_client import fetch_daily_quotes
# id_token を省略するとモジュール内のキャッシュと settings.jquants_refresh_token を使って取得します
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 品質チェック単体実行:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 注意点 / 運用上のポイント

- J-Quants API のレート制限（120 req/min）や 401 リフレッシュ処理はクライアントで考慮されていますが、運用側でも適切な間隔での取得やエラーハンドリングを想定してください。
- DuckDB のファイルパスはデフォルトで data/kabusys.duckdb です。大きなデータを扱うとファイルサイズが増えるため、保存先のディスク容量に注意してください。
- 自動 .env ロードはプロジェクトルート検出に基づくため、開発環境で意図せず .env が読み込まれる場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動ロードに切り替えられます。
- ETL は品質問題をすべて報告する設計です。重大エラーが検出された場合、ETL の継続/停止は呼び出し側で判断してください。
- News Collector は外部リソースを取得するため、ネットワーク制限・RSS フォーマット差異・不正データなどを考慮してください（実装で多数の防御をしていますが追加運用ルールを推奨します）。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内の主要ファイルと役割です（src/kabusys を基準）:

- __init__.py
  - パッケージ初期化・バージョン情報
- config.py
  - 環境変数 / Settings 管理、.env 自動ロードロジック
- data/
  - jquants_client.py: J-Quants API クライアント（取得 + 保存）
  - news_collector.py: RSS ニュース収集・前処理・保存
  - schema.py: DuckDB スキーマ定義と init_schema
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - quality.py: データ品質チェック
  - stats.py: 統計ユーティリティ（zscore_normalize）
  - features.py: features の公開インターフェース
  - calendar_management.py: market_calendar 管理（営業日判定等）
  - audit.py: 監査ログ用スキーマ（signal/events/orders/executions）
  - etl.py: ETL 公開型（ETLResult の再エクスポート）
- research/
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、rank
  - factor_research.py: モメンタム / ボラティリティ / バリュー の計算
  - __init__.py: 研究系 API エクスポート
- strategy/
  - （戦略層の実装想定ファイル: 空の __init__.py が存在）
- execution/
  - （発注 / 約定管理想定ファイル: 空の __init__.py が存在）
- monitoring/
  - （監視関連: 空の __init__.py が存在）

---

## コントリビュート / 拡張案

- strategy / execution 層の具体的なブローカー連携実装（kabu API 等）
- AI スコア計算 / モデル学習パイプラインの追加
- CI / テストケース（duckdb の in-memory テスト等）
- requirements.txt / poetry / pyproject.toml による依存管理

---

README は基本的な導入・利用例を示しています。より詳細な使い方や内部設計（DataPlatform.md / StrategyModel.md 等）については、該当ドキュメントを参照のうえ各モジュール内の docstring をご確認ください。