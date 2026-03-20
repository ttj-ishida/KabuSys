# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）。  
データ収集（J-Quants）、ETL、マーケットカレンダー管理、ニュース収集、ファクター計算、特徴量エンジニアリング、シグナル生成、発注／監査スキーマを含む一連の機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の戦略開発〜実運用を想定したモジュール群を持つライブラリです。主な役割は次の通りです。

- J-Quants API から株価・財務・カレンダー等を安全に取得（レートリミット・再試行・トークン自動更新対応）
- DuckDB を用いたデータベーススキーマ定義と冪等な保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース（RSS）収集と銘柄紐付け（SSRF対策・サイズ制限）
- 研究用ファクター計算・特徴量正規化・特徴量保存
- シグナル生成（ファクタースコア＋AIスコア統合、BUY/SELL の生成）
- 発注・約定・ポジション・監査（スキーマ設計。実際のブローカー連携は execution 層で実装）
- 環境変数管理（.env 自動読み込み機能）

設計上の方針として、ルックアヘッドバイアスの排除、冪等性、シンプルでテストしやすいインターフェースを重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（ページネーション、レート制御、指数バックオフ、トークンリフレッシュ）
  - 生データを DuckDB に冪等保存する save_* 関数
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema() による初期化
- data/pipeline.py
  - run_daily_etl(): 市場カレンダー・株価・財務の差分ETL＋品質チェック
  - 個別 ETL ジョブ（prices/financials/calendar）
- data/news_collector.py
  - RSS フェッチ、安全対策、記事正規化、raw_news 保存、銘柄抽出・紐付け
- data/calendar_management.py
  - market_calendar の管理、営業日判定・前後営業日の取得、夜間カレンダー更新ジョブ
- research/*
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Spearman rank）やファクター統計サマリー
- strategy/feature_engineering.py
  - 研究で生成された生ファクターを正規化・合成して features テーブルへ保存
- strategy/signal_generator.py
  - features と ai_scores を合成して final_score を計算、BUY/SELL シグナル生成・signals テーブルへ保存
- data/news_collector と data/jquants_client は外部ネットワークアクセスに関する堅牢な実装（SSRF、gzip、Content-Length制限等）
- config.py
  - .env / .env.local 自動読み込み（プロジェクトルート検出）と必須環境変数チェック

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に | 演算子・標準ライブラリの仕様を使用）
- DuckDB（Python パッケージ）および必要なライブラリ

推奨インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要依存をインストール
   - pip install duckdb defusedxml

   （パッケージが配布されているなら `pip install -e .` を想定）

3. 環境変数の設定
   - プロジェクトルートに `.env`（および開発環境で `.env.local`）を配置できます。
   - 自動ロードはデフォルトで有効。無効化するには環境変数を設定:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（config.Settings 参照）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）

その他（任意・デフォルトあり）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG/INFO/・・・)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — .env 自動ロードを無効化（値が存在すれば無効）
- KABUSYS で使用する DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）

例 `.env`（簡易）
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

## 使い方（基本的な例）

下記は Python から直接呼ぶ例です。スクリプトや CI/CD ジョブとして組み込んでください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（市場カレンダー・株価・財務＋品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日が対象
print(result.to_dict())
```

3) 特徴量構築（strategy.feature_engineering）
```python
from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, date(2025, 1, 15))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
count = generate_signals(conn, date(2025, 1, 15))
print(f"signals written: {count}")
```

5) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes はテキストから抽出する有効銘柄コードの集合（例: {'7203', '6758', ...}）
r = run_news_collection(conn, known_codes={'7203', '6758'})
print(r)  # 各ソースごとの新規保存件数
```

6) JPX カレンダー更新（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

注意点
- 各関数は DuckDB 接続（kabusys.data.schema.init_schema が返す接続）を受け取ります。
- ETL やデータ取得はネットワークアクセスを行うため、環境変数（JQUANTS_REFRESH_TOKEN 等）を正しく設定してください。
- .env の自動読み込みはパッケージ読み込み時に行われます（プロジェクトルートの .git または pyproject.toml を検出）。テスト時などに無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - アプリケーション設定へのアクセス（例: settings.jquants_refresh_token）
- kabusys.data.schema.init_schema(db_path)
  - DuckDB スキーマを初期化して接続を返す
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
  - 日次 ETL の実行
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - J-Quants からのデータフェッチ（ページネーション対応）
- kabusys.data.jquants_client.save_*（conn, records）
  - DuckDB への冪等保存
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
  - RSS 収集ジョブ
- kabusys.strategy.build_features(conn, target_date)
  - features テーブルの構築
- kabusys.strategy.generate_signals(conn, target_date, threshold=..., weights=None)
  - signals テーブルの生成（BUY/SELL）

---

## ディレクトリ構成

（ルートはパッケージ配下の `src/kabusys/` を想定）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント + 保存関数
    - news_collector.py         — RSS/news 収集・処理
    - pipeline.py               — ETL パイプライン (run_daily_etl 等)
    - schema.py                 — DuckDB スキーマ定義・init_schema
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - features.py               — data.stats の再エクスポート
    - calendar_management.py    — market_calendar 管理（営業日判定、更新ジョブ）
    - audit.py                  — 監査ログスキーマ（signal_events, order_requests, executions）
    - audit / その他 components...
  - research/
    - __init__.py
    - factor_research.py        — momentum/volatility/value の計算
    - feature_exploration.py    — 将来リターン / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py    — features を構築
    - signal_generator.py       — final_score と signals 生成
  - execution/                  — 発注ロジック（プレースホルダ）
  - monitoring/                 — 監視・メトリクス（プレースホルダ）
  - ...（その他ユーティリティ）

---

## 動作モード

settings.env で指定する運用モード:
- development
- paper_trading
- live

settings.is_dev / is_paper / is_live プロパティで判定できます。モードに応じて発注層や通知の挙動を切り替えてください。

---

## 注意・運用上のポイント

- 機密情報（トークン・パスワード）は .env.local 等で管理し、リポジトリに含めないでください。
- DB 初期化（init_schema）はスキーマ定義を作成しますが、運用時のバックアップ・VACUUM 等の運用設計は別途行ってください。
- 実運用でのブローカー接続（kabu API 等）や Slack 通知はそれぞれの execution / monitoring 層で実装してください。
- API レートやネットワーク障害に対するリトライ・ログは実装済みですが、運用監視とアラートの仕組みを整備してください。

---

もし README に追加したい内容（例: CI の流れ、デプロイ手順、デモスクリプト、詳しい環境変数のサンプルなど）があれば教えてください。必要に応じてサンプルスクリプトや .env.example を追記します。