# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。J-Quants から市場データや財務データを取得して DuckDB に蓄積し、ファクター計算・特徴量生成・シグナル生成・ニュース収集などの一連処理を提供します。発注層（ブローカー接続）や監視・監査のためのスキーマも含んでおり、研究 → バックテスト → 実運用に向けた機能群を備えています。

主要な設計方針の抜粋
- ルックアヘッドバイアスを避けるため、常に target_date 時点で利用可能なデータのみを使用する設計
- DuckDB をデータストアに採用し、冪等（ON CONFLICT）／トランザクション単位の置換を重視
- 外部 API 呼び出しにはレート制御・リトライ・トークン自動更新などを実装
- ニュース収集では SSRF / XML Bomb / 大量レスポンス対策を実装

---

## 機能一覧

- データ取得（J-Quants API）
  - 株価日足（OHLCV）取得・保存（ページネーション対応・トークン自動リフレッシュ）
  - 財務データ（四半期版）取得・保存
  - JPX マーケットカレンダー取得・保存
- ETL / パイプライン
  - 差分取得（最終取得日の追跡、backfill による後出し修正吸収）
  - 日次 ETL (run_daily_etl)
  - 市場カレンダー更新ジョブ
- データスキーマ / 初期化
  - DuckDB に必要なテーブル群（Raw / Processed / Feature / Execution / Audit）を作成する init_schema
- 特徴量・リサーチ
  - momentum / volatility / value 等のファクター計算
  - クロスセクションの Z スコア正規化ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリー
- 特徴量パイプ（戦略用）
  - features テーブル構築（build_features）
  - features と AI スコアを統合してシグナル生成（generate_signals）
  - エグジット判定（ストップロスやスコア低下）
- ニュース収集
  - RSS フィード取得（SSRF / サイズ / XML 安全対策）
  - raw_news / news_symbols への冪等保存
  - テキスト前処理と銘柄コード抽出
- 監査ログ（audit）スキーマ
  - signal_events / order_requests / executions 等、発注から約定までのトレーサビリティ

---

## 必要条件

- Python 3.10 以上（型表記に `X | None` を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib 等を多用（追加外部ライブラリは最小限）

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## 環境変数

このプロジェクトは環境変数 / .env を用いて機密情報やパスを管理します。パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）で `.env` / `.env.local` を自動読込します。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（アプリ起動・一部機能で必要）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注層使用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）

設定は `kabusys.config.settings` から参照できます。必須変数が不足した場合は Settings のプロパティで ValueError が発生します。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに pyproject / requirements があればそれに従う）
   - 開発インストール（任意）:
     - pip install -e .

4. 環境変数ファイルを作成
   - プロジェクトルートに `.env` を置く（`.env.example` を用意しておくと便利）
   - 例:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=./data/kabusys.duckdb

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     - from kabusys.data.schema import init_schema, get_connection
     - conn = init_schema(settings.duckdb_path)  # settings は kabusys.config.settings
   - またはメモリ DB で試す:
     - conn = init_schema(":memory:")

---

## 使い方（主要な API サンプル）

以下は簡単な利用例です。実運用ではエラーハンドリングやログ設定を適宜追加してください。

- DuckDB 初期化（1回だけ実行）
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL（データ取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定せず今日のETL
print(result.to_dict())
```

- 市場カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 特徴量の構築（戦略層）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date(2024, 1, 5))
print(f"features upserted: {count}")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection(settings.duckdb_path)
total = generate_signals(conn, target_date=date(2024, 1, 5))
print(f"signals written: {total}")
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
# known_codes: 銘柄抽出に使う有効なコードセット（省略可能）
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- J-Quants から直接データを取得して保存（テスト用）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
saved = jq.save_daily_quotes(conn, records)
```

---

## ログ・デバッグ

- 環境変数 `LOG_LEVEL`（DEBUG / INFO / ...）でログ出力レベルを制御します（Settings.log_level）。
- 自動 .env 読込が不要なテスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主なファイル）

以下はリポジトリ内の主要なモジュール構成（src/kabusys 以下）です。実際のファイルはプロジェクトのツリーと差異がある場合があります。

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（取得・保存）
    - news_collector.py                 — RSS ニュース収集
    - schema.py                         — DuckDB スキーマ定義・初期化
    - stats.py                          — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - features.py                       — features 公開インターフェース
    - calendar_management.py            — カレンダー管理（営業日判定等）
    - audit.py                          — 監査ログ用スキーマ
    - (他: quality 等の補助モジュールが存在する想定)
  - research/
    - __init__.py
    - factor_research.py                — ファクター計算（momentum/volatility/value）
    - feature_exploration.py            — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py            — features の構築（build_features）
    - signal_generator.py               — シグナル生成（generate_signals）
  - execution/                          — 発注 / 約定関連（実装のエントリポイント）
  - monitoring/                         — 監視 / モニタリング関連

---

## 開発・テストのヒント

- DuckDB の初期化は一度だけ実行すれば良い（init_schema）。テストでは ":memory:" を使うと便利。
- 設定の自動読み込みは .env / .env.local を優先的に読みます。テストで環境汚染を避ける場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- ニュース収集や外部 API 呼び出し部はネットワーク I/O を含むため、ユニットテストでは該当関数の HTTP 呼び出し部分をモックすることを推奨します（例: news_collector._urlopen や jquants_client._request を差し替え）。

---

## ライセンス / 貢献

（プロジェクトに合わせてここにライセンス・貢献方法を追記してください）

---

この README はコードベースの公開インターフェースと運用上の注意点を簡潔にまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md / DataSchema.md 等）や運用手順は別途ドキュメントを参照してください。必要であれば README に追記・改善します。