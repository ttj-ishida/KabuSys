# KabuSys

日本株向けの自動売買システム基盤ライブラリです。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査ログ管理など、アルゴリズムトレーディングに必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を含むパッケージです。

- J-Quants API からの市場データ・財務データ・市場カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を使ったデータスキーマ定義と永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究（research）用のファクター計算・特徴量探索ユーティリティ
- 戦略層の特徴量作成（正規化・フィルタ）とシグナル生成ロジック（BUY/SELL）
- ニュース収集（RSS）と銘柄抽出
- マーケットカレンダー管理、監査ログ / トレーサビリティ設計
- 環境変数・設定管理（.env 読み込み・自動化）

設計上の特徴:
- ルックアヘッドバイアスを避けるため、常に target_date 時点の情報のみを利用する実装方針
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全に行う）
- 外部 API 呼び出しは data 層に集約（strategy 層や execution 層は API へ直接依存しない）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動更新）
  - schema: DuckDB のテーブル定義と初期化（init_schema）
  - pipeline: 日次差分ETL（run_daily_etl、run_prices_etl 等）
  - news_collector: RSS フィード収集と raw_news / news_symbols 保存
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリ
- strategy/
  - feature_engineering: 各ファクターを取りまとめて features テーブルへ保存（正規化・フィルタ）
  - signal_generator: features と ai_scores を統合し BUY/SELL シグナルを生成
- config: .env / 環境変数の自動読み込み・検証
- audit: 発注・約定の監査ログスキーマ（UUID ベースのトレーサビリティ）
- execution / monitoring: （骨組み、将来的な発注や監視処理のための名前空間）

---

## セットアップ手順

前提:
- Python 3.9+（コードは型ヒントにより 3.9+ を想定）
- DuckDB がインストール可能な環境

例: 仮想環境作成とインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要なパッケージをインストール（プロジェクトに requirements ファイルがあればそれを利用）
pip install duckdb defusedxml
# ローカル開発用にパッケージを editable インストールする場合
pip install -e .
```

（注意）上のインストール命令は最低限の依存のみを想定しています。実行環境や追加機能によって他のライブラリが必要になる場合があります。

.env（環境変数）設定:
- リポジトリルートに `.env` または `.env.local` を置くと自動で読み込まれます（config モジュールが .git または pyproject.toml を基準にプロジェクトルートを探索します）。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テストなどで便利）。

代表的な環境変数（README 用サンプル）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxx

# kabuステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知等に使用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX

# DB パス (任意、デフォルトは data/kabusys.duckdb)
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 動作環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要 API と実行例）

以下はライブラリを使って代表的な処理を実行するためのサンプル（Python スクリプトや REPL から実行できます）。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

# ファイルを指定（":memory:" でインメモリ DB）
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（features テーブルへの書き込み）

```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへの書き込み）

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {n}")
```

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効なコード集合（例: set of "7203","6758",...）
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)
```

6) マーケットカレンダー更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- 各処理は DuckDB コネクションを受け取り、トランザクションを利用して原子的に書き込みます。
- J-Quants の API 呼び出しには認証トークン（JQUANTS_REFRESH_TOKEN）が必要です。config.settings を通じて取得されます。

---

## 環境変数 / 設定の振る舞い

- config.Settings により必要な環境変数の存在チェックを行い、未設定の場合は ValueError を発生させます（必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
- .env / .env.local の自動読み込み順序: OS 環境 > .env.local > .env。OS 環境の変数は上書きされません。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成

以下はコードベースの主要なファイルとディレクトリの構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - schema.py
      - stats.py
      - news_collector.py
      - calendar_management.py
      - features.py
      - audit.py
      - audit (続きがあれば)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (将来的な監視ロジック置き場)
- pyproject.toml / setup.cfg / README.md (プロジェクトルート)

主要モジュール説明:
- data/schema.py: DuckDB のスキーマ定義と init_schema / get_connection を提供
- data/jquants_client.py: J-Quants API 呼び出しと保存ユーティリティ（fetch_*/save_*）
- data/pipeline.py: ETL の統合エントリ（run_daily_etl 等）
- research/*: ファクター計算・解析ユーティリティ
- strategy/*: 特徴量作成（build_features）とシグナル生成（generate_signals）
- data/news_collector.py: RSS 取得・正規化・DB 保存・銘柄抽出

---

## 依存関係（代表）

- duckdb
- defusedxml

追加のパッケージ（利用する機能による）:
- もし Slack 通知や kabu API クライアントを外部ライブラリで実装する場合はそれらが必要になります（本コード内では標準ライブラリの urllib を使用）。

requirements.txt / pyproject.toml に依存を明示してください（本 README はコード内容から推測して最低限の依存を記載しています）。

---

## 開発メモ / 注意事項

- DuckDB の SQL で日時や日付型の取り扱いに注意してください（Python 側では datetime / date オブジェクトを用います）。
- news_collector は外部 URL を取得するため SSRF 対策やレスポンスサイズ制限を実装していますが、運用時は HTTP タイムアウトやリトライポリシーを検討してください。
- J-Quants API のレート制限（120 req/min）に従う設計になっています。大量データ取得時は処理時間を見込んでください。
- strategy 層 / execution 層はできるだけ外部 API に依存しないように設計されています。発注ロジックは execution 層に実装して連携する想定です。

---

## ライセンス・貢献

この README ではライセンスやコントリビュート手順は含めていません。必要に応じてリポジトリルートに LICENSE や CONTRIBUTING.md を用意してください。

---

README に記載して欲しい追加情報（CI 手順、テスト方法、完全な依存リストなど）があれば教えてください。必要に応じて具体例やコマンドを追記します。