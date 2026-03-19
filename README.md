# KabuSys

日本株向け自動売買基盤（KabuSys）のコードベース README。  
このリポジトリはデータ収集・品質管理・特徴量生成・リサーチ・監査ログなどを含む ETL / 研究基盤と、発注ロジックを組み合わせたシステムのコアライブラリです。

---

## 概要

KabuSys は日本株に対する自動売買システムの基盤ライブラリです。  
主に以下の責務を持ちます。

- J-Quants API からの市場データ（株価日足・財務・カレンダー）取得と DuckDB への保存（冪等）
- RSS ベースのニュース収集と記事・銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 特徴量（Momentum / Value / Volatility 等）の計算・正規化
- 研究用ユーティリティ（将来リターン計算・IC 計算・統計サマリー）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）スキーマ
- 簡易な ETL パイプラインと夜間バッチジョブ
- 設定は環境変数（.env）で管理

設計方針として、本番口座や証券会社 API への直接アクセスは本コードの多くの部分では行わず（特に research / data 部分）、DuckDB 上のデータ操作と再現可能な処理に注力しています。

---

## 主な機能一覧

- data/
  - J-Quants クライアント（ページネーション・リトライ・トークン自動更新）
  - DuckDB スキーマ定義と初期化
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - RSS ニュース収集（SSRF 対策・gzip・XML セーフ化）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログ（signal_events / order_requests / executions 等）
  - 統計ユーティリティ（Zスコア正規化等）
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（将来リターン calc_forward_returns、IC calc_ic、統計サマリー）
- config
  - 環境変数管理（.env 自動ロード、必須チェック、KABUSYS_ENV / LOG_LEVEL 等）
- audit / execution / strategy / monitoring
  - 発注・監視・戦略実装のためのスケルトン（拡張用）

---

## 要件

- Python 3.10 以上（型ヒントに | 演算子、型アノテーションを利用）
- 必要なパッケージ（主なもの）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS ソース）
- J-Quants API アカウント（リフレッシュトークン）

インストール時に使う依存はプロジェクトの packaging / requirements に依存します。簡易には以下を想定してください：

pip install duckdb defusedxml

（本リポジトリをパッケージとしてインストールする場合は pyproject / setup に従ってください）

---

## セットアップ手順

1. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject があればそれに従ってください）
   - pip install -e . など

3. 環境変数 (.env) を用意
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 最低限必要な環境変数（config.Settings で必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション等の API パスワード（発注系で使用）
     - SLACK_BOT_TOKEN — Slack 通知を使う場合
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV = development | paper_trading | live  (デフォルト: development)
     - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   例 .env（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化
   - Python から以下を実行して DB とテーブルを作成します（ファイルパスは DUCKDB_PATH に合わせてください）。

   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   - 監査ログ用 DB を分けたい場合:
   ```python
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

以下はライブラリの主要な API を使う簡単な例です。各関数は DuckDB 接続を受け取り、明示的にトランザクションを管理できます。

1. 日次 ETL を実行する（市場カレンダー・株価・財務の差分取得と品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data import pipeline, schema

# DB 初期化済みを前提
conn = schema.init_schema("data/kabusys.duckdb")  # 初回のみ実行すれば良い

# 日次 ETL を実行（id_token を渡すとテストでトークンを注入可能）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2. ニュース収集ジョブを走らせる

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# 既知の銘柄コードセットを渡すと記事と銘柄の紐付けを行います
known_codes = {"7203", "6758", "9432"}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

3. 特徴量 / ファクター計算（リサーチ）

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data import stats

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2024, 1, 31)

mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)

# 将来リターン（翌日・5日・21日）
fwd = calc_forward_returns(conn, t, horizons=[1,5,21])

# IC の計算（例: mom_1m と fwd_1d の相関）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

# 統計サマリー
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
print(summary)

# Z-score 正規化
normed = stats.zscore_normalize(mom, ["mom_1m", "mom_3m"])
```

4. 市場カレンダー操作

```python
from datetime import date
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
d = date(2024, 1, 1)
is_trade = calendar_management.is_trading_day(conn, d)
next_td = calendar_management.next_trading_day(conn, d)
```

5. J-Quants からデータを直接取得して保存

```python
from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API の refresh token
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知を有効にする場合
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
- LOG_LEVEL — ログレベル（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定するとパッケージ起動時の .env 自動ロードを無効化

設定不足（必須キー未設定）は config.Settings のプロパティアクセス時に ValueError を送出します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理（.env 自動ロード、必須チェック）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（リトライ・レート制御・保存関数）
  - news_collector.py — RSS 取得・前処理・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETL の公開型エイリアス（ETLResult）
  - features.py — zscore 正規化の再エクスポート
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付）
  - calendar_management.py — 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit.py — 監査ログスキーマ（signal_events / order_requests / executions）
  - pipeline.py (上記)
- research/
  - __init__.py — research の公開 API
  - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - factor_research.py — momentum / value / volatility の実装
- strategy/
  - __init__.py (拡張ポイント)
- execution/
  - __init__.py (拡張ポイント)
- monitoring/
  - __init__.py (拡張ポイント)

（上記はコードベースに含まれる主要ファイルを抜粋したものです）

---

## 開発・運用上の注意点 / トラブルシューティング

- .env の自動読み込みはプロジェクトルート（.git もしくは pyproject.toml を基準）を探索して行います。テストなどで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API のトークン周り:
  - get_id_token はリフレッシュトークンから id_token を取得します。_request は 401 を受けた際に自動で1回だけリフレッシュを試みます。
- DuckDB ファイルパスの親ディレクトリが存在しない場合は schema.init_schema / init_audit_db が自動作成しますが、パーミッション等に注意してください。
- news_collector は外部 RSS を取得するため SSRF 対策が実装されています（スキームチェック、プライベートアドレスブロック、リダイレクト検査など）。社内のプロキシや特殊なネットワーク環境では注意が必要です。
- quality.run_all_checks はエラー・警告を収集して返します。ETL の継続・停止判断は運用側で行ってください（Fail-Fast ではありません）。
- Python バージョンは 3.10 以上を推奨します。

---

## 貢献・拡張ポイント

- strategy / execution / monitoring パッケージは拡張用に空の __init__ が存在します。実際のシグナル生成や証券会社とのラッパー実装はここに追加してください。
- 特徴量・AI スコアリング・ポートフォリオ最適化は features / research を基に自由に実装可能です。
- 監査ログと発注フローの結合（order_request_id を用いた冪等処理、ブローカーコールバックの取り込み）を実際のブローカー API に合わせて実装してください。

---

必要であれば、README に含めるサンプルスクリプト（cron 用、systemd 用、Dockerfile/Compose など）、または CI 用の簡易テスト手順を追加できます。どの情報を優先して追記するか教えてください。