# KabuSys

日本株自動売買システムのコアライブラリ（リサーチ・データプラットフォーム・戦略ロジック）。  
本リポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ等の基盤機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローをサポートするライブラリ群です。主な責務は以下のとおりです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータベーススキーマ定義・初期化
- ETL パイプライン（差分取得、保存、品質チェック）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ）
- シグナル生成（最終スコア計算、BUY/SELL 生成、エグジット判定）
- ニュース収集（RSS → raw_news、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 発注/監査向けのスキーマ（execution / audit）設計（発注層は別途実装）

設計方針として、ルックアヘッドバイアスを避けるために「target_date 時点で利用可能なデータのみ」を使うこと、DB 保存は冪等（ON CONFLICT）で行うこと、外部依存を最小化してテストしやすくすることを重視しています。

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ）
  - schema: DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: ETL（差分更新・backfill・品質チェック）と日次 ETL エントリポイント
  - news_collector: RSS 収集、テキスト前処理、記事保存、銘柄抽出
  - calendar_management: JPX カレンダー管理、営業日判定ユーティリティ
  - stats: zscore_normalize 等の統計ユーティリティ
- research/
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering: 生ファクターを正規化→features テーブルへ保存
  - signal_generator: features + ai_scores を統合して final_score を算出し signals テーブルへ保存
- config: 環境変数・設定管理（.env の自動読み込み機能）
- execution, monitoring: 発注・監視層のエントリ（拡張用）

各モジュールは基本的に DuckDB 接続を受け取り、DB のテーブルのみを参照・更新します（発注 API への直接依存を持たない設計）。

---

## 必要条件

- Python 3.9+
- 主要ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワーク経由で J-Quants API を利用する場合は J-Quants の認証情報が必要

（実際の requirements.txt がある場合はそちらを利用してください。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. パッケージのインストール（開発モード）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 必要な環境変数

Settings クラスで参照される主な環境変数（必須と既定値）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, デフォルト: development) — 有効値: development, paper_trading, live
- LOG_LEVEL (任意, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると .env 自動ロードを無効化)

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 初期化（DuckDB スキーマ作成）

Python REPL かスクリプトで DuckDB のスキーマを初期化します。デフォルトの DB パスは settings.duckdb_path（例: data/kabusys.duckdb）。

例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可能
```

init_schema はテーブルをすべて作成し、DuckDB 接続オブジェクトを返します。

---

## 主要な使い方（例）

以下は主要な処理を呼び出す際の簡単なサンプルです。実運用ではログ出力やエラーハンドリングを適宜行ってください。

- 日次 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブルへの保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 10))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへの保存）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2024, 1, 10))
print(f"signals written: {total}")
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事から銘柄抽出して news_symbols に紐付ける
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

- カレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- J-Quants データ取得 API を直接利用する例
```python
from kabusys.data import jquants_client as jq
from datetime import date

data = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(data))
```

---

## 開発・テスト時の注意点

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から行われます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- J-Quants API はレート制限（120 req/min）とリトライロジックを備えています。テスト時は id_token を明示的にモック注入することを推奨します。
- DuckDB への書き込みは基本的にトランザクションで囲んでおり、冪等（ON CONFLICT）を保つ設計です。
- news_collector は SSRF・XML Bomb 等の攻撃に配慮した実装がされていますが、外部ソースを扱う際は注意してください。

---

## ディレクトリ構成

リポジトリ内のおおよその構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（fetch/save）
    - schema.py                       — DuckDB スキーマ定義・初期化
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - news_collector.py               — RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py          — 市場カレンダー管理（is_trading_day 等）
    - stats.py                        — 統計ユーティリティ（zscore_normalize 等）
    - features.py                     — data.stats の再エクスポート
    - audit.py                        — 監査ログ（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py              — momentum/volatility/value の計算
    - feature_exploration.py          — 将来リターン / IC / サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py          — features テーブル構築
    - signal_generator.py             — final_score、BUY/SELL シグナル生成
  - execution/                         — 発注層（拡張用）
  - monitoring/                        — 監視系（拡張用）

各ファイルに詳細なドキュメント文字列（docstring）が付与されています。まずは schema.init_schema、pipeline.run_daily_etl、strategy.build_features、strategy.generate_signals を触ることで主要なワークフローを把握できます。

---

## 補足・設計ノート

- ルックアヘッドバイアス対策として、すべての集計・スコア計算は target_date 時点で利用可能なデータのみを参照します。
- DB 保存はできるだけ冪等に実装しており、ETL を再実行しても二重挿入が起きないようになっています。
- jquants_client はトークンの自動リフレッシュ、リトライ、レートリミット制御を持ちます。実際の運用では API キー管理に注意してください。
- KABUSYS_ENV により挙動（live/paper_trading/development）を切り替えられます。発注ロジックを統合する際は is_live / is_paper プロパティを参照してください。

---

もし README に追加したい「デプロイ手順」「CI 実行例」「具体的な運用フロー（ポートフォリオ構築 → 発注）」などがあれば、用途に合わせたセクションを追記します。どの部分を詳細化したいか教えてください。