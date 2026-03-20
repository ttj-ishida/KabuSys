# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）

このリポジトリは、データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、監査ログなどを含む日本株自動売買システムのコアモジュール群を提供します。研究（Research）と本番（Execution）層を分離した設計になっており、DuckDB を用いたローカルデータレイヤーを中心に構成されています。

主な目的
- J-Quants API からのデータ取得と DuckDB への冪等保存
- 風味付けされたファクター（Momentum / Value / Volatility / Liquidity）の計算
- 正規化済み特徴量の保存（features テーブル）
- 最終スコア計算に基づく BUY/SELL シグナル生成（signals テーブル）
- RSS ベースのニュース収集と銘柄紐付け
- ETL パイプライン（差分取得、品質チェック、カレンダー管理）
- 監査用テーブル群（シグナル → 発注 → 約定 のトレース）

---

## 機能一覧

- 環境変数管理
  - .env / .env.local を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - 自動読み込みの無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ取得・保存
  - J-Quants クライアント（rate limit 対応、リトライ、トークン自動リフレッシュ）
  - raw_prices / raw_financials / market_calendar / raw_news などの保存関数（冪等）

- ETL & パイプライン
  - run_daily_etl: 市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分取得（最終取得日を基に差分を自動算出）とバックフィル対応

- 特徴量（Feature）処理
  - Research 層で計算した生ファクターを正規化・合成して features テーブルへ保存（build_features）
  - z-score 正規化ユーティリティ（data.stats.zscore_normalize）

- シグナル生成
  - 正規化済み特徴量と AI スコアを統合して final_score を計算（generate_signals）
  - Bear レジーム検知により BUY シグナル抑制、SELL のエグジット判定（ストップロス等）

- ニュース収集
  - RSS フィードから記事を取得、正規化、raw_news に冪等保存
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成
  - SSRF 防御、gzip サイズ検査、トラッキングパラメータ除去、銘柄コード抽出

- スキーマ / 監査
  - DuckDB スキーマ定義と初期化（init_schema）
  - 監査用テーブル群（signal_events, order_requests, executions など）

---

## 必要条件（推奨）

- Python 3.10+
- duckdb
- defusedxml
- （その他標準ライブラリのみで多くを実装しています）

簡易的なインストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発用にパッケージ化している場合:
# pip install -e .
```

依存関係はプロジェクト側で requirements.txt や pyproject.toml にまとめてください。

---

## 環境変数（重要）

以下はコード内で参照される主要な環境変数です（.env ファイルに設定できます）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（Execution 層で利用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意/デフォルトあり:
- KABUSYS_ENV — 環境 (development / paper_trading / live)（default: development）
- LOG_LEVEL — ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用等）ファイルパス（default: data/monitoring.db）

自動読み込みについて:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探し `.env` → `.env.local` の順で読み込みます。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で便利）。

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo_url>
   cd <repo_root>
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

2. 環境変数を作成
   - プロジェクトルートに `.env` を作成し、必須キーを設定します（例は下記）。

   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
   ```python
   from pathlib import Path
   import duckdb
   from kabusys.data.schema import init_schema, get_connection
   db_path = Path("data/kabusys.duckdb")
   conn = init_schema(db_path)  # テーブルを作成して接続を返します
   conn.close()
   ```

---

## 使い方（主要な操作例）

以下はよく使うワークフローのサンプルです。

- 日次 ETL を実行する（市場カレンダー、株価、財務、品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- 特徴量（features）を構築する
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 3, 1))
print(f"upserted features: {n}")
conn.close()
```

- シグナルを生成する
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals written: {count}")
conn.close()
```

- RSS ニュース収集ジョブを実行する
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出に使用する有効なコードの集合（例: {'7203', '6758', ...}）
results = run_news_collection(conn, known_codes=set())
print(results)
conn.close()
```

- J-Quants から生データを直接取得して保存する例
```python
from kabusys.data.schema import init_schema
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
saved = save_daily_quotes(conn, records)
print(f"saved rows: {saved}")
conn.close()
```

---

## 注意点・設計方針（抜粋）

- ルックアヘッドバイアス防止:
  - 特徴量計算・シグナル生成は target_date 時点で利用可能なデータのみを用いる設計。
  - J-Quants から取得したデータには fetched_at を付与して「いつ入手可能になったか」をトレース可能にしています。

- 冪等性:
  - データ保存関数（save_*）は ON CONFLICT を用いて重複を避けます。
  - ETL / features / signals の日付単位置換はトランザクション＋バルク挿入で原子性を保証します。

- セキュリティ / 安全性:
  - RSS フェッチ時は SSRF を防ぐためリダイレクト先・ホストの検査を実施。
  - defusedxml を用いて XML の悪用（XML Bomb 等）を防御。
  - J-Quants クライアントは rate limit（120 req/min）を固定間隔スロットリングで守ります。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・ディレクトリの概観です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - schema.py                     — DuckDB スキーマ定義・初期化
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - features.py                   — features 再エクスポート
    - calendar_management.py        — 市場カレンダー管理（is_trading_day 等）
    - audit.py                      — 監査ログテーブル定義
    - (その他: quality 等を想定)
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py        — 将来リターン・IC・サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        — 生ファクターの正規化→features 挿入
    - signal_generator.py           — final_score 計算→signals 挿入
  - execution/
    - __init__.py                   — 発注/約定/ポジション管理層用のプレースホルダ
  - monitoring/                      — 監視・外部統合用（存在する場合）

（実際のファイルは上記に示したソースコード群を参照してください）

---

## 追加情報 / 開発メモ

- 環境の切り替え（development / paper_trading / live）は `KABUSYS_ENV` で制御され、settings.is_live / is_paper / is_dev で判定できます。
- jquants_client の内部では自動的に id_token を取得・キャッシュし、401 で自動リフレッシュする実装があります。
- ETL の品質チェック（quality モジュール）は run_daily_etl から呼ばれ、重大度に応じた検出結果を ETLResult に格納します（quality モジュールは別実装を想定）。
- SQL 実行は DuckDB を前提に設計されています。大量データ投入時は適宜 VACUUM やパフォーマンスチューニングを検討してください。

---

## サポート / コントリビュート

バグ報告、提案、プルリクエストはリポジトリの Issue / PR をご利用ください。ドキュメントの改善、テスト追加、品質チェック拡張などの貢献を歓迎します。

---

以上が README.md の概要です。必要であれば、セットアップ用のスクリプト例（docker-compose、systemd タイマー、cron ジョブサンプル）や .env.example ファイル、依存関係一覧（requirements.txt / pyproject.toml）も追記します。どれを追加しますか？