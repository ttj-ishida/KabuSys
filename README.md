# KabuSys

KabuSys は日本株の自動売買とリサーチのための小規模フレームワークです。  
DuckDB をデータ層に使い、データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテストまでを含む設計になっています。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（各処理は target_date 時点のデータのみを参照）
- DuckDB を用いた冪等（idempotent）なデータ保存
- API 呼び出しはレート制限とリトライを組み込む
- 研究（research）と本番（execution/backtest）を分離

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（jquants_client）：日足・財務・カレンダー取得、DuckDB への保存
  - RSS ニュース収集（news_collector）：RSS 取得・正規化・raw_news 保存・銘柄紐付け
  - ETL パイプライン（data.pipeline）：差分更新ロジック、品質チェックフック

- データスキーマ管理
  - DuckDB スキーマ定義・初期化（data.schema）：Raw / Processed / Feature / Execution 層のテーブルを作成

- 研究・特徴量
  - ファクター計算（research.factor_research）：モメンタム / ボラティリティ / バリュー等
  - 特徴量正規化（strategy.feature_engineering）：ユニバースフィルタ・Z スコア正規化・features テーブル保存
  - 特徴量探索（research.feature_exploration）：将来リターン計算・IC / 統計サマリー

- シグナル生成（strategy.signal_generator）
  - features / ai_scores を統合して final_score を算出
  - BUY / SELL 条件判定（Bear レジーム抑制、ストップロス等）
  - signals テーブルへの冪等書き込み

- バックテスト（backtest）
  - ポートフォリオシミュレータ（slippage / commission モデル）と約定ロジック
  - 日次ループでのシグナル約定・評価（engine.run_backtest）
  - バックテストメトリクス（CAGR / Sharpe / MaxDD / Win rate 等）
  - CLI エントリポイント（kabusys.backtest.run）

- ユーティリティ
  - 汎用統計（data.stats）の Z スコア正規化等
  - 環境変数管理（config）: .env 自動読込、必須チェック、環境モード判定

---

## 必要条件（推奨）

- Python 3.9+（型注釈や match 等に依存しないが、現実装の型表現に合わせるため少なくとも 3.9 以上を推奨）
- duckdb
- defusedxml
- （標準ライブラリ中心に実装されていますが、依存パッケージはプロジェクトの要件に応じて追加してください）

インストール例（仮想環境を推奨）:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install duckdb defusedxml
# パッケージ配布を想定している場合は:
# pip install -e .
```

---

## 環境変数（.env）

プロジェクトは .env / .env.local を自動でプロジェクトルート（.git または pyproject.toml を基準）から読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須・任意）：

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。jquants_client が ID トークンを取得するために使用します。

- KABU_API_PASSWORD (必須)  
  kabu ステーション API 用のパスワード（execution 層で使用）。

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン（monitoring / 通知機能で使用）。

- SLACK_CHANNEL_ID (必須)

- DUCKDB_PATH (任意)  
  デフォルト DB ファイルパス（例: data/kabusys.duckdb）。data.schema.init_schema に渡すパスのデフォルト。

- SQLITE_PATH (任意)  
  監視用 SQLite パス（monitoring 用）。

- KABUSYS_ENV (任意)  
  環境モード。`development`, `paper_trading`, `live` のいずれか（デフォルト: development）。

- LOG_LEVEL (任意)  
  ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

例（.env）:

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン・仮想環境作成

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# もしパッケージをインストール可能なら:
# pip install -e .
```

2. .env を作成（上記の必須環境変数を設定）

3. DuckDB スキーマ初期化

Python REPL またはスクリプトで:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

これで必要なテーブルが作成されます。

---

## 使い方（代表的な例）

- J-Quants からデータを取得して保存（プログラム例）

```python
from datetime import date
import duckdb
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved", saved)
conn.close()
```

- RSS を収集して raw_news に保存

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes に有効な銘柄コードセットを渡すと銘柄紐付けも行われます
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(result)
conn.close()
```

- 特徴量生成（features テーブルへ）

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,31))
print("features upserted:", n)
conn.close()
```

- シグナル生成（signals テーブルへ）

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,1,31), threshold=0.6)
print("signals written:", count)
conn.close()
```

- バックテスト（CLI）

DuckDB に事前に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を用意しておく必要があります。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

- バックテスト（プログラムから呼び出す）

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
conn.close()
```

---

## 注記 / 運用上のポイント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストや CI で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- jquants_client は API レートリミットとリトライロジック（指数バックオフ、401 トークンリフレッシュ含む）を備えていますが、実運用ではログ観察とレート設計の見直しを行ってください。
- news_collector は SSRF 対策（スキーム検証、プライベート IP ブロック、リダイレクト検査）やレスポンスサイズ制限を実装しています。
- features / signals / positions 等は「日付単位で削除してから挿入する」形（トランザクション）で冪等性を保っています。
- DuckDB のバージョンに依存する機能（外部キーの振る舞いや ON CONFLICT の挙動）に差異がある場合があります。使用する DuckDB のバージョンを固定することを推奨します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント + 保存関数
  - news_collector.py — RSS 収集・前処理・保存
  - schema.py — DuckDB スキーマ定義 / init_schema / get_connection
  - stats.py — 共通統計ユーティリティ（zscore_normalize）
  - pipeline.py — ETL パイプライン（差分更新等）
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — 特徴量生成（正規化・ユニバース）
  - signal_generator.py — final_score 計算・シグナル生成
- backtest/
  - __init__.py
  - engine.py — バックテストの全体ループ
  - simulator.py — 約定・ポートフォリオ管理・スナップショット
  - metrics.py — バックテスト評価指標計算
  - run.py — CLI エントリポイント
- execution/ — 発注関連（現状空のパッケージプレースホルダ）
- monitoring/ — 監視・通知（パッケージプレースホルダ）

---

## 開発・拡張のヒント

- 研究フェーズ（research/*）で得たファクターやモデルを strategy に持ち込み、テストを行う際は DuckDB 上で再現可能なスナップショットを作成すると便利です（バックテスト用に _build_backtest_conn があり、インメモリ DB にデータをコピーします）。
- シグナル生成の重み（weights）や閾値（threshold）は generate_signals の引数で上書き可能です。実験を簡単に行えます。
- news_collector の extract_stock_codes は単純な 4 桁数字抽出に基づくため、ノイズ除去や辞書による拡張を検討してください。
- ETL は差分更新を意図しているため、初回投入時は長期間のデータを取得する必要があります（_MIN_DATA_DATE を参照）。

---

この README はコードベースの概要と代表的な使い方をまとめたものです。より詳細な仕様（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）は別ドキュメントを参照してください（存在する場合）。README に不足している点や、実装を拡張したい箇所があれば教えてください。