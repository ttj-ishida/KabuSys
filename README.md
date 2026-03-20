# KabuSys — 日本株自動売買システム (README)

KabuSys は日本株向けのデータ収集・特徴量生成・シグナル生成・監査までを含む自動売買プラットフォームのコアライブラリです。DuckDB をデータストアに採用し、J-Quants API や RSS ニュースからのデータ取得、研究用ファクター計算および戦略シグナル生成をモジュール化して提供します。

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 環境変数 (.env) と設定
- 基本的な使い方（コード例）
  - DB 初期化
  - 日次 ETL 実行
  - 特徴量の構築
  - シグナル生成
  - ニュース収集ジョブ
  - カレンダー更新ジョブ
- ディレクトリ構成
- 開発メモ / 注意点

---

## プロジェクト概要

このライブラリは以下のレイヤーを提供します。

- Data layer（DuckDB）
  - 生データ（raw_prices, raw_financials, raw_news など）
  - 整形データ（prices_daily, fundamentals, market_calendar など）
  - 特徴量・AI スコア（features, ai_scores）
  - 発注・監査（signals, signal_queue, orders, executions, audit テーブル群）
- Data ingest
  - J-Quants API クライアント（rate limit / token 自動リフレッシュ / リトライ対応）
  - RSS ベースのニュース収集（SSRF 対策 / トラッキングパラメータ除去 / 記事 ID の冪等化）
- ETL パイプライン（差分取得・保存・品質チェック）
- Research モジュール（ファクター計算・特徴量解析・IC 計算）
- Strategy 層（特徴量正規化 → final_score 計算 → BUY/SELL シグナル生成）
- Audit / トレーサビリティ（シグナル→発注→約定の完全トレース）

設計上の要点：
- ルックアヘッド（未来情報）を避けるため、target_date 時点のデータのみを参照する実装
- DuckDB へは冪等な保存（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）
- ネットワーク処理に対する堅牢なエラーハンドリング（再試行・バックオフ等）

---

## 主な機能一覧

- DuckDB スキーマ定義と初期化（kabusys.data.schema.init_schema）
- J-Quants API クライアント（株価・財務・カレンダー取得、トークン管理、レート制御）
- ETL パイプライン（run_daily_etl：カレンダー・株価・財務の差分取得、品質チェック）
- ニュース収集（RSS 取得・前処理・記事保存・銘柄抽出）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量構築（Zスコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
- シグナル生成（final_score の重み合成、Bear レジーム抑制、BUY/SELL 判定、signals テーブル更新）
- マーケットカレンダー管理（営業日判定・前後営業日検索・夜間更新ジョブ）
- 監査ログ（signal_events / order_requests / executions など）

---

## 前提・依存関係

- Python 3.10 以上（typing の | 演算子等を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- （オプション）J-Quants API 利用時にネットワークアクセス

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージをプロジェクトとしてインストールする場合
pip install -e .
```

※ プロジェクトは src/ 配下のパッケージレイアウトを想定しています（pip install -e . が使えます）。

---

## セットアップ手順

1. リポジトリをクローンしてワーク環境を作成
2. Python 仮想環境を作る（推奨）
3. 依存パッケージをインストール（duckdb, defusedxml 等）
4. 環境変数（.env）を用意する（下記参照）
5. DuckDB スキーマを初期化する

DB 初期化（例）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH を参照（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

init_schema(":memory:") を指定すればインメモリ DB での利用も可能です。

---

## 環境変数 (.env) と設定

パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（主な）環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション用パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必要に応じて）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

設定はライブラリ内で `from kabusys.config import settings` によりアクセスできます（settings.jquants_refresh_token 等）。

---

## 基本的な使い方（コード例）

以下は代表的なワークフローの例です。すべて DuckDB 接続（kabusys.data.schema.init_schema が返す conn）を受け取る形で動作します。

1) DB 初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL（J-Quants からデータを差分取得し保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しないと今日の日付で実行
print(result.to_dict())
```

3) 特徴量の構築（features テーブルを target_date 分更新）
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, date(2026, 3, 1))
print(f"features upserted: {count}")
```

4) シグナル生成（features + ai_scores を用いて signals を作成）
```python
from kabusys.strategy import generate_signals

n = generate_signals(conn, date(2026, 3, 1), threshold=0.60)
print(f"signals written: {n}")
```

5) ニュース収集ジョブ（複数ソース、銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コードの集合（例: {"7203", "6758", ...}）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes_set)
print(results)  # {source_name: 新規保存件数, ...}
```

6) カレンダー更新ジョブ（夜間バッチで実行する想定）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点：
- run_daily_etl() は内部で calendar ETL → prices ETL → financials ETL → 品質チェック の順に実行します。各ステップは独立して例外処理され、失敗しても可能な限り処理を継続します。
- J-Quants API 呼び出しはレート制限（120 req/min）に従いスロットリングされます。

---

## ディレクトリ構成

リポジトリ（src/kabusys）内の主要ファイル / モジュール：

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント（取得 / 保存関数含む）
      - news_collector.py          — RSS ニュース収集・保存・銘柄抽出
      - schema.py                  — DuckDB スキーマ定義・初期化
      - stats.py                   — 汎用統計ユーティリティ（zscore_normalize 等）
      - pipeline.py                — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py     — カレンダー管理・更新ジョブ
      - features.py                — data 層の特徴量ユーティリティ再エクスポート
      - audit.py                   — 監査ログ（order_requests / executions 等）
    - research/
      - __init__.py
      - factor_research.py         — ファクター計算（momentum/volatility/value）
      - feature_exploration.py     — IC / forward returns / summary 等
    - strategy/
      - __init__.py
      - feature_engineering.py     — 特徴量の正規化・ユニバースフィルタ・features 保存
      - signal_generator.py        — final_score 計算、BUY/SELL 判定、signals テーブル保存
    - execution/                    — 発注/ブローカー連携用プレースホルダ（空の __init__.py）
    - monitoring/                   — 監視・メトリクス用（将来的拡張）
    - その他：README やドキュメント（別途）

---

## 開発メモ / 注意点

- 型安全性や数値検査（isfinite 等）に配慮した実装が多く含まれています。欠損や NaN/Inf に注意してデータ前処理を行ってください。
- DuckDB の SQL 実行では、プレースホルダを用いたパラメタライズドクエリを使用している箇所が多いです（SQL インジェクション対策）。
- news_collector は SSRF・XML Bomb 等を意識した堅牢な実装（リダイレクト検査、defusedxml、レスポンスサイズ上限）になっていますが、外部ソースの扱いには十分注意して運用してください。
- 環境は `KABUSYS_ENV` により development / paper_trading / live を切替可能です。live モードでは実際の発注や外部通知の取り扱いに注意してください。
- tests や CI の設定がある場合は、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って .env 自動読み込みを無効にすることでテストの信頼性を高められます。

---

この README はコードベースの主要機能をまとめた概要です。各モジュールには詳細なドキュメント文字列（docstring）が含まれているため、実装や API の詳細はソースコードの該当モジュールを参照してください。必要であれば、具体的な使用例や開発用スクリプト（CLI、ジョブ設定、Unit Test の例）を追加で作成できます。