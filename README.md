# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
DuckDB をデータ層に使い、J-Quants API から市場データ・財務データ・カレンダーを収集し、ETL・品質チェック・特徴量生成・ニュース収集・監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群をまとめたライブラリです：

- J-Quants からの株価・財務・カレンダー取得（差分取得、ページネーション対応、レート制御、リトライ）
- DuckDB ベースのスキーマ定義と冪等保存（ON CONFLICT）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース収集（RSS からの前処理・SSRF 対策・トラッキングパラメータ除去・銘柄抽出）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー、Z スコア正規化）
- マーケットカレンダー管理（営業日判定、前後営業日・期間の営業日リスト等）
- 監査ログ（シグナル→発注→約定のトレースを可能にする監査スキーマ）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）

設計方針として、外部ライブラリへの依存を最小限にし（ただし DuckDB と defusedxml などは使用）、ETL とデータ保存を冪等に保ち、Look-ahead Bias を防ぐために取得時刻（fetched_at）を UTC で記録します。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（認証・ページネーション・レート制御・リトライ）
  - fetch/save の組み合わせで DuckDB に冪等保存
- data/schema
  - DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）定義と初期化
- data/pipeline
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）を実行
- data/news_collector
  - RSS フィードの取得、前処理、raw_news への保存、銘柄抽出、news_symbols の紐付け
- data/calendar_management
  - market_calendar の更新と営業日判定ユーティリティ
- data/quality
  - 欠損 / 重複 / スパイク / 日付不整合チェック
- research/factor_research, research/feature_exploration
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）、ファクター統計サマリー
- data/stats
  - zscore_normalize（クロスセクション Z スコア正規化）
- audit
  - 監査ログ（signal_events, order_requests, executions 等）初期化ユーティリティ

---

## 必要要件（概略）

- Python 3.10+（typing の Union 型記法などに合わせて）
- duckdb
- defusedxml

（実プロジェクトでは pyproject.toml や requirements.txt を用意してください）

---

## 環境変数 / 設定

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。設定は `kabusys.config.settings` 経由で参照できます。代表的な環境変数：

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注周り）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — 通知先チャンネルID

任意（デフォルト値あり）:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

.env 例（簡易）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## セットアップ手順（ローカル開発用の例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   # その他、実行環境に応じて追加パッケージをインストールしてください
   ```

4. 環境変数を設定（プロジェクトルートに `.env` を作る）
   - 上記の .env 例を参考に作成

5. DuckDB スキーマ初期化
   Python REPL またはスクリプトで：
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

6. （任意）監査ログ専用 DB 初期化
   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要なユースケース）

以下はライブラリの代表的な呼び出し例です。

- 日次 ETL 実行（J-Quants から差分取得して DuckDB に保存）
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

# DB 初期化（既に初期化済みならスキップ可）
conn = schema.init_schema("data/kabusys.duckdb")

# ETL 実行（今日分を対象）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に利用する銘柄コード集合（例: {"7203","6758"...}）
res = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

- 研究用ファクター計算（例：モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
today = date(2024, 1, 31)

# momentum 計算
mom = calc_momentum(conn, today)

# 将来リターン計算（翌日・5営業日・21営業日）
fwd = calc_forward_returns(conn, today, horizons=[1,5,21])

# IC 計算（例: mom_1m と fwd_1d の相関）
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

- Z スコア正規化
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

- market_calendar を利用した営業日判定
```python
from kabusys.data import calendar_management
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2024, 2, 1)
print("is trading day?", calendar_management.is_trading_day(conn, d))
print("next trading day:", calendar_management.next_trading_day(conn, d))
```

---

## よく使う API / 保存・取得の流れ（要点）

- jquants_client.fetch_* で API 取得（自動でページネーション対応）
- jquants_client.save_* で DuckDB に冪等保存（ON CONFLICT）
- data.schema.init_schema で初期スキーマを作成
- data.pipeline.run_daily_etl で日次 ETL（カレンダー→株価→財務→品質チェック）
- data.news_collector.run_news_collection で RSS 全取得→保存→銘柄紐付け
- data.quality.run_all_checks で ETL 後の品質チェックを実行

---

## ディレクトリ構成

コードベースの主要ファイルとディレクトリ（src/kabusys 以下）：

- kabusys/
  - __init__.py
  - config.py                   — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py          — RSS ニュース収集/保存/銘柄抽出
    - schema.py                  — DuckDB スキーマ定義と init_schema
    - stats.py                   — 統計ユーティリティ（zscore_normalize）
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - features.py                — 特徴量ユーティリティ（公開インターフェース）
    - calendar_management.py     — カレンダー更新・営業日ユーティリティ
    - audit.py                   — 監査ログスキーマ初期化
    - etl.py                     — ETL 結果型の再エクスポート
    - quality.py                 — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py         — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py                — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                — 発注・実行関連（拡張ポイント）
  - monitoring/
    - __init__.py                — 監視関連（拡張ポイント）

---

## 開発上の注意点 / 補足

- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）を探索します。テスト等で自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants の API 呼び出しはレート制御（120 req/min）とリトライロジックを備えています。401 を受け取った際はリフレッシュトークンで自動的にトークンを更新します。
- DuckDB の INSERT は ON CONFLICT を使って冪等に保存されます。外部から直接スキーマ操作する場合は整合性に注意してください。
- news_collector は SSRF 対策、サイズ制限、XML の安全パース（defusedxml）などを実装しています。
- research モジュールは外部 API や発注 API にアクセスしません（研究・バックテスト用に DuckDB の prices_daily / raw_financials のみを参照）。
- 監査ログ（audit）は UTC タイムスタンプで保存されることを前提にしています。

---

## 今後の拡張ポイント（例）

- 発注実行部分（kabuステーション連携）の実装とシミュレーター（paper_trading の強化）
- 戦略管理・バックテストフレームワークとの統合
- Slack 通知・監視ダッシュボードのサンプル実装
- unit tests / CI の追加（品質チェックや ETL の回帰テスト）

---

README の内容は現状コードベースの公開 API と設計ノートに基づいて作成しています。運用にあたっては J-Quants API 利用規約・証券会社 API の保安要件に従ってください。