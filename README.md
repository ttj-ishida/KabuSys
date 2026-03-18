# KabuSys

日本株向けの自動売買システム向けライブラリ群（データ収集・ETL・特徴量・リサーチ・監査ログ基盤など）です。  
このリポジトリは、J-Quants API からのデータ収集、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、ファクター/特徴量計算、監査ログなど、実運用を意識した機能を提供します。

主な設計方針：
- DuckDB を中心としたローカル DB による冪等的なデータ保存
- J-Quants API レート制限遵守・トークン自動リフレッシュ・リトライ
- Look-ahead bias の防止（fetched_at を記録）
- ETL は差分更新・バックフィルをサポート
- 外部依存を最小限にして標準ライブラリで保守性重視の実装

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得 API（settings）

- データ取得 / 保存（kabusys.data）
  - J-Quants API クライアント（株価 / 財務 / 市場カレンダー）
    - レートリミット制御、リトライ、トークン自動更新
  - DuckDB スキーマ定義・初期化（init_schema / get_connection）
  - ETL パイプライン（差分更新・バックフィル・品質チェック）
    - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - ニュース収集（RSS）と銘柄抽出・保存（news_collector）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal/order/execution 層）の初期化（init_audit_schema / init_audit_db）

- 特徴量 / 研究（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
    - calc_momentum, calc_volatility, calc_value
  - 将来リターン計算・IC（Information Coefficient）など
    - calc_forward_returns, calc_ic, factor_summary, rank
  - Zスコア正規化ユーティリティ（kabusys.data.stats.zscore_normalize）

- 発注 / 戦略 / 監視モジュールの骨組み（strategy, execution, monitoring）  
  （個別実装は各プロジェクト側で拡張）

---

## 前提条件

- Python 3.10+
- pip-installable な依存（最低限）:
  - duckdb
  - defusedxml

（環境に応じて追加パッケージが必要になる場合があります）

---

## セットアップ

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに requirements.txt がある場合はそれを使用してください。ここでは最低限の例）
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（ただしプロジェクトルートが特定できる場合のみ）。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（例）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

オプション（デフォルトあり）:
- KABUSYS_ENV — development|paper_trading|live（デフォルト: development）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）

例 `.env`（簡略）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## データベース初期化

DuckDB スキーマを初期化するには `kabusys.data.schema.init_schema` を使用します。

Python 例:
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

監査ログ専用 DB を別に初期化する場合:
```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## ETL 実行例

日次 ETL（カレンダー・株価・財務・品質チェック一括）を実行する例:
```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

個別ジョブ:
- run_prices_etl(conn, target_date, id_token=None, date_from=None, backfill_days=3)
- run_financials_etl(...)
- run_calendar_etl(...)

ETL 実行中は品質チェック結果（QualityIssue のリスト）が ETLResult に含まれます。

---

## ニュース収集（RSS）

RSS から記事を取得し DuckDB に保存するサンプル:
```python
from kabusys.data import news_collector, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
# 既存の銘柄コード集合（銘柄抽出に使用）, 任意
known_codes = {"7203", "6758", "9984"}

results = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

個別に RSS を取得:
- fetch_rss(url, source, timeout=30) -> list[NewsArticle]
- save_raw_news(conn, articles) -> 新規記事ID のリスト
- save_news_symbols(conn, news_id, codes) -> 保存件数

ニュース収集は SSRF 対策・応答サイズ制限・XML デフューズ処理等を組み込んで安全性を高めています。

---

## 研究・特徴量計算の使用例

DuckDB に保存した prices_daily / raw_financials を用いてファクター計算や IC（スピアマン）を行えます。

例: モメンタム計算
```python
from datetime import date
from kabusys.research import calc_momentum
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024, 1, 10))
# records は [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...]
```

将来リターンと IC 計算:
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,1,10), horizons=[1])
# factor_records は上で算出したレコード（code とファクター列を含む）
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

Zスコア正規化:
```python
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "ma200_dev"])
```

---

## 設計上の注意点 / 運用メモ

- J-Quants API はレート制限（120 req/min）を厳守するため内部でスロットリングを行います。大量取得時は時間を要する可能性があります。
- API 呼び出しで 401 が返った場合、自動でリフレッシュトークンから id_token を再取得して1回だけ再試行します。
- ETL は差分更新・backfill を行いますが、初回ロード時はデータ期間が長くなるため時間がかかります。
- DuckDB のバージョンや SQL 機能差異に注意してください（DDL や FK の一部は DuckDB のバージョン依存です）。
- 自動 env ロードはプロジェクトルート（.git または pyproject.toml）から行います。テスト等で無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

---

## 例: 簡単なワークフロー

1. DuckDB スキーマ初期化
2. run_daily_etl でデータを取得・保存
3. 研究モジュールで特徴量計算・正規化
4. 戦略層でシグナル生成（signal_events に保存）
5. 発注・監査ログとして order_requests / executions を管理

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数と設定管理
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント（取得・保存）
    - news_collector.py    — RSS ニュース収集
    - schema.py            — DuckDB スキーマ定義・初期化
    - pipeline.py          — ETL パイプライン（差分更新・ETLResult）
    - features.py          — 特徴量ユーティリティ（公開）
    - stats.py             — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py — カレンダー管理 / 営業日判定
    - audit.py             — 監査ログ DDL / 初期化
    - etl.py               — ETL 公開インターフェース
    - quality.py           — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py — 将来リターン / IC / summary
    - factor_research.py     — momentum / volatility / value
  - strategy/               — 戦略層（骨組み）
  - execution/              — 発注実装（骨組み）
  - monitoring/             — 監視 / メトリクス（骨組み）

---

## 開発・テスト

- 自動 .env ロードを無効にしてユニットテストを容易にする:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- DuckDB を使ったテストでは ":memory:" を使用すると高速に実行できます:
  ```python
  from kabusys.data import schema
  conn = schema.init_schema(":memory:")
  ```

---

貢献歓迎 / Issue・PR を立ててください。README に書かれていない使い方や追加のユーティリティを順次拡張していく予定です。