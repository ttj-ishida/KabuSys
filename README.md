# KabuSys

日本株向け自動売買プラットフォームのモジュール群です。データ収集（J-Quants）、DuckDB スキーマ管理、ETL パイプライン、ニュース収集、特徴量 / リサーチユーティリティ、監査ログ用スキーマなどを含みます。本 README はコードベースに含まれる主要機能と初期セットアップ、簡単な使い方をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ基盤と研究/戦略開発に必要なユーティリティを提供する Python パッケージです。主な設計方針は以下です。

- J-Quants API からの株価・財務・カレンダーの差分取得（レート制限・再試行・トークン自動更新対応）
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution / Audit 層）
- ETL の差分更新、品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 保護・サイズ制限・トラッキング除去）
- Research 用のファクター計算（Momentum / Value / Volatility）と IC / 統計サマリ
- 発注・監査のためのスキーマと設計（冪等性、トレーサビリティ）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット、リトライ、トークンリフレッシュ、ページネーション）
  - fetch/save 系の関数（株価・財務・カレンダー）
- data/schema.py
  - DuckDB のテーブル定義と初期化（init_schema）
- data/pipeline.py
  - 日次 ETL パイプライン（差分取得、保存、品質チェック） run_daily_etl
- data/news_collector.py
  - RSS 取得・前処理・冪等保存・銘柄抽出・紐付け
- data/quality.py
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- data/calendar_management.py
  - 市場カレンダー管理（営業日判定・next/prev_trading_day 等）
- data/audit.py
  - 発注→約定までの監査用スキーマ初期化（監査DB用スキーマ）
- research/factor_research.py, feature_exploration.py
  - Momentum, Value, Volatility 等ファクター計算、forward return・IC・統計サマリ
- data/stats.py / data/features.py
  - Zスコア正規化などの統計ユーティリティ

---

## システム要件（想定）

- Python 3.10+
- DuckDB Python パッケージ
- defusedxml（RSS XML パースの安全対策）
- （必要に応じ）インターネット接続（J-Quants API / RSS）

必要なパッケージ例:
- duckdb
- defusedxml

（プロジェクトの pyproject.toml / requirements.txt があればそちらを使用してください）

---

## 環境変数 / .env

KabuSys は .env ファイル（プロジェクトルート）または環境変数から設定を読み込みます（自動ロード。ただしテスト等で無効化可）。主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite（監視 DB 等、デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

.env の読み込みルールやクォート/コメント処理は kabusys.config モジュールが担っています。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject.toml があれば pip install -e .）

4. .env を準備
   - プロジェクトルートに .env を作成し、上記必須環境変数を設定してください（.env.example があればそれを参照）。
   - 例:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで schema.init_schema を実行して DB ファイルを作成します（親ディレクトリは自動作成されます）。

   例:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings
   schema.init_schema(settings.duckdb_path)
   ```

6. 監査ログ専用 DB（必要な場合）
   - data.audit.init_audit_db を使って監査用 DB を初期化できます。

   例:
   ```python
   from kabusys.data import audit
   audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な例）

以下は主要な処理の簡単な使用例です。実運用ではログ出力や例外処理、スケジューラ（cron / Airflow 等）を組み合わせてください。

1) 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from kabusys.data import schema, pipeline
from kabusys.config import settings

# DB 初期化済みであること
conn = schema.init_schema(settings.duckdb_path)

# 当日分の ETL を実行
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

2) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）

```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

3) Research 用のファクター計算 / forward return / IC

```python
from kabusys.data import schema
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = schema.get_connection("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target)
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

4) DuckDB への保存（J-Quants 取得 → 保存）は jquants_client の fetch/save を利用します。fetch は自動的にトークンキャッシュ・ページネーションを扱います。

---

## 運用上の注意点・設計上のポイント

- J-Quants のレート制限（120 req/min）を遵守する実装（モジュール内に RateLimiter）。
- HTTP 4xx/5xx に対するリトライ（指数バックオフ）、401 ならトークン自動更新を試行。
- Data 層の保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で重複挿入を防止。
- NewsCollector は SSRF 対策、受信サイズ制限、トラッキングパラメータ除去を実装。
- market_calendar が無い場合は曜日ベースのフォールバックを使用して営業日判定を行う。
- ETL は Fail-Fast ではなく、各ステップのエラーを収集して呼び出し元で判断できるようにする。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys 以下）の主なファイルです。実際のプロジェクトには他の補助ファイルや設定ファイルがある可能性があります。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch/save）
    - news_collector.py        — RSS ニュース収集・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義・初期化
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   — 市場カレンダー管理
    - audit.py                 — 監査ログ（order_requests / executions など）
    - etl.py                   — ETL インターフェース（ETLResult 再エクスポート）
    - quality.py               — データ品質チェック
    - features.py              — 特徴量インターフェース（zscore の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Value/Volatility 計算
    - feature_exploration.py   — forward return / IC / summary
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 開発・デバッグ

- config.settings は実行時に環境変数を参照します。自動 .env ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テストや CI で自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の SQL クエリは多くの箇所でパラメータバインド（?）を使用しています。直接 SQL を編集する際はインジェクションに注意してください。
- ニュース収集などのネットワークコードはタイムアウトや例外を呼び出し元に伝播します。運用では再試行ポリシーや監視を組み合わせてください。

---

## ライセンス・貢献

（この README にライセンス情報は含まれていません。リポジトリの LICENSE ファイルを参照してください。）

貢献やバグ報告は Pull Request / Issue で受け付けてください。大きな変更を加える場合は事前に Issue で設計方針を共有してください。

---

必要であれば、具体的なスクリプト例（systemd タイマー / Airflow DAG / cron ジョブ）や CI 設定、.env.example のテンプレート、ユニットテストの書き方（jquants_client のネットワーク部分や news_collector の _urlopen をモックする方法など）も別途作成できます。どのドキュメントを優先して欲しいか教えてください。