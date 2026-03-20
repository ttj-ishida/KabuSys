# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）

このリポジトリは、J‑Quants 等のデータソースから市場データを収集・整形し、
特徴量生成・シグナル算出・監査・発注基盤までを想定したモジュール群を提供します。
主に研究（research）、データ（data）、戦略（strategy）、発注（execution）層に分かれた設計です。

---

## 主な機能（概要）

- データ収集 & ETL
  - J‑Quants API クライアント（ページネーション、レート制限、リトライ、トークン自動更新）
  - RSS ニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - DuckDB への冪等保存（ON CONFLICT / トランザクション）
  - 市場カレンダー取得 / 営業日判定ロジック

- データ基盤
  - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - 統計ユーティリティ（Z スコア正規化 等）
  - ETL パイプライン（差分取得、バックフィル、品質チェック連携）

- 研究・特徴量
  - Momentum / Volatility / Value 系ファクター計算（prices_daily / raw_financials ベース）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ

- 戦略
  - 特徴量の正規化・合成（features テーブル生成）
  - AI スコアと統合した final_score 計算、BUY / SELL シグナル生成（signals テーブル）
  - Bear レジーム抑制、エグジット（ストップロス等）

- 監査・実行（基盤）
  - 監査テーブル（signal_events / order_requests / executions 等）の DDL 定義
  - signal_queue / orders / trades / positions 等を想定したスキーマ

---

## 必要な環境変数

kabusys は .env ファイルまたは環境変数から設定を読み込みます。自動ロードはプロジェクトルート（`.git` または `pyproject.toml`）を基準に行われます。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須／デフォルト）:

- JQUANTS_REFRESH_TOKEN (必須) — J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot Token
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - このコードベースで想定される主な依存:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 実際のプロダクトでは requirements.txt / pyproject.toml に依存関係をまとめてください。

4. 環境変数設定
   - ルートに `.env` または `.env.local` を作成するか、OS 環境変数を設定します。
   - 例: `.env` を作成して上の環境変数を記載。

5. パッケージを編集可能モードでインストール（任意）
   ```
   pip install -e .
   ```

---

## 使い方（簡単な例）

以下は主要ユースケースの Python スニペット例です。

- DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使ってクエリや ETL を実行できます
```

- 日次 ETL 実行（J‑Quants から差分取得 → 保存 → 品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 特徴量作成（feature_engineering.build_features）:
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, date(2025, 1, 31))
print(f"features upserted: {n}")
```

- シグナル生成（strategy.signal_generator.generate_signals）:
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, date(2025, 1, 31))
print(f"signals written: {total}")
```

- RSS ニュース収集 & 保存:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は既知銘柄コードのセット（抽出に利用）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

- カレンダー更新ジョブ（夜間バッチ想定）:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar rows saved: {saved}")
```

ログは環境変数 LOG_LEVEL で調整してください。

---

## 主要モジュール / ディレクトリ構成

（src/kabusys 以下の主要ファイルと役割）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数と設定取得（自動 .env ロード、必須チェック、env/log_level 判定）
  - data/
    - __init__.py
    - jquants_client.py
      - J‑Quants API クライアント（認証・ページネーション・保存ユーティリティ）
    - news_collector.py
      - RSS 取得、前処理、raw_news / news_symbols 保存
    - schema.py
      - DuckDB スキーマ DDL 一式と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - 日次 ETL（run_daily_etl など）、差分取得ロジック
    - calendar_management.py
      - 市場カレンダー管理（is_trading_day / next_trading_day 等）
    - features.py
      - data.stats の再エクスポート（互換インターフェース）
    - audit.py
      - 監査ログ用 DDL（signal_events, order_requests, executions 等）
    - (その他: quality 等の想定モジュールが呼び出されます)
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、ファクターサマリ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - raw ファクターの正規化・合成 → features テーブルに UPSERT
    - signal_generator.py
      - features と ai_scores を統合して final_score を算出し signals を作成
  - execution/
    - __init__.py
    - （発注・ブローカー連携の実装を想定）
  - monitoring/
    - （監視・アラート連携を想定）

---

## 設計上の重要ポイント（注意事項）

- 冪等性
  - DB への保存は ON CONFLICT / トランザクションを基本とし、繰り返し実行しても整合性を保ちます。

- ルックアヘッドバイアスの回避
  - 戦略・特徴量計算は target_date 時点までのデータのみを使用する設計です。

- レート制御・リトライ
  - J‑Quants クライアントはレート制限（120 req/min）を守るよう固定間隔スロットリングを行い、リトライ・トークン自動更新を備えます。

- セキュリティ
  - RSS 取得は SSRF 対策（スキーム検証・プライベートアドレス検出・リダイレクト検査）を実装しています。
  - XML パースは defusedxml を使用して安全化しています。

- テスト性
  - 主要関数は接続やトークンを引数で注入できるようにしており、単体テストの差替え（モック）が容易です。

---

## 開発にあたって

- 依存バージョンや CI、Lint、テストのセットアップはプロジェクトの方針に合わせて追加してください。
- 本 README はコードベースの概要と利用方法を補助するためのもので、実運用ではさらに運用手順（監視、バックアップ、シークレット管理、ロールバック方針等）を整備してください。

---

ご不明点や README に追記してほしいセクションがあれば教えてください。必要に応じてサンプル .env.example や CLI コマンド例、ユースケース別の手順を追加できます。