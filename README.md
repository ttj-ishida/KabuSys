# KabuSys

日本株向け自動売買基盤（研究 / データプラットフォーム / 戦略 / 発注監査）の共通ライブラリ群です。DuckDB をデータレイヤに用い、J-Quants API や RSS からデータを収集・整備し、特徴量計算 → シグナル生成 → 発注（監査ログ）へつなぐためのユーティリティ群を提供します。

主な設計方針:
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性重視（DB への保存は ON CONFLICT / トランザクションで安全に）
- 外部依存を最小化（標準ライブラリ + 必要最小限のパッケージ）
- テストしやすさ（id_token 注入や自動 .env ロード無効化等）

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動ロード（必要に応じて無効化可能）
  - 必須設定のラップ（Settings オブジェクト）

- Data（データプラットフォーム）
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新）
  - RSS ニュース収集器（SSRF / XML bomb 対策、トラッキング削除、記事ID生成）
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分取得・保存・品質チェック）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 統計ユーティリティ（Zスコア正規化等）
  - 監査ログ用テーブル定義（signal_events / order_requests / executions）

- Research（研究用ユーティリティ）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ

- Strategy（戦略）
  - 特徴量エンジニアリング（features テーブル作成・Zスコア正規化・ユニバースフィルタ）
  - シグナル生成（features + ai_scores を統合して final_score を算出、BUY/SELL 判定、signals テーブルへ書き込み）

- News（ニュース）
  - RSS 取得・正規化・raw_news 保存、news_symbols による銘柄紐付け

- その他
  - 各種ユーティリティ（URL 正規化、ファイル/DB 初期化、ETL 結果構造）

---

## セットアップ手順

前提:
- Python 3.9+（ソースは型注釈で | 型を使用しているため対応バージョンを確認してください）
- DuckDB が利用可能（Python パッケージを使用）

基本インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
# 必要パッケージ (最低限)
pip install duckdb defusedxml
# （プロジェクトとしてインストール可能なら）pip install -e .
```

重要な環境変数（README に記載している名前を .env に設定してください）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 送信先チャンネルID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

自動 .env ロードを無効にする（テスト等で利用）:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします。

例: .env.example（プロジェクトルートに配置）

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_refresh_token_here

# kabuステーション
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX

# DB paths
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境・ログ
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要なワークフロー例）

以下は最小限の利用例です。DuckDB の初期化、ETL 実行、特徴量作成、シグナル生成の流れを示します。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

# ファイルに保存する DB を初期化（親ディレクトリは自動作成）
conn = init_schema("data/kabusys.duckdb")
# またはメモリ DB
# conn = init_schema(":memory:")
```

2) 日次 ETL の実行（J-Quants トークンは settings から参照されます）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（features テーブルの作成）

```python
from kabusys.strategy import build_features
from datetime import date

n_features = build_features(conn, target_date=date.today())
print("features 作成数:", n_features)
```

4) シグナル生成（signals テーブルへの書き込み）

```python
from kabusys.strategy import generate_signals
from datetime import date

n_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals 書き込み数:", n_signals)
```

5) ニュース収集と銘柄紐付け

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 抽出に使う有効銘柄コードの集合（例: prices_daily から集める）
known_codes = {row[0] for row in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

注意点:
- J-Quants API 呼び出しはレート制限（120 req/min）および再試行ロジックを備えています。大量取得時は待ち時間が入ります。
- ETL は部分的な失敗を許容し、処理結果（ETLResult）に品質問題やエラーを返します。運用側でアラートや再試行を制御してください。

---

## 設定（Settings / 環境変数）

Settings オブジェクト（kabusys.config.settings）からアクセスできます。必須項目は取得時に ValueError が発生します。

例:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # JQUANTS_REFRESH_TOKEN が未設定なら例外
print(settings.duckdb_path)            # Path オブジェクト
print(settings.env)                    # development|paper_trading|live
```

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）を探し `.env` と `.env.local` を読み込みます。
- 優先順位: OS 環境 > .env.local > .env
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（主要ファイル）

以下はソースの主要ファイルと簡単な説明です（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、Settings オブジェクト、自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制限、トークン刷新、保存ユーティリティ）
    - news_collector.py
      - RSS 収集・前処理・DB 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義 & init_schema / get_connection
    - pipeline.py
      - 日次 ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
    - calendar_management.py
      - 営業日判定、next/prev_trading_day、calendar_update_job
    - features.py
      - zscore_normalize の再エクスポート
    - stats.py
      - zscore_normalize など統計ユーティリティ
    - audit.py
      - 監査ログ用テーブル DDL（signal_events / order_requests / executions 等）
  - research/
    - __init__.py
    - factor_research.py
      - mom/value/volatility/liquidity の計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ、rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブルの構築（ユニバースフィルタ・正規化・UPSERT）
    - signal_generator.py
      - final_score 計算・BUY/SELL 判定・signals 保存
  - execution/
    - __init__.py
    - （発注処理や証券会社接続はここに追加）
  - monitoring/
    - （監視 / メトリクス系のユーティリティを配置）

---

## 運用上の注意とセキュリティ

- J-Quants リフレッシュトークンや kabu API パスワード等は秘匿情報です。`.env` をバージョン管理に含めないでください。
- news_collector は外部 URL を読み込みます。SSRF/プライベートアドレス回避や XML パース安全化（defusedxml）を組み込んでいますが、運用ネットワーク構成に応じた制約を推奨します。
- DuckDB ファイルへのアクセス権・バックアップ戦略を考慮してください（監査ログや約定情報が含まれます）。
- production(live) 環境での実行前に KABUSYS_ENV を適切に設定し、paper_trading モードで検証してください。

---

もし README に追加したい使用例（cron / Airflow / systemd ジョブの書き方）、CI テストやロギング設定のテンプレート、あるいは外部システムとのインテグレーション（Slack 通知や kabuステーション発注フロー）のサンプルが必要であれば教えてください。