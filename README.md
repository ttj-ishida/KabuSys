# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ミニマム実装）。  
データ収集（J-Quants）、DuckDB スキーマ管理、ETL パイプライン、ニュース収集、特徴量計算、品質チェック、監査ログなど、アルゴリズム取引に必要な主要コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主な目的とする Python パッケージです。

- J-Quants API からの株価・財務・マーケットカレンダーの取得（レート制御、リトライ、トークン自動更新対応）
- DuckDB を用いたデータベーススキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS を用いたニュース収集と銘柄紐付け（SSRF 対策、トラッキングパラメータ除去）
- 研究用ユーティリティ（モメンタム・ボラティリティ・バリュー等のファクター計算、IC 計算、Z スコア正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）

設計方針として、外部に対する副作用（注文送信等）は最小限に抑え、DuckDB と標準ライブラリを中心に実装されています。

---

## 主な機能一覧

- 環境設定管理（`.env` / `.env.local` の自動読み込み、必須環境変数チェック）
- J-Quants クライアント
  - 株価日足 / 財務データ / マーケットカレンダー取得（ページネーション対応）
  - レートリミット・リトライ・トークン自動更新の実装
  - DuckDB への冪等保存（ON CONFLICT / DO UPDATE）
- DuckDB スキーマ定義（raw_prices, prices_daily, raw_financials, features, signals, audit テーブル等の定義と初期化）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS、URL 正規化、SSRF 対策、raw_news 保存、銘柄抽出）
- 研究用モジュール
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログテーブル（signal_events / order_requests / executions 等）

---

## 要件（依存）

最低限必要なパッケージ（例）:

- Python 3.10+
- duckdb
- defusedxml

実行環境によっては他パッケージが必要になる可能性があります（例: テスト・Slack通知など）。requirements.txt が用意されている場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローンする
   ```
   git clone <repository-url>
   cd <repository-dir>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   例:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトに requirements ファイルがあれば `pip install -r requirements.txt`）

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env`（および開発用に `.env.local`）を配置すると自動で読み込まれます。
   - 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用途）。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

   オプション:
   - KABUSYS_ENV — 実行環境: `development` / `paper_trading` / `live`（デフォルト `development`）
   - LOG_LEVEL — ログレベル: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト `INFO`）
   - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
   - SQLITE_PATH — 監視用 SQLite パスなど（デフォルト: `data/monitoring.db`）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   KABU_API_PASSWORD=xxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   Python から初期化します:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   # これで必要なテーブルとインデックスが作成されます
   ```

---

## 使い方（簡単な例）

### 日次 ETL を実行する（最小例）
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

# DB 初期化（既に初期化済みでも安全）
conn = schema.init_schema("data/kabusys.duckdb")

# ETL 実行（引数を指定しなければ今日を対象に差分取得・品質チェックを実行）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

run_daily_etl は内部で market calendar → prices → financials → 品質チェックを順番に実行します。ETLResult に処理結果や検出された品質問題・エラーが含まれます。

### ニュース収集ジョブ（RSS）
```python
from kabusys.data import schema
from kabusys.data.news_collector import run_news_collection
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う既知のコード集合（例: 上場銘柄の4桁コード）
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)
```

### J-Quants データ取得（低レベル）
```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token を用いる（環境変数経由）
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB に保存する場合:
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

### 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)

# Zスコア正規化
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

---

## 注意点 / 実装上の重要事項

- J-Quants API クライアントは 120 req/min のレートリミットを守るように実装されています（モジュール内でスロットリング）。
- HTTP エラー（408/429/5xx）に対してリトライ（指数バックオフ）を行います。401 を受けた場合はリフレッシュトークンでトークンを再取得して 1 回リトライします。
- ETL の保存処理は冪等（ON CONFLICT）で設計されているため、何度実行しても重複した行が作られにくいです。
- News Collector は SSRF 対策・XML 安全処理（defusedxml）・レスポンスサイズ制限などを実装しています。
- 環境変数の自動ロード: プロジェクトルートの `.env` → `.env.local` の順（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV の有効値: `development`, `paper_trading`, `live`。不正値を設定すると起動時に例外が投げられます。

---

## ディレクトリ構成（抜粋）

以下は主要モジュールのツリー（src 側）です。実際のリポジトリでは他のファイルやドキュメントも存在する場合があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py          # J-Quants API クライアント（取得＋保存）
      - news_collector.py          # RSS ニュース収集
      - schema.py                  # DuckDB スキーマ定義 / 初期化
      - stats.py                   # 統計ユーティリティ（zscore_normalize）
      - pipeline.py                # ETL パイプライン（差分取得/品質チェック）
      - features.py                # 特色の公開インターフェース
      - calendar_management.py     # カレンダー管理ユーティリティ
      - audit.py                   # 監査ログスキーマ・初期化
      - etl.py                     # ETL 公開インターフェース
      - quality.py                 # データ品質チェック
    - research/
      - __init__.py
      - feature_exploration.py     # 将来リターン計算・IC・summary
      - factor_research.py         # momentum/volatility/value 等
    - strategy/                     # 戦略関連（拡張領域）
      - __init__.py
    - execution/                    # 発注・実行管理（拡張領域）
      - __init__.py
    - monitoring/                   # 監視関連モジュール（未実装ファイルあり）

---

## トラブルシューティング

- .env が読み込まれない / 別の .env を使いたい
  - 自動ロードはプロジェクトルート検出（.git または pyproject.toml）を基準に行います。ユースケースに合わせて `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、任意の方法で環境変数を注入してください。
- DuckDB 初期化で失敗する
  - DB の親ディレクトリがない場合、schema.init_schema は自動で作成します。パーミッションなどを確認してください。
- API 呼び出しで 401 が頻発する
  - JQUANTS_REFRESH_TOKEN の有効性を確認してください。get_id_token により自動的に idToken を取得・更新しますが、リフレッシュトークン自体が無効だと失敗します。
- ニュース収集で XML パースエラーが出る
  - 該当フィードが非標準な形式の可能性があります。ログを確認し、特定ソースだけスキップする設定にするとよいでしょう。

---

## 開発メモ / 今後の拡張案

- strategy / execution パッケージの実装（実際の注文発行ロジック・リスク管理）
- Slack 通知やモニタリングダッシュボードとの統合
- 高度な特徴量・モデリングパイプライン（ML モデルの保存・推論）
- テストカバレッジの拡充（ネットワーク関連はモックで分離）

---

必要であれば、README に含めるコマンド例（systemd バッチ設定例や docker-compose 例）、`.env.example` のテンプレート、あるいは具体的な ETL 運用手順（cron / Airflow など）も追加で作成します。どの情報を追加したいか教えてください。