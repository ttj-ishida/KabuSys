# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ集

このリポジトリは、J-Quants 等のデータソースから市場データ・財務データ・ニュースを取得して DuckDB に保存し、特徴量生成・シグナル生成・監査ログ管理を行うことを目的としたモジュール群です。研究（research）と本番（execution）を分離した設計で、ETL → feature → signal → execution のワークフローをサポートします。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数 / 設定
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API から日足・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS ベースのニュース収集と記事→銘柄の紐付け
- 研究用に用意されたファクター計算（Momentum / Volatility / Value）と特徴量正規化（Zスコア）
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- 発注／約定／ポジション等の監査ログを保持するスキーマ
- カレンダー管理・ETL パイプラインの自動化支援

設計上の留意点：
- ルックアヘッドバイアスの排除（target_date 時点のデータのみを参照）
- 冪等性（DuckDB への保存は ON CONFLICT で更新）
- ネットワーク／API 呼び出しに対するレート制御・リトライ
- 外部依存を最小化（標準ライブラリ + 最低限のパッケージ）

---

## 機能一覧

主な機能（モジュール）:

- data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・レート制限・保存関数含む）
  - pipeline: 日次 ETL（市場カレンダー、日足、財務）の差分取得と保存ロジック
  - news_collector: RSS フィード収集、前処理、raw_news / news_symbols への保存
  - schema: DuckDB 用のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - calendar_management: JPX カレンダーの管理・営業日判定ユーティリティ
  - stats: zscore 正規化などの統計ユーティリティ
- research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）計算・統計サマリー
- strategy
  - feature_engineering: 生ファクターの正規化・ユニバースフィルタ・features テーブルへの書き込み
  - signal_generator: features と ai_scores を統合して BUY / SELL シグナルを生成（signals テーブルへ）
- execution: （パッケージ存在、将来的な発注ロジック・ブローカー連携）
- monitoring / audit: 監査ログや実行トレースを保持するためのスキーマ（audit モジュール等）

---

## セットアップ手順

動作要件（推奨）
- Python 3.10+
- DuckDB
- ネットワークアクセス（J-Quants、RSS）

基本的なセットアップ手順:

1. リポジトリをクローン
   ```bash
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - このコードベースで直接参照されている主な外部ライブラリ:
     - duckdb
     - defusedxml
   - pip でインストール:
   ```bash
   pip install duckdb defusedxml
   ```
   - （プロジェクトに requirements.txt がある場合はそれを利用してください）
   - その他、運用で使う場合は Slack SDK 等を追加でインストールすることがあります。

4. 環境変数を設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（ただしテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数などは後述の「環境変数 / 設定」を参照してください。

5. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトから実行:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイルが無ければ作成される
   conn.close()
   ```

---

## 使い方（簡易サンプル）

ここでは代表的なワークフローの例を示します。

1) DuckDB スキーマを初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants の認証トークンは環境変数で管理）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量を構築（features テーブルの生成）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals

num = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals written: {num}")
```

5) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は銘柄抽出時に用いる有効なコード集合（例: set(["7203","6758",...])）
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)
```

注意点:
- 実運用ではログ設定、エラーハンドリング、認証トークン管理（refresh token → id token 取得）を適切に行ってください。
- ETL 処理・シグナル生成は冪等で設計されています（同一 target_date で上書き）。

---

## 環境変数 / 設定

kabusys は .env ファイル（プロジェクトルート）または OS 環境変数から設定を読み込みます。自動読み込みはデフォルトで有効です（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

主な設定項目（Settings クラス参照）:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- kabuステーション（発注／ブローカー）
  - KABU_API_PASSWORD (必須): kabu API のパスワード
  - KABU_API_BASE_URL (任意): デフォルト http://localhost:18080/kabusapi
- Slack（通知等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (省略可): 例 "data/kabusys.duckdb"（Settings.duckdb_path）
  - SQLITE_PATH (省略可): 例 "data/monitoring.db"
- 実行環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

例 `.env`（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 注意事項 / 運用上のヒント

- DuckDB ファイルはアプリが動作するユーザー権限で書き込み可能な場所に配置してください（デフォルト data/）。
- J-Quants のレート制限に注意（実装内で 120 req/min の制御あり）。
- RSS フィード取得は SSRF 対策や受信サイズ制限を組み込んでいますが、外部フィードの信頼性は常に検証してください。
- シグナル → 実際の発注フローは execution 層とブローカー API に依存します。運用環境（live）の場合は必ず paper_trading（検証口座）で十分なテストを行ってください。
- 自動環境変数ロードが不要なテストでは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要なファイル・パッケージ構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / Settings 管理
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント + 保存関数
    - news_collector.py             -- RSS 収集・保存・銘柄抽出
    - schema.py                     -- DuckDB スキーマ定義と初期化
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - stats.py                      -- zscore_normalize 等の統計ユーティリティ
    - calendar_management.py        -- カレンダー管理・営業日ユーティリティ
    - audit.py                      -- 監査ログ用スキーマ定義（signal_events, order_requests, executions など）
    - features.py                   -- data.stats のエクスポート
  - research/
    - __init__.py
    - factor_research.py            -- momentum/volatility/value の計算
    - feature_exploration.py        -- 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        -- features テーブル作成（正規化・ユニバースフィルタ）
    - signal_generator.py           -- features + ai_scores → signals 生成
  - execution/                       -- 発注・実行関連（初期パッケージ）
  - monitoring/                      -- 監視系（DB monitoring 用 SQLite パス等）

補足:
- schema.py により Raw / Processed / Feature / Execution 層のテーブルがすべて定義されています。
- research モジュールは外部ライブラリに依存せず、研究用途での利用を想定しています。

---

以上が README.md のサンプルです。必要があれば、以下について追記できます:
- CI / テストの実行方法（ユニットテストの例）
- 具体的な運用スケジュール（cron 例: 夜間 ETL → 朝シグナル生成）
- requirements.txt / packaging 手順
- Slack 通知・監視の設定サンプル

どの内容を優先して詳述しますか？