# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に用い、J-Quants API や RSS を収集して特徴量計算・シグナル生成・発注トレーサビリティまでの基盤処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を想定したモジュール群を含むパッケージです。

- データ収集（J-Quants API 経由の株価・財務・マーケットカレンダー）
- 生データ / 整形データ / 特徴量 / 発注関連の DuckDB スキーマの定義と初期化
- ETL（差分取得・保存・品質チェック）パイプライン
- ニュース収集（RSS）と記事→銘柄の紐付け
- 研究（research）向けのファクター計算・特徴量探索ユーティリティ
- 戦略：特徴量作成（正規化）およびシグナル生成（BUY/SELL）
- 発注 / 監査（audit）用のスキーマとトレーサビリティ設計
- 設定管理（環境変数 / .env 読み込み）

設計方針のポイント：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクション）
- ネットワーク・パース時の堅牢性（レートリミット、リトライ、SSRF 対策、XML セキュリティ）
- 外部依存は最小限（標準ライブラリ + 必要パッケージ）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・トークンリフレッシュ・レート制御・保存関数）
  - schema: DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: ETL 実行（market calendar / prices / financials）と品質チェック連携
  - news_collector: RSS 収集・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・翌営業日/前営業日検索・カレンダー更新ジョブ
  - stats: Zスコア正規化等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン・IC 計算・統計サマリー
- strategy/
  - feature_engineering: 生ファクターを正規化して features テーブルに保存
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成
- config: 環境変数管理（.env 自動読み込み、必須チェック）
- audit: 発注〜約定の監査テーブル定義（トレーサビリティ向け）
- execution / monitoring: 発注実装・モニタリング層（パッケージ API として公開）

---

## 動作環境 / 依存

- Python 3.10 以上（型注釈に | を使用しているため）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- （推奨）開発環境では pip と仮想環境を利用してください。

requirements.txt がない場合は最小で次をインストールしてください：

pip install duckdb defusedxml

パッケージ開発中はソースを editable インストールできます：

pip install -e .

---

## セットアップ手順

1. リポジトリをクローン、仮想環境を作成して有効化：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存のインストール：
   - pip install duckdb defusedxml

3. 環境変数の準備（.env ファイルをプロジェクトルートに配置）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID: 通知先チャンネル ID
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
   - 任意 / デフォルトあり:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN="your_refresh_token"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C12345678"
   KABU_API_PASSWORD="password"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   注意: パッケージ起動時に自動で .env をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. DuckDB スキーマ初期化：
   Python から簡単に初期化できます：

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   ```

---

## 使い方（基本的な操作例）

以下は典型的なワークフローの一例です（Python スクリプト/REPL で実行）。

1. DB 初期化（初回のみ）

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 日次ETL を実行（市場カレンダー・株価・財務の差分取得と品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

3. 特徴量の構築（target_date に対して features テーブルを作成）

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2025, 3, 1))
print(f"upserted features: {n}")
```

4. シグナル生成（features と ai_scores を基に BUY/SELL を signals テーブルへ）

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, date(2025, 3, 1))
print(f"generated signals: {count}")
```

5. ニュース収集（RSS を収集して raw_news に保存、既存記事はスキップ）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

6. J-Quants API クライアントを直接使う（テスト／差分取得用に id_token を注入可能）

```python
from kabusys.data import jquants_client as jq
from datetime import date

quotes = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
# 保存:
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, quotes)
```

注意点:
- すべての「日付基準」処理は target_date 時点のデータのみを参照しており、将来データを使わないよう設計されています。
- generate_signals は ai_scores が未登録の場合でも中立値で補完して動作します。
- ETL、API 呼び出しにはネットワークリトライやレート制御が組み込まれています。

---

## 設定（環境変数）

主要な環境変数（キー、必須/デフォルト、用途）：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API リフレッシュトークン
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- KABU_API_PASSWORD (必須 for execution) — kabuステーション API パスワード（発注を行う場合）
- KABUSYS_ENV (任意, default=development) — 実行環境: development / paper_trading / live
- LOG_LEVEL (任意, default=INFO) — ログレベル
- DUCKDB_PATH (任意, default=data/kabusys.duckdb) — DuckDB ファイルパス
- SQLITE_PATH (任意, default=data/monitoring.db) — 監視用 SQLite パス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化（テスト時など）

.env パースルールは shell 形式に近く、クォート・エスケープ・コメント等に対応します。

---

## ディレクトリ構成（抜粋）

```
src/kabusys/
├── __init__.py
├── config.py                          # 環境変数管理・Settings
├── data/
│   ├── __init__.py
│   ├── jquants_client.py              # J-Quants API クライアント + 保存関数
│   ├── schema.py                      # DuckDB スキーマ定義・初期化
│   ├── pipeline.py                    # ETL パイプライン
│   ├── news_collector.py              # RSS 収集・保存・銘柄抽出
│   ├── calendar_management.py         # カレンダー更新 / 営業日判定
│   ├── features.py                    # 公開の特徴量ユーティリティ
│   ├── stats.py                       # zscore_normalize 等
│   ├── audit.py                       # 監査ログ（order_requests, executions 等）
│   └── ... (quality, others)
├── research/
│   ├── __init__.py
│   ├── factor_research.py             # momentum/volatility/value 等
│   └── feature_exploration.py         # forward returns, IC, summary
├── strategy/
│   ├── __init__.py
│   ├── feature_engineering.py         # features テーブル構築
│   └── signal_generator.py            # signals 生成ロジック
├── execution/                         # 発注レイヤ（未実装の実装ファイル群）
├── monitoring/                        # 監視モジュール（未実装の実装ファイル群）
...
```

各モジュールは README の先頭にある docstring や関数ドキュメントで設計方針・副作用（DB 参照/更新の有無）を明示しています。実装の詳細は各ファイル内ドキュメントを参照してください。

---

## 開発 / テスト

- Python 3.10+ を使用してください。
- 単体テストフレームワークはリポジトリに含まれていませんが、各関数は依存注入（DuckDB 接続や id_token の注入）をサポートしているため、モックや一時的な in-memory DB（":memory:"）でテストが可能です。
- .env の自動読み込みを抑えたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ライセンス / 貢献

リポジトリのルートに LICENSE がある前提です。バグ報告や機能提案は Issue を立ててください。コード貢献は Pull Request を送ってください。

---

この README はコードベース内の docstring と関数設計に基づいてまとめています。実際の運用や本番発注機能を使う場合は、kabuステーション API の設定や証券会社の要件、法的・監査要件を十分ご確認ください。