# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J‑Quants API や RSS を用いたデータ収集、DuckDB ベースのスキーマ管理、ファクター計算・特徴量生成、シグナル生成、監査ログなど、研究〜本番運用を想定した一連の機能を提供します。

---

## 主な特徴（機能一覧）

- データ収集
  - J‑Quants API から株価（日足）、財務データ、マーケットカレンダーをページネーション対応で取得
  - RSS フィードからニュース記事を収集し、記事と銘柄の紐付けを行う
  - レート制限・リトライ・トークン自動リフレッシュ等の堅牢な HTTP 処理

- データ管理
  - DuckDB による 3 層（Raw / Processed / Feature）＋ Execution 層のスキーマ定義と初期化
  - 生データ保存用の冪等性（ON CONFLICT）対応

- ETL / パイプライン
  - 差分取得（最終取得日からの差分）を自動で計算する日次 ETL（run_daily_etl）
  - 品質チェックフレームワーク（欠損・スパイク等の検出を想定）

- 研究・特徴量計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - クロスセクションの Z スコア正規化ユーティリティ

- 戦略
  - 特徴量統合（build_features）：研究で得られた生ファクターを正規化・合成して features テーブルへ保存
  - シグナル生成（generate_signals）：features ＋ ai_scores を統合し BUY / SELL シグナルを生成して signals テーブルへ保存
  - Bear レジーム判定やエグジット（ストップロス等）ロジックを実装

- その他
  - マーケットカレンダー管理・営業日ユーティリティ（next_trading_day 等）
  - 監査ログ（signal_events / order_requests / executions）によるトレーサビリティ設計

---

## 要件（主要依存）

- Python 3.9+
- duckdb
- defusedxml

必要に応じて urllib/標準ライブラリのみで動作する部分もありますが、上記は最低限必要な外部パッケージです。

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 任意: プロジェクトを開発インストールできる場合
pip install -e .
```

（プロジェクトのパッケージ管理ファイルがある場合はそちらを参照してください。）

---

## 環境変数 / 設定

kabusys は環境変数または `.env` / `.env.local` から設定を読み込みます（自動ロード、ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

必須（Settings._require によるチェック）:
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注層で使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — 環境 (development, paper_trading, live)。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite パス。デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するフラグ（1 を設定）

例: `.env`（簡易）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン／取得
2. 仮想環境を作成して依存をインストール
   - pip install duckdb defusedxml
   - 他に必要なパッケージがあれば適宜インストール
3. 環境変数を設定（`.env` をプロジェクトルートに作成）
4. DuckDB スキーマを初期化

DuckDB スキーマ初期化例（Python）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

これでテーブル定義がすべて作成されます（冪等）。

---

## 使い方（主要な操作例）

ここでは代表的な操作の Python スニペットを示します。date は datetime.date を利用します。

- DuckDB 接続／スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")
# 既に初期化済みで接続のみ欲しい場合:
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー・株価・財務を差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しないと today が使われる
print(result.to_dict())
```

- 特徴量の構築（features テーブルへ保存）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2024, 1, 1))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへ保存）
```python
from kabusys.strategy import generate_signals
from datetime import date
n_signals = generate_signals(conn, date(2024, 1, 1))
print(f"signals written: {n_signals}")
```

- ニュース収集ジョブ（RSS の収集と保存）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄コード集合（extract_stock_codes に使用）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

- マーケットカレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 研究用ユーティリティ例（forward returns / IC）
```python
from kabusys.research import calc_forward_returns, calc_ic, rank
# calc_forward_returns(conn, target_date, horizons=[1,5,21]) ...
```

- 設定取得（環境変数をラップ）
```python
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.is_live)
```

注意: これらの関数は DuckDB 上のテーブル（prices_daily, raw_financials, features, ai_scores, positions 等）を参照します。ETL を実行・データを投入した後に戦略処理を行ってください。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要なモジュールと用途の一覧です（path は src/kabusys 以下）:

- __init__.py
- config.py
  - 環境変数と .env の自動読み込み、Settings クラス
- data/
  - jquants_client.py — J‑Quants API クライアント（取得 & DuckDB 保存ユーティリティ）
  - news_collector.py — RSS 取得・記事正規化・DB 保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema()
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - pipeline.py — 日次 ETL（run_daily_etl）、個別 ETL ジョブ
  - features.py — data.stats の再エクスポート
  - calendar_management.py — カレンダー更新と営業日ユーティリティ
  - audit.py — 監査ログ（信頼性・トレーサビリティ用 DDL）
  - (その他 execution 層関連のモジュール)
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算
  - feature_exploration.py — 将来リターン、IC、統計サマリーなど
- strategy/
  - feature_engineering.py — 生ファクターから features を構築（正規化・フィルタ）
  - signal_generator.py — features + ai_scores → final_score → signals 生成
- execution/ — 発注・約定・ポジション管理（空の __init__ や関連実装ファイル）
- monitoring/ — 監視・メトリクス関連（該当モジュールがあればここに配置）

（実際のリポジトリでは上記以外の補助モジュールや設定ファイルが存在する場合があります。）

---

## 運用上の注意 / 設計上のポイント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- J‑Quants API はレート制限（120 req/min）を想定しており、内部で固定間隔の RateLimiter を使用しています。大量データ取得時はスループットに注意してください。
- DuckDB のスキーマは冪等（CREATE TABLE IF NOT EXISTS / ON CONFLICT）で定義されています。初回は init_schema() を使ってください。
- ルックアヘッドバイアス回避の方針が設計に組み込まれています：各計算は target_date 時点で利用可能なデータのみを用いるよう設計されています。
- 本パッケージは発注レイヤ（実際に証券会社へ発注）と完全に統合できるように設計されていますが、本番運用時は必ずサンドボックス・ペーパートレード環境で十分に検証してください（KABUSYS_ENV を適切に設定）。

---

## さらなる参照

- 各モジュールの docstring に設計意図や参照すべきドキュメント（例: StrategyModel.md, DataPlatform.md 等）が記載されています。実装やチューニング時は該当ファイルやドキュメントを確認してください。
- tests や CI、依存管理のファイル（requirements.txt / pyproject.toml）が存在する場合はそちらに従ってください。

---

README はプロジェクトのトップレベル README.md に相当する要約です。追加で API リファレンスや開発フロー（テスト・リリース手順）を望まれる場合は、その内容に合わせて追記できます。必要であればサンプルの .env.example やユースケース別のハンズオン（ETL→feature→signal→発注）を別ファイルで作成します。