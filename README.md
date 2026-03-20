# KabuSys

日本株向けの自動売買基盤ライブラリです。データ取得（J-Quants）、ETL、特徴量作成、戦略シグナル生成、ニュース収集、監査・取引履歴管理などを DuckDB を中心に実装しています。本 README はコードベース（src/kabusys/**）に基づく利用ガイドです。

---

## プロジェクト概要

KabuSys は日本株のデータパイプライン（株価・財務・市場カレンダー・ニュース）と、研究→運用に繋がる特徴量作成・シグナル生成の機能群を提供します。設計方針の要点：

- DuckDB をデータレイク／ワークスペースとして使用（冪等な保存を重視）
- J-Quants API を用いた差分取得・ページネーション対応・トークン自動リフレッシュ
- 研究コード（research）で算出した生ファクターを正規化して戦略へ供給
- シグナル生成は状態（Bear レジーム等）や売買ルール（ストップロス等）を考慮
- ニュース（RSS）収集は SSRF や XML 攻撃対策済み
- API 呼び出し等は再現性・トレーサビリティ重視（fetched_at、監査テーブル等）

---

## 主な機能一覧

- data
  - J-Quants クライアント（取得 + 保存: raw_prices / raw_financials / market_calendar）
  - DuckDB スキーマ定義・初期化（init_schema）
  - ETL パイプライン（差分更新、バックフィル、品質チェック）
  - ニュース収集（RSS 取得、正規化、raw_news 登録、銘柄抽出）
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - 汎用統計（Z スコア正規化）
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索ツール（forward returns / IC / サマリー等）
- strategy
  - build_features: ファクターの統合・正規化 → features テーブルへ
  - generate_signals: features / ai_scores / positions を元に BUY/SELL を生成して signals へ
- execution / monitoring / audit（基盤用のテーブル設計と一部実装）

---

## 必要条件（例）

- Python 3.9+（型アノテーション等を利用）
- duckdb
- defusedxml
- （標準ライブラリ以外に上記が最低限必要。実環境では requests 等が追加で必要になる場合あり）

簡易インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# (パッケージ化されているなら)
pip install -e .
```

パッケージに requirements.txt / pyproject.toml がある場合はそれに従ってください。

---

## 環境変数（必須／主要）

config.Settings から参照される主な環境変数:

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabu ステーション API パスワード（発注等で使用）
  - SLACK_BOT_TOKEN — Slack 通知用トークン
  - SLACK_CHANNEL_ID — Slack チャンネル ID
- 任意（デフォルトあり）
  - KABUSYS_ENV — 環境: development / paper_trading / live （デフォルト development）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — =1 を設定すると .env 自動ロードを無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定している場合、.env の自動読み込みを飛ばします
  - KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）

自動ロードの挙動:
- パッケージ起点で .git または pyproject.toml を基準にプロジェクトルートを探索し、.env/.env.local を自動で読み込みます。
- 読み込み順: OS 環境 > .env.local > .env。上書き制御あり。

例 .env（要作成）:

```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（duckdb, defusedxml 等）
4. .env を作成して環境変数を設定
5. DuckDB スキーマ初期化

例:

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 必要なら pip install -e .
# 環境変数は .env に記述
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

---

## 使い方（主要な操作例）

ここでは Python スクリプト/REPL からの利用例を示します。duckdb コネクションは kabusys.data.schema.get_connection / init_schema が返す接続を使います。

- DB 初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants からの差分取得 + 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 特徴量（features）構築

```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 3, 1))
print("features upserted:", n)
```

- シグナル生成

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 3, 1))
print("signals generated:", count)
```

- ニュース収集ジョブ（RSS）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効コードのセット（省略可能）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

- J-Quants から直接データ取得 & 保存

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")

# 取得
records = jq.fetch_daily_quotes(date_from=some_date, date_to=some_date)
# 保存（raw_prices テーブル）
saved = jq.save_daily_quotes(conn, records)
```

---

## 主要 API（要点）

- kabusys.config.settings — 環境変数から設定値を取得
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ作成
- kabusys.data.pipeline.run_daily_etl(conn, ...) — 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）
- kabusys.research.calc_momentum / calc_volatility / calc_value — ファクター計算
- kabusys.strategy.build_features(conn, target_date) — features テーブル作成
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights) — signals 作成
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — RSS 収集と保存
- kabusys.data.jquants_client — J-Quants API クライアント + 保存ユーティリティ

---

## ディレクトリ構成

以下は src/kabusys 以下の主要ファイル（抜粋）と役割です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動ロード含む）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py — RSS 収集・前処理・DB 登録
  - schema.py — DuckDB スキーマ定義・初期化
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - calendar_management.py — market_calendar 管理・営業日判定
  - audit.py — 監査ログ用 DDL（signal_events / order_requests / executions）
  - features.py — データ側の特徴量ユーティリティ公開
- src/kabusys/research/
  - __init__.py
  - factor_research.py — momentum / volatility / value の計算
  - feature_exploration.py — forward returns / IC / factor summary / rank
- src/kabusys/strategy/
  - __init__.py
  - feature_engineering.py — build_features 実装（正規化・フィルタ）
  - signal_generator.py — generate_signals 実装（スコア統合 / BUY/SELL 生成）
- src/kabusys/execution/
  - __init__.py（発注・実行層の骨格）
- その他：monitoring / logging 用のモジュールが配置される想定

（README に記載した以外にも細かなユーティリティ関数や DDL 定義が含まれます；全ファイルは src/kabusys 以下を参照してください）

---

## 注意点 / 実運用での留意点

- 環境変数／シークレットは適切に管理してください（.env を Git 管理しない等）。
- J-Quants のレート制限（120 req/min）に従う実装とリトライロジックが組み込まれていますが、ETL 実行時は API 利用上限に注意してください。
- features / signals の処理は「target_date 時点の情報のみ」を使う設計で、ルックアヘッドバイアス防止に配慮しています。外部で時刻参照を追加する場合は注意してください。
- DuckDB はファイルロック・バックアップに関する運用上の注意があるため、同時書き込みやバックアップ戦略を検討してください。
- news_collector は RSS をパースするため defusedxml を使用し、SSRF 対策／レスポンスサイズ制限等の防御ロジックを備えていますが、外部データ取り込みは常に潜在的リスクを伴います。

---

## 開発／貢献

- コードの追加や改修は各モジュールの設計方針（ドキュメント文字列）に沿って行ってください。
- テストや CI はこの README には含まれていません。ユニットテストを追加する場合は、環境変数自動ロードの副作用を避けるため KABUSYS_DISABLE_AUTO_ENV_LOAD を活用してください。

---

必要であれば、README にサンプル .env.example、requirements.txt、簡易 CLI スクリプト例や、各モジュール（pipeline, strategy, news_collector 等）のより詳しい使い方（引数一覧・戻り値・エラー挙動）を追加できます。どの部分を詳述したいか指示してください。