# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants や RSS 等からデータを収集して DuckDB に格納し、研究用ファクター計算、特徴量生成、シグナル作成、発注監査などのワークフローを提供します。

主な設計方針
- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみを利用）
- DuckDB を中心としたローカルデータプラットフォーム（冪等保存）
- 外部 API 呼び出しにはレート制御・リトライ・トークン自動リフレッシュを導入
- DB 操作はトランザクションで原子性を確保

---

## 機能一覧

- データ取得 / 保存
  - J-Quants からの株価（日足）・財務データ・マーケットカレンダー取得（jquants_client）
  - RSS からのニュース収集（news_collector）
  - DuckDB への冪等保存（ON CONFLICT / RETURNING を利用）
- スキーマ管理
  - DuckDB スキーマ初期化と接続（data.schema.init_schema / get_connection）
- ETL パイプライン
  - 日次差分 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）（data.pipeline.run_daily_etl）
- 研究 / ファクター
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算・IC 計算・統計サマリー（research.feature_exploration）
- 特徴量生成 / シグナル
  - ファクターの正規化・合成して features テーブルへ保存（strategy.feature_engineering.build_features）
  - features と ai_scores を統合して BUY/SELL シグナルを生成（strategy.signal_generator.generate_signals）
- マーケットカレンダー管理（data.calendar_management）
- 発注・監査用スキーマ（data.audit, execution 層用テーブル定義）
- 共通ユーティリティ
  - Z スコア正規化などの統計ユーティリティ（data.stats）

---

## 前提条件

- Python 3.10 以上（PEP 604 の `X | Y` 型注釈を使用しているため）
- 推奨ライブラリ（プロジェクトで利用される主要依存）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード等にアクセスする場合）

例（pip）:
```
pip install duckdb defusedxml
```

（プロジェクトに pyproject.toml / requirements があればそちらを使用してください。）

---

## 環境変数（主な必須設定）

設定は環境変数、またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（デフォルト）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注連携時）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG/INFO/...)
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.env 例はプロジェクトの `.env.example` を参照してください。

---

## セットアップ手順

1. リポジトリをクローン / 取り込み
2. Python 仮想環境を作成し有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt   # ある場合
   pip install duckdb defusedxml
   ```
4. `.env` を作成して環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を置く
   - 必須のトークン / パスワード等を設定する
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化します（下記「使い方」を参照）

---

## 使い方（例）

以下は主要な処理の簡単な利用例です。実運用ではエラーハンドリングやログ設定を適切に行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH に基づく
conn = init_schema(settings.duckdb_path)  # ファイルを作成しテーブルを作る
```

2) 日次 ETL を実行（市場カレンダー / 株価 / 財務 を差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量を構築（strategy 層）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date(2025, 1, 14))
print(f"built features for {n} codes")
```

4) シグナルを生成
```python
from kabusys.strategy import generate_signals
from datetime import date

num_signals = generate_signals(conn, target_date=date(2025, 1, 14))
print(f"generated {num_signals} signals")
```

5) RSS ニュース収集（news -> raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効なコード集合（省略可）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(res)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

7) J-Quants の生データ取得と保存（低レベル）
```python
from kabusys.data import jquants_client as jq
from datetime import date

records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
saved = jq.save_daily_quotes(conn, records)
```

---

## 注意事項 / 運用のヒント

- 自動環境変数読み込み:
  - モジュール起動時にプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し `.env` / `.env.local` を読み込みます。
  - テストなどで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- リトライ・レート制御:
  - J-Quants クライアントは 120 req/min のレート制御、指数バックオフ、401 のトークン自動リフレッシュを実装しています。
- 冪等性:
  - 原則として API からのデータ保存は ON CONFLICT により冪等に実行されます（再実行しても重複登録されない）。
- ローカル DB の管理:
  - DUCKDB_PATH に指定したファイルをバックアップまたは外部ストレージに適宜保存してください。
- テスト / デバッグ:
  - duckdb のインメモリ接続（":memory:"）を使ってユニットテストを行えます（schema.init_schema(":memory:")）。

---

## ディレクトリ構成（主要部）

この README は与えられたコードベースに基づきます。主要なファイル／パッケージは以下の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント
      - news_collector.py            — RSS ニュース収集
      - schema.py                    — DuckDB スキーマ定義・初期化
      - stats.py                     — 統計ユーティリティ（zscore_normalize）
      - pipeline.py                  — ETL パイプライン（差分更新等）
      - calendar_management.py       — マーケットカレンダー管理
      - audit.py                     — 発注監査ログスキーマ
      - features.py                  — data 層の feature ユーティリティ公開
    - research/
      - __init__.py
      - factor_research.py           — Momentum / Volatility / Value 等
      - feature_exploration.py       — 将来リターン / IC / サマリー等
    - strategy/
      - __init__.py
      - feature_engineering.py       — features テーブル作成
      - signal_generator.py          — BUY/SELL シグナル生成
    - execution/                      — 発注・実行関連（パッケージ置き場）
    - monitoring/                     — 監視・メトリクス（パッケージ置き場）
- pyproject.toml / setup.cfg 等（パッケージング / 依存管理があれば）

---

## 貢献 / 拡張案

- AI スコア生成パイプライン（ai_scores 生成ロジックの追加）
- 発注エンジン（kabuステーション連携実装：execution 層の実装）
- 品質チェック（data.quality モジュールの拡張）
- テストカバレッジ強化（unit/integration tests）

---

以上です。README の補足・改善点（例: 実行スクリプト、CI 設定、.env.example の内容）を追加したい場合は、どの内容を入れたいか教えてください。