# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB を中心に「データ収集（J-Quants）→ 前処理 → 特徴量作成 → シグナル生成 → 発注（実装層）」のワークフローをサポートします。研究用の factor 計算や品質チェック、ニュース収集機能（RSS）なども含まれます。

---

## プロジェクト概要

- データ取得：J-Quants API から株価・財務・カレンダー等を取得（rate limit / retry / token refresh 対応）。
- データ保存：DuckDB に Raw / Processed / Feature / Execution 層のスキーマを提供し冪等的に保存。
- ETL：差分更新（バックフィル含む）・品質チェックを行う日次 ETL。
- 研究機能：ファクター計算（Momentum / Volatility / Value）・特徴量探索（IC 等）。
- 戦略：Z スコア正規化済み特徴量と AI スコアを統合して売買シグナルを生成（BUY/SELL）。
- ニュース：RSS 取得・前処理・記事保存・銘柄抽出の安全なパイプライン。
- 設定管理：.env / .env.local / OS 環境変数から設定を読み込み（自動ロード可／無効化可）。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・トークンリフレッシュ・再試行・レート制御）
  - schema: DuckDB スキーマ定義と初期化（raw/processed/feature/execution 層）
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）
  - news_collector: RSS 取得・前処理・DB保存・銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: Z スコア正規化などの統計ユーティル
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン・IC・統計サマリ
- strategy/
  - feature_engineering: 生ファクターを正規化・合成して features テーブルへ保存
  - signal_generator: features + ai_scores から final_score を算出し signals を生成
- execution/: 発注・執行層（骨組み）

---

## 必要な環境変数

config.Settings で参照される必須・任意の主な環境変数:

必須（実行に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV — "development", "paper_trading", "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG","INFO",...（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" にすると .env 自動読込を無効化
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API の base URL（デフォルトローカル）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があればそれを使用）

3. 環境変数を設定
   - プロジェクトルートに `.env` ファイルを作成するか、OS 環境変数を直接設定。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. DuckDB スキーマの初期化（例）
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")  # ディレクトリは自動作成されます
     ```

---

## 使い方（代表的な操作）

以下は代表的なワークフローと簡単なコード例です。関数はすべて DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

- 日次 ETL（データ収集 → 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量のビルド（features テーブルへ書き込み）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

- シグナル生成（signals テーブルへ書き込み）
```python
from datetime import date
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today())
print(f"signals generated: {count}")
```

- RSS ニュース収集（news_collector の統合ジョブ）
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
# known_codes は既存の銘柄リスト（set of str）を渡すと銘柄紐付けを行う
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

- カレンダーバッチ更新
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- 各処理は冪等（date 単位の削除→挿入等）を意識して設計されています。
- research モジュールは prices_daily/raw_financials のみを参照し、本番発注 API へはアクセスしません（安全性）。

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                             — 環境変数・設定管理（.env 自動ロード）
- data/
  - __init__.py
  - jquants_client.py                   — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py                   — RSS 取得・前処理・DB保存
  - schema.py                           — DuckDB スキーマ定義・初期化
  - stats.py                            — 統計ユーティリティ（zscore_normalize）
  - pipeline.py                         — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py              — カレンダー管理・ジョブ
  - audit.py                            — 監査ログスキーマ（signal/order/execution トレース）
- research/
  - __init__.py
  - factor_research.py                   — Momentum / Volatility / Value 計算
  - feature_exploration.py               — forward returns / IC / summary
- strategy/
  - __init__.py
  - feature_engineering.py               — features の構築（正規化・ユニバースフィルタ）
  - signal_generator.py                  — final_score 計算と BUY/SELL 判定
- execution/                              — 発注・執行層（エントリ・骨組み）
- monitoring/                             — 監視用モジュール（監視DB等）※未詳細化

ドキュメント参照:
- ソース内の docstring とコメントに設計方針・仕様（例: StrategyModel.md, DataPlatform.md 等）が参照されています。実運用や拡張時はそれらの設計文書に従ってください。

---

## 運用上の注意

- J-Quants のレートリミット（120 req/min）や retry / refresh ロジックは jquants_client に実装されています。複数並列ジョブで API を叩く場合は全体のスロットリングに注意してください。
- DuckDB のファイルパスはデフォルトで data/kabusys.duckdb。バックアップ・永続化ポリシーを運用側で決めてください。
- .env の自動読み込みは config.py によりプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると安全です。
- ニュース収集では外部 URL を扱うため、SSRF 対策や response サイズ制限等の保護が実装されていますが、追加の監査や制限が必要な場合は設定してください。

---

ご希望があれば以下の追記を作成します:
- 開発環境向けの Makefile / tox / GitHub Actions のサンプル
- CI 用の DB 初期化スクリプト例
- デバッグ時のログ設定・例外ハンドリングポリシー

必要な場合は用途（ローカル実行 / CI / 本番）を教えてください。