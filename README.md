# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ群です。データ取得（J‑Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB ベースのスキーマ管理など、戦略研究から実運用（発注レイヤを除く）までの中核処理を提供します。

注: 本リポジトリは発注ブローカー接続や取引所への実注文送信部分を含まず、戦略・データ基盤・監査ロジックを中心に実装されています。

---

## 主要な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と必須変数取得ヘルパー
- J‑Quants API クライアント
  - ページネーション対応、レート制限（120 req/min）厳守、リトライ/トークン自動リフレッシュ
  - 株価（OHLCV）、財務データ、マーケットカレンダー取得
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義し初期化
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックと日次ETL の統合実行
- データ処理・統計ユーティリティ
  - クロスセクション Z スコア正規化等
- 研究用ファクター計算
  - Momentum / Volatility / Value などのファクターを prices_daily/raw_financials から計算
- 特徴量生成（feature engineering）
  - 生ファクターの結合、ユニバースフィルタ、Z スコア正規化、features テーブルへの冪等保存
- シグナル生成
  - features と AI スコアを統合して final_score を算出、BUY/SELL シグナルを signals テーブルに冪等保存
- ニュース収集
  - RSS フィード収集、URL 正規化（トラッキングパラメータ除去）、SSRF 対策、raw_news 保存、銘柄抽出・紐付け
- 監査ログ（audit）スキーマ
  - シグナル→発注→約定までのトレーサビリティ用テーブル群（監査設計）

---

## 前提（Prerequisites）

- Python 3.10 以上（PEP 604 の型記法（X | None）を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- ネットワークから外部 API（J‑Quants、RSS）へアクセス可能であること

実行環境に合わせて追加の依存関係が発生する可能性があります。requirements.txt がある場合はそちらを利用してください。

---

## セットアップ手順

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されていれば）pip install -e .

3. 環境変数の用意
   - プロジェクトルートに `.env`（および環境ごとに `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

オプション（既定値あり/説明）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト INFO）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（主要な API と簡単な例）

次に示すのはライブラリの代表的な使い方例です。実運用では各処理をジョブ（cron / Airflow / Prefect 等）で実行してください。

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ファイルに DB を作成
```

- 日次 ETL の実行（J‑Quants からデータ取得 → 保存 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日を基準に実行
print(result.to_dict())
```

- 特徴量（features）をビルド
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, date(2024, 1, 12))
print(f"{count} 銘柄の features を upsert")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn, date(2024, 1, 12))
print(f"{n} 件のシグナルを書き込みました")
```

- ニュース収集（RSS）と保存
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出に使う有効コード集合（省略すると紐付け処理をスキップ）
res = run_news_collection(conn, sources=None, known_codes={"6758", "7203"})
print(res)  # {source_name: saved_count}
```

- J‑Quants API から生データを直接取得（テスト用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes

quotes = fetch_daily_quotes(date_from=None, date_to=None)  # id_token はモジュールキャッシュを利用
```

- 環境設定の参照
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## 実装上の注意・設計方針（重要メモ）

- 冪等性
  - DB への保存は可能な限り ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING を用いて冪等に設計されています。
- ルックアヘッドバイアス対策
  - feature/signal 等の計算は target_date 時点まで入手可能なデータのみを参照することを意識して実装されています（future data を参照しない設計）。
- レート制限とリトライ
  - J‑Quants へのリクエストは RateLimiter による固定間隔スロットリングと、HTTP エラーに対する指数バックオフリトライを行います。401 はトークンを自動リフレッシュして一度だけ再試行します。
- RSS ニュース収集のセキュリティ
  - SSRF 対策、XML 攻撃防止、受信サイズ上限などを組み込んでいます。
- ローカル環境でのテスト
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効にできます（テスト時に便利）。

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリの概観（src/kabusys 配下）です。

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / 設定の読み込み
    - data/
      - __init__.py
      - jquants_client.py    — J‑Quants API クライアント
      - news_collector.py    — RSS ニュース収集 / 保存
      - schema.py            — DuckDB スキーマ定義と init_schema
      - stats.py             — 統計ユーティリティ（zscore_normalize）
      - pipeline.py          — ETL パイプライン（run_daily_etl 等）
      - features.py          — data.stats の公開ラッパ
      - calendar_management.py — マーケットカレンダー管理
      - audit.py             — 監査ログスキーマ
      - (その他 data モジュール)
    - research/
      - __init__.py
      - factor_research.py   — momentum/volatility/value 等のファクター計算
      - feature_exploration.py — IC, forward returns, 統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py — features 作成処理
      - signal_generator.py    — final_score 計算と signals 書き込み
    - execution/              — （発注・実行管理用のエントリプレース）
    - monitoring/            — （監視用コード置き場）
    - (その他)

README にまとめた以外にも、品質チェックや監視、発注監査のためのテーブル/ユーティリティが多数実装されています。詳細は各モジュールの docstring を参照してください。

---

もし README に追加してほしい内容（例: CI/テストの実行方法、サンプル .env.example、具体的なジョブスケジューラ設定例）があれば教えてください。必要に応じて追記します。