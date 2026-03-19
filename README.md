# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを備えたモジュール群を提供します。

現バージョン: 0.1.0

---

## 概要

KabuSys は DuckDB を中心としたデータプラットフォームと、戦略レイヤ（特徴量生成・シグナル生成）を分離して実装した日本株自動売買システム向けライブラリです。  
設計の要点:

- データ層（Raw / Processed / Feature / Execution）を DuckDB で管理（冪等な保存／DDL 定義あり）
- J-Quants API から株価・財務・カレンダーを取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- 研究（research）で作成したファクターを正規化して features テーブルへ格納
- features と AI スコアを統合して売買シグナルを生成（BUY / SELL）
- ニュース収集（RSS）と銘柄抽出
- 市場カレンダー管理（営業日判定、次/前営業日、期間内営業日リスト）
- 監査ログ（signal → order → execution のトレース）用スキーマ

---

## 主な機能

- データ取得 / ETL
  - J-Quants API クライアント（fetch/save の冪等実装）
  - 日次 ETL パイプライン（run_daily_etl）
  - 市場カレンダー差分取得（calendar_update_job）

- データベース管理
  - DuckDB スキーマ定義と初期化（init_schema）
  - 各レイヤ（raw_prices, prices_daily, features, signals, orders, executions 等）

- データ処理 / 研究
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量エンジニアリング（build_features）
  - 統計ユーティリティ（zscore_normalize, IC 計算等）
  - 特徴量探索・将来リターン解析（calc_forward_returns, calc_ic, factor_summary）

- 戦略層
  - シグナル生成（generate_signals）：features と ai_scores を用いて final_score を計算し BUY/SELL を生成

- ニュース処理
  - RSS 取得・前処理（fetch_rss）
  - raw_news / news_symbols への冪等保存（save_raw_news, save_news_symbols）
  - 銘柄コード抽出（extract_stock_codes）

- セキュリティ・堅牢性
  - RSS の SSRF 対策、受信サイズ制限、defusedxml 利用
  - API のレート制御、リトライ、トークン自動更新
  - DB トランザクションによる原子性の担保（INSERT/DELETE/ROLLBACK 処理）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 環境（3.9+ 推奨）を用意
3. 必要な Python パッケージをインストール

推奨パッケージ例（プロジェクトで使われている主要依存）:
- duckdb
- defusedxml

例（pip）:
```bash
python -m pip install duckdb defusedxml
```

4. 環境変数の設定  
`.env` ファイルまたは OS 環境変数で設定します。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須環境変数（例）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=******
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=CXXXXXXX

任意（デフォルト有り）:
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development | paper_trading | live
- LOG_LEVEL=INFO | DEBUG | WARNING | ERROR | CRITICAL

`.env` のサンプル（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=change_me
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（代表的な操作）

以下は Python REPL やスクリプトから呼び出して使う例です。DuckDB のパスは settings.duckdb_path を使うか、関数に直接渡します。

- スキーマ初期化（DuckDB の作成とテーブル生成）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

- 日次 ETL を実行（J-Quants からデータ取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量（features）を生成
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"upserted features: {count}")
```

- シグナルを生成（features と ai_scores を参照して signals テーブルに書き込み）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total}")
```

- ニュース収集ジョブを走らせる
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出のための有効コード集合（省略可）
res = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(res)  # {source_name: saved_count, ...}
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

注意点:
- run_daily_etl や fetch 系はネットワークを使います。J-Quants のレート制限（120 req/min）や API エラーに対応する実装になっていますが、運用時は適切な間隔で呼び出してください。
- generate_signals は features / ai_scores / positions を参照します。事前に features の生成や ai_scores の用意が必要です。
- 各種保存処理は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意図して実装されています。

---

## 設定と環境

主な設定は環境変数を経由して Settings クラス（kabusys.config.settings）で参照できます。重要なプロパティ:

- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path (Path 型)
- settings.sqlite_path (Path 型)
- settings.env (development|paper_trading|live)
- settings.log_level

自動で .env を読み込む仕組み:
- プロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）を探索して `.env` と `.env.local` を読み込みます。
- OS 環境変数を尊重し、`.env.local` は既存の OS 環境変数を上書きしません（保護されます）。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch/save）
    - news_collector.py        — RSS 収集・前処理・保存
    - schema.py                — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                 — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - features.py              — data API の再公開（zscore_normalize）
    - calendar_management.py   — 市場カレンダー管理（営業日判定、update_job）
    - audit.py                 — 監査ログ（signal/order/execution）スキーマ
    - (その他 data 関連モジュール)
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（mom/value/volatility）
    - feature_exploration.py   — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py   — features を構築して DB に保存
    - signal_generator.py      — final_score 計算・BUY/SELL シグナル生成
  - execution/                 — 発注・ブローカー連携層（未実装ファイルあり）
  - monitoring/                — 監視・メトリクス層（SQLite 等での監視 DB）

（上記は主要モジュール抜粋です。詳しいモジュール一覧は src/kabusys 以下を参照してください）

---

## 運用上の注意

- 本ライブラリは取引ロジック（シグナル生成）と実際の発注（execution 層）を分離する設計です。実環境で発注を行う場合は execution 層の実装と安全ガード（2段階確認、レート制御、リスク制限）を必ず組み込んでください。
- 本番環境では settings.env を `live` に設定し、ログレベルや監視を強化してください。
- ETL 実行中の品質チェック結果（quality モジュール）で致命的な問題が検出された場合は、自動的に処理を停止するのではなく管理者アラートを出すなどの運用設計を推奨します。
- ニュース収集や RSS の外部アクセスは SSRF / Gzip Bomb / XML Bomb 等の攻撃対策を講じていますが、運用ネットワークの制限（プロキシ、アウトバウンド制御）も検討してください。

---

## 開発・テスト

- 自動 env ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットして、テスト用の環境変数注入を行ってください。
- 各モジュールは外部依存を最小化する設計（標準ライブラリ中心）ですが、実行には `duckdb`、`defusedxml` などが必要です。
- 単体テスト時は DuckDB の `":memory:"` を使うと高速に DB を作成できます。

---

以上が README の概要です。必要であれば、以下について詳細を追加できます：
- .env.example の完全なテンプレート
- CI / cron での ETL・カレンダー更新・シグナル生成の運用例
- execution 層の実装ガイドライン（ブローカー API の設計）
- モジュール別 API リファレンス（関数引数・戻り値の完全表）