# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
データ取得（J-Quants），ETL，特徴量生成，シグナル生成，ニュース収集，監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つコンポーネントを備えたパッケージです。

- J-Quants API 経由での市場データ・財務データ・カレンダー取得（rate-limit / retry / token refresh 対応）
- DuckDB を用いたスキーマ管理・永続化（Raw / Processed / Feature / Execution 層）
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- 研究（research）向けのファクター計算・探索ユーティリティ
- 戦略（strategy）向けの特徴量正規化・シグナル生成
- ニュース収集（RSS）と記事→銘柄紐付け
- 環境変数管理と設定アクセス（自動 .env ロード機能）

設計上のポイント:
- ルックアヘッドバイアスを回避するため、各処理は target_date 時点のデータのみを使用
- DuckDB への保存は冪等（ON CONFLICT / トランザクション）で実装
- 外部ライブラリへの過度な依存を避け、標準ライブラリ中心でユーティリティを実装

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API 呼び出し（ページネーション・リトライ・トークン更新）
  - schema: DuckDB スキーマ定義と初期化（init_schema）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL ジョブ（prices, financials, calendar）
  - news_collector: RSS 取得・正規化・raw_news 保存と銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: z-score 正規化ユーティリティ
- research/
  - factor_research: momentum / volatility / value のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）・統計サマリー等
- strategy/
  - feature_engineering.build_features: ファクターの統合・正規化・features テーブルへの UPSERT
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナルを生成
- config:
  - 環境変数読み込み（.env / .env.local 自動ロード）、Settings クラスで設定を参照可能
- audit / execution / monitoring:
  - 監査ログ・発注/約定管理・監視用テーブル等の DDL を含む（実装済みのスキーマ／ユーティリティ）

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（コードの型記法に依存）
- DuckDB を利用（Python パッケージ duckdb）
- ネットワークから RSS や J-Quants API にアクセス可能

1. リポジトリをクローン／ワークディレクトリへ移動
2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)
3. 必要パッケージをインストール（最低限）
   - pip install duckdb defusedxml
   - その他、プロジェクト配布用に setup.py / pyproject.toml を用意している場合は `pip install -e .` を推奨
4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルト値あり）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV: development / paper_trading / live（デフォルト：development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト：INFO）
5. DuckDB スキーマ初期化
   - Python から実行例:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

---

## 使い方（主要ワークフロー例）

以下は Python スクリプトや REPL から呼び出す想定です。

1) DB 初期化（1回）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（市場カレンダー・株価・財務の差分取得＋品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量作成（research の生ファクターを結合して features に保存）
```python
from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, date(2024, 1, 12))
print(f"upserted features: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
count = generate_signals(conn, date(2024, 1, 12))
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ（RSS 取得・raw_news 保存・銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードの集合（例：データベースから取得）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

--- 

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、自動で .env をロードしません（テスト用途）

自動ロード順序: OS 環境 > .env.local (override) > .env（ただし project root が .git または pyproject.toml を基準に探索されます）

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定 / .env ロード / Settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & 保存ユーティリティ
    - schema.py              — DuckDB スキーマ（DDL）と init_schema/get_connection
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - news_collector.py      — RSS 取得・前処理・保存・銘柄抽出
    - calendar_management.py — 営業日判定・更新ジョブ
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - features.py            — data.stats の公開インターフェース
    - audit.py               — 監査ログ（signal_events / order_requests / executions 等の DDL）
  - research/
    - __init__.py
    - factor_research.py     — momentum / volatility / value ファクター計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化・クリップ・UPSERT）
    - signal_generator.py    — generate_signals（final_score 計算・BUY/SELL 生成）
  - execution/               — 発注関連モジュール置き場（空パッケージ）
  - monitoring/              — 監視・アラート用モジュール（パッケージとして想定）

---

## 注意事項 / 運用上のヒント

- DuckDB のファイル保存先（DUCKDB_PATH）はバックアップや排他に注意してください（同時書き込み等）。
- J-Quants の API レート制限／認証トークン管理は jquants_client に実装されていますが、運用時はトークンの管理に留意してください。
- 本パッケージは戦略ロジックの核を提供しますが、実際の発注（ブローカー接続）やリスク管理ポリシーは運用側で適切に実装してください。
- テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使い .env 自動ロードを無効にすることで設定の注入を明示化できます。

---

必要であれば README に含める具体的なコード例、環境ファイルの雛形（.env.example）、あるいはデプロイ／CI 用の手順を追加できます。どの情報を優先して追加しますか？