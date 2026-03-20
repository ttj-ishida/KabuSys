# KabuSys

KabuSys は日本株の自動売買プラットフォームを想定したコードベースです。J-Quants などの外部データソースからデータを取得・保存し、研究用ファクター計算、特徴量生成、シグナル生成、ETL、ニュース収集、マーケットカレンダー管理、監査ログなどを一貫して提供します。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株向けにデータ収集 → 特徴量生成 → シグナル作成 → 発注・監視までのワークフローを支援するライブラリ群
- 設計方針:
  - DuckDB をローカル DB に用いてデータ層を構築（冪等保存、トランザクション制御）
  - ルックアヘッドバイアス回避のため、常に target_date 時点のデータのみで計算
  - 外部 API 呼び出しはレート制御・リトライ・トークン自動更新を備えたクライアント経由
  - 研究コード（research）と本番処理（data / strategy / execution）を明確に分離

---

## 主な機能一覧

- 環境設定管理
  - .env ファイルの自動読み込み（プロジェクトルートの検出）と必須環境変数チェック
- データ層（data）
  - J-Quants クライアント（株価・財務・カレンダー取得、トークン自動リフレッシュ、レート制御、リトライ）
  - RSS ベースのニュース収集（SSRF 対策、URL 正規化、記事ID生成、銘柄抽出）
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - ETL パイプライン（差分取得、バックフィル、品質チェック呼び出し）
  - マーケットカレンダー管理（営業日判定、前後営業日取得）
  - 統計ユーティリティ（Z スコア正規化等）
  - 監査ログ / 発注トレーサビリティ用テーブル
- 研究（research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 特徴量探索・IC（Information Coefficient）計算・将来リターン算出
- 戦略（strategy）
  - 特徴量構築（research の生ファクターを統合・正規化して features テーブルへ保存）
  - シグナル生成（features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを作成）
- ニュース → 銘柄紐付け（news_symbols）や raw_news の保存
- 実行（execution）層：発注・約定・ポジション管理のテーブル定義（実装は拡張を想定）

---

## 前提条件

- Python 3.10 以上（型注釈に `X | None` 形式を使用）
- 必要な Python パッケージ（主に例示）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API を使う場合）
- J-Quants のリフレッシュトークン等外部サービス用の資格情報

※実際の requirements.txt はこのリポジトリに含まれていないため、上記パッケージを個別にインストールしてください。

---

## インストール（開発環境向け）

例: 仮想環境を使うことを推奨します。

1. 仮想環境作成・アクティベート（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml

3. パッケージを編集可能モードでインストール（リポジトリルートで）
   - pip install -e .

---

## 環境変数（主なもの）

このプロジェクトでは環境変数または .env ファイルで設定を与えます。主要なキー:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

自動で .env を読み込む仕組みが有効になっています（プロジェクトルートに .env/.env.local）。
自動読み込みを無効化するには:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定が不足していると Settings が ValueError を投げます。README にある .env.example を参考に作成してください。

---

## セットアップ手順（DB 初期化など）

1. DuckDB スキーマを初期化する
```py
from kabusys.data import schema

# ファイルで永続化する場合:
conn = schema.init_schema("data/kabusys.duckdb")

# テスト等インメモリ:
# conn = schema.init_schema(":memory:")
```

init_schema() は必要なテーブルを全て作成し、DuckDB 接続オブジェクトを返します。

2. （任意）ロギング設定
```py
import logging
logging.basicConfig(level=logging.INFO)
```

3. 必要な環境変数を .env に設定（J-Quants トークン等）

---

## 使い方（代表的なワークフロー）

以下は典型的な日次処理の流れ（ETL → 特徴量 → シグナル生成）です。

1. 日次 ETL を実行してデータを取得・保存する
```py
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())

# ETLResult に処理結果・品質問題・エラー情報が入る
print(result.to_dict())
```

2. 特徴量（features）を構築する
```py
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

3. シグナルを生成する
```py
from kabusys.strategy import generate_signals

signals_count = generate_signals(conn, target_date=date.today())
print("signals generated:", signals_count)
```

4. ニュース収集（RSS）を実行する
```py
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に用いる有効な銘柄コード集合（例: set(["7203","6758",...])）
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)
```

5. カレンダー更新ジョブ
```py
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar entries saved:", saved)
```

注意:
- jquants_client の fetch 系関数はネットワークを使います。テスト時は id_token を注入したりモックしてください。
- run_daily_etl は複数ステップを独立に実行し、失敗したステップはログを残して継続します。戻り値の ETLResult で総括できます。

---

## ディレクトリ構成（src/kabusys の主要ファイル）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings クラス（必須設定チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御・自動トークン更新・リトライ・save_* 関数）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存・銘柄抽出・run_news_collection
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - features.py
      - zscore_normalize の公開再エクスポート
    - calendar_management.py
      - market_calendar の更新・営業日判定ヘルパー（is_trading_day 等）
    - audit.py
      - 監査ログ用テーブル定義（signal_events / order_requests / executions 等）
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算・IC 計算・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - research の生ファクターを統合・正規化して features テーブルへ保存
    - signal_generator.py
      - features と ai_scores を統合して final_score を計算し BUY/SELL を生成
  - execution/
    - __init__.py（発注層は拡張ポイント）
  - monitoring/
    - （モニタリング機能を想定したパッケージエクスポート）

---

## 開発・テストのヒント

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時に自動読み込みを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ネットワーク呼び出し（jquants_client.fetch_* や news_collector.fetch_rss）はユニットテストでモックしやすいように id_token 注入や内部 helper の差し替えが可能です（news_collector._urlopen 等）。
- DuckDB はインメモリ（":memory:"）で動作するため、単体テストの DB 初期化に便利です。
- ロギングを有効にしておくと ETLResult や処理の詳細が把握しやすくなります。

---

必要であれば README をプロジェクトの実際の依存関係や運用手順に合わせて調整します。追加で「デプロイ手順」「cron 設定例」「監視・アラート設定」などを含めることも可能です。どの情報を優先して補足しますか？