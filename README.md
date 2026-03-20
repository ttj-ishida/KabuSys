# KabuSys

日本株自動売買システムのコアライブラリ（モジュール群）。データ取得・ETL、特徴量計算、シグナル生成、ニュース収集、DuckDB スキーマ定義など、戦略実行に必要な基盤処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォームのコアコンポーネント群です。主な目的は以下です。

- J-Quants API からの市場データ・財務データの取得と DuckDB への永続化（ETL）
- RSS ベースのニュース収集と記事⇄銘柄の紐付け
- 研究（research）モジュールでのファクター計算・解析
- 戦略（strategy）層での特徴量正規化・シグナル生成
- スキーマ定義・データ品質チェック・カレンダー管理等のインフラ機能
- 発注層（execution）やモニタリング（monitoring）用のインタフェースを想定（モジュール分割済み）

設計方針として、ルックアヘッドバイアスの防止、冪等性（DB側 ON CONFLICT / トランザクション）、外部依存の最小化（標準ライブラリ中心）を重視しています。

---

## 機能一覧

- 環境管理
  - .env/.env.local からの自動ロード（`kabusys.config.Settings`）
  - 必須環境変数チェック
- データ取得（J-Quants クライアント）
  - 株価日足（ページネーション対応、レート制限・リトライ・トークンリフレッシュ）
  - 財務データ
  - マーケットカレンダー
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）
- ETL パイプライン
  - 差分更新ロジック（最終取得日からの差分取得／バックフィル）
  - 日次 ETL 実行エントリ（`run_daily_etl`）
  - 品質チェック（quality モジュールに基づく。quality は別途実装想定）
- スキーマ管理
  - DuckDB のスキーマ初期化（raw / processed / feature / execution 層）
  - インデックス作成・DDL 定義
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 対応、XML 攻撃対策）
  - 記事正規化（URL トラッキング除去、ID は URL 正規化の SHA-256 ハッシュ）
  - raw_news / news_symbols への冪等保存
  - 銘柄コード抽出（4桁コード）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Spearman）・統計サマリー
  - z-score 正規化ユーティリティ
- 戦略（strategy）
  - 特徴量構築（正規化・ユニバースフィルタ）: `build_features`
  - シグナル生成（final_score 計算、BUY/SELL 生成）: `generate_signals`
  - Bear レジーム判定、エグジット（ストップロス等）判定
- その他ユーティリティ
  - マーケットカレンダー操作（営業日／次営業日／営業日リスト）
  - 統計ユーティリティ（zscore_normalize 等）

---

## 必要条件 / 依存関係

最小限で動かす場合の主要依存:

- Python 3.9+
- duckdb
- defusedxml

（プロジェクト側で Slack 通知や kabu ステーション連携を使う場合は別途 slack-sdk や証券会社 API クライアントなどが必要）

インストール例（仮）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発パッケージがあれば `pip install -e .` など
```

※ 実際のパッケージング / requirements.txt はリポジトリに合わせて用意してください。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化する

2. パッケージ依存をインストールする（上記参照）

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定します。
   - 自動ロード: `kabusys.config` はプロジェクトルート（.git または pyproject.toml を探します）から `.env`/.env.local を自動読み込みします。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 `.env`（必須キー）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
# オプション DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマ初期化

Python REPL またはスクリプトで:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイル DB を作成・スキーマ初期化
conn.close()
```

---

## 使い方（代表的なワークフロー）

以下はライブラリ API を直接呼ぶ例です。運用ジョブ（systemd / cron / Airflow 等）から呼び出せるように設計されています。

- 日次 ETL を実行してデータを取得・保存する:

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化済みを想定
conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量を構築する（features テーブルへ保存）:

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 15))
print(f"built features for {n} symbols")
```

- シグナルを生成する（signals テーブルへ保存）:

```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 15))
print(f"generated {count} signals")
```

- ニュース収集ジョブを実行する:

```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar records: {saved}")
```

---

## 主要モジュール / API（要点）

- kabusys.config
  - settings: 環境変数取得用プロパティ（例: settings.jquants_refresh_token）
- kabusys.data.jquants_client
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - get_id_token
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection / extract_stock_codes
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

詳細な関数の挙動やパラメータは各モジュールの docstring を参照してください。

---

## ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         # 環境設定・.env 自動ロード
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント + 保存ロジック
    - news_collector.py               # RSS ニュース収集・保存
    - pipeline.py                     # ETL パイプライン
    - schema.py                       # DuckDB スキーマ定義・初期化
    - stats.py                        # 統計ユーティリティ（zscore_normalize）
    - features.py                     # features への公開インターフェース
    - calendar_management.py          # カレンダー管理・更新ジョブ
    - audit.py                        # 監査ログテーブル定義
  - research/
    - __init__.py
    - factor_research.py              # ファクター計算（momentum/value/volatility）
    - feature_exploration.py          # 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py          # 正規化・ユニバースフィルタ・features 保存
    - signal_generator.py             # final_score 計算・BUY/SELL 判定・signals 保存
  - execution/
    - __init__.py                     # 発注層インタフェース（将来的に実装）
  - monitoring/                       # 監視・アラート用（将来的に実装）

---

## 運用上の注意

- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかを指定してください。`settings.is_live` などで判定できます。
- J-Quants API はレート制限（120 req/min）があります。クライアントは固定間隔スロットリングと指数バックオフを組み合わせて制御していますが、運用側でも並列実行に注意してください。
- DuckDB スキーマは冪等で作成されます。初回は init_schema() を呼び出してから ETL を実行してください。
- ニュース収集では SSRF 対策・XML サニタイズを実装していますが、外部フィード URL の管理・監視は重要です。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env 自動ロードを無効化できます（テスト時に有用）。

---

## 貢献 / 拡張案

- execution 層のブローカー API 実装（kabuステーション連携、発注の信頼性向上）
- 品質チェックモジュール（quality）の拡充と自動アラート
- Slack 通知やダッシュボード連携の強化（monitoring）
- テストカバレッジの整備（ユニット・統合テスト）

---

この README はコードベース内の docstring と実装方針に基づいて作成しています。実際の運用時は secrets の管理（Vault 等）、CI/CD、監視の導入を合わせて検討してください。質問や追加したい内容があれば教えてください。