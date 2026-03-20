# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants から市場データを取得して DuckDB に蓄積し、研究用ファクターの計算、特徴量正規化、シグナル生成、ニュース収集、ETL パイプライン、監査ログ管理などを提供します。

---

## プロジェクト概要

KabuSys は次のレイヤーを備えた、日本株自動売買システム向けの共通ライブラリです。

- Data 層: J-Quants API クライアント、RSS ニュース収集、DuckDB スキーマ定義・初期化、ETL パイプライン、品質チェック用ユーティリティ
- Research 層: ファクター計算（モメンタム・ボラティリティ・バリュー等）、特徴量探索・IC 計算
- Strategy 層: 特徴量の正規化・合成（features テーブル作成）、最終スコア計算および売買シグナル生成（signals テーブルへ保存）
- Execution / Audit 層: 発注・約定・ポジション・監査ログ用スキーマを定義（発注の送受信は外部ブリッジで実装）

設計方針の主なポイント:
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- DuckDB を中心とした冪等的な保存（ON CONFLICT / トランザクション）
- 外部依存を最小限に（標準ライブラリ + 必要最小限の外部モジュール）
- API レート制御・リトライ、RSS の SSRF 対策などの実運用考慮

---

## 主な機能一覧

- J-Quants API クライアント
  - 株価日足（ページネーション対応）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー
  - トークン取得・自動リフレッシュ・レート制限・リトライ実装

- DuckDB スキーマ管理
  - raw / processed / feature / execution 層のテーブル定義
  - インデックス定義、init_schema による初期化

- ETL パイプライン
  - 日次 ETL（calendar / prices / financials の差分取得・保存）
  - 差分取得とバックフィルのサポート
  - 品質チェックの呼び出しフック

- Research / Feature 工程
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - Z スコア正規化ユーティリティ

- Strategy（特徴量生成・シグナル生成）
  - build_features: 生ファクターを正規化して features テーブルに UPSERT
  - generate_signals: features + ai_scores から final_score を計算し signals を作成
  - Bear レジームフィルタ、売買（BUY/SELL）ルール、エグジット判定（ストップロス等）

- ニュース収集
  - RSS フィード取得（gzip 対応、SSRF 対策、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存

- 監査ログ / Audit スキーマ
  - signal_events / order_requests / executions などトレーサビリティ用テーブル

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必須（本コードベースで参照）：duckdb, defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトに requirements ファイルがある場合はそれを利用してください：
   pip install -r requirements.txt）

3. リポジトリをパッケージとしてインストール（開発モード）
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（pyproject.toml や .git があるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須の環境変数（主要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネルID（必須）

任意の設定（デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）

例 .env（テンプレート）
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

## 使い方（代表的な関数・ワークフロー）

以下は Python REPL やスクリプトからの利用例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = init_schema(":memory:")
```

- 日次 ETL 実行（J-Quants の API トークンは環境変数から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量生成（features テーブル作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2025, 3, 1))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブル作成）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals written: {total_signals}")
```

- RSS ニュース収集ジョブ（既知銘柄セットを与えて news_symbols も生成）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- J-Quants からの日足取得と保存（個別利用）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

ログレベルや KABUSYS_ENV に応じて動作モード（開発・ペーパートレード・本番）を切り替えできます。設定は環境変数 `KABUSYS_ENV` を利用してください。

---

## ディレクトリ構成

主要なファイル・パッケージ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存）
    - news_collector.py      -- RSS ニュース収集・保存
    - schema.py              -- DuckDB スキーマ定義・初期化
    - stats.py               -- 汎用統計ユーティリティ（zscore_normalize）
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py -- マーケットカレンダー管理
    - features.py            -- features インターフェース（再エクスポート）
    - audit.py               -- 監査ログスキーマ
    - execution/             -- 実行関連（発注連携などのためのパッケージ）
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム / ボラティリティ / バリュー等の計算
    - feature_exploration.py -- forward returns, IC, summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py -- build_features（特徴量作成）
    - signal_generator.py    -- generate_signals（最終スコア・シグナル生成）
  - execution/               -- 発注統合・kabu 接続（実装の拡張部分）
  - monitoring/              -- 監視/メトリクス関連（別モジュールで実装想定）

簡易ツリー（抜粋）
```
src/kabusys/
├── config.py
├── data/
│   ├── jquants_client.py
│   ├── news_collector.py
│   ├── schema.py
│   ├── pipeline.py
│   └── ...
├── research/
│   ├── factor_research.py
│   └── feature_exploration.py
├── strategy/
│   ├── feature_engineering.py
│   └── signal_generator.py
└── ...
```

---

## 注意事項 / 補足

- DuckDB のバージョンや機能差（外部キーの ON DELETE 等）に依存する部分があるため、README 内のスキーマ初期化や運用時は実行環境での DuckDB バージョン互換性確認を推奨します（コード内に注記あり）。
- J-Quants API のレート制限や credential の取り扱いには注意してください。トークンの保護は運用責任です。
- 自動で .env を読み込む仕組みがありますが、CI/テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して外部依存を切ることができます。
- システム全体の動作には追加のラッパー（ジョブスケジューラ、broker adapter、Slack 通知等）が必要です。本ライブラリは基盤部分を提供することを目的としています。

---

何か追加で README に載せたい情報（例えば具体的な API キー取得手順、詳しいテーブル定義ドキュメントのリンク、CI ワークフロー例など）があれば教えてください。README を拡張して記載します。