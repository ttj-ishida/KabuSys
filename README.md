# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けのデータ収集・ETL・監査・実行基盤のコアライブラリです。  
J-Quants API や RSS を用いたデータ収集、DuckDB ベースのスキーマ管理、日次 ETL パイプライン、データ品質チェック、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限対応（120 req/min）、リトライ（指数バックオフ）、401 の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS 取得、XML の安全パース（defusedxml）、URL 正規化・トラッキング除去
  - SSRF 対策（スキーム検査、リダイレクト先のプライベートアドレス検査）
  - 記事ID は正規化後 URL の SHA-256（先頭32文字）で生成し冪等保存
  - bulk INSERT とトランザクションで効率的に保存、銘柄コード抽出・紐付け

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層を含むスキーマ定義
  - テーブル作成（冪等）とインデックス作成をサポート
  - 監査ログ（signal_events / order_requests / executions）用テーブル生成機能

- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル（後出し修正吸収）
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行して問題を収集

- カレンダー管理
  - JPX カレンダーの夜間差分更新ジョブ
  - 営業日判定・前後営業日取得・期間の営業日リスト取得等ユーティリティ

---

## 必要環境

- Python 3.10 以上（注: 型表記に `X | None` を使用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

その他、実運用では Slack や kabuステーション API など他モジュールを使う可能性があります（当該コードベースでは環境変数を通じた設定を用います）。

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# またはプロジェクトの requirements.txt があればそれを使用
```

---

## 環境変数（設定）

自動的に `.env` / `.env.local` をプロジェクトルートから読み込みます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（必須とデフォルト）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- システム
  - KABUSYS_ENV (任意, 値: development | paper_trading | live, デフォルト: development)
  - LOG_LEVEL (任意, 値: DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

Settings は `kabusys.config.settings` から参照できます。必須環境変数が欠落すると ValueError が投げられます。

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=********
KABU_API_PASSWORD=********
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # + プロジェクトの requirements.txt があればそれを使用
   # pip install -r requirements.txt
   ```

4. 環境変数を用意
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、上記の必須キーを設定してください。
   - テスト時や CI で自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DuckDB スキーマの初期化
   - Python REPL かスクリプト上で次を実行:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成して DB を初期化
   conn.close()
   ```

6. 監査ログスキーマ（任意）
   ```python
   from kabusys.data import schema, audit
   conn = schema.init_schema("data/kabusys.duckdb")
   audit.init_audit_schema(conn)
   ```

---

## 使い方（主要な API と実例）

以下は代表的な使い方サンプルです。適宜ロギング設定や例外処理を追加してください。

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data import schema, pipeline

# DB 初期化済みであること
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn)

print(result.to_dict())
```

- ニュース収集（RSS）を実行して DuckDB に保存
```python
from kabusys.data import schema, news_collector
conn = schema.init_schema("data/kabusys.duckdb")

# sources は {source_name: rss_url} の dict。省略時は DEFAULT_RSS_SOURCES を使用
known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄リストを用意
stats = news_collector.run_news_collection(conn, known_codes=known_codes)
print(stats)
```

- J-Quants トークン取得（直接利用する場合）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings の JQUANTS_REFRESH_TOKEN を使用
```

- DuckDB 接続を取得（スキーマ初期化は行わない）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## 主要モジュールの説明

- kabusys.config
  - 環境変数のロード・管理（.env 自動読み込み、必須値チェック）
- kabusys.data.jquants_client
  - J-Quants API との通信、ページネーション、保存ユーティリティ（DuckDB への保存関数含む）
- kabusys.data.news_collector
  - RSS フィードの安全な取得、記事正規化、DuckDB への保存、銘柄抽出
- kabusys.data.schema / audit
  - DuckDB のスキーマ定義と初期化関数、監査ログの初期化
- kabusys.data.pipeline
  - 差分取得・バックフィル・日次 ETL 実行と品質チェックの統合
- kabusys.data.quality
  - 欠損・重複・スパイク・日付不整合の検出ロジック
- kabusys.data.calendar_management
  - 市場カレンダーの管理・営業日判定ユーティリティ
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 戦略・発注・監視向け名前空間（本体実装は該当ディレクトリ内に追加実装を想定）

---

## ディレクトリ構成

リポジトリ内の主なファイル・モジュール（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
      - (戦略モジュールを配置)
    - execution/
      - __init__.py
      - (発注・実行モジュールを配置)
    - monitoring/
      - __init__.py
      - (監視・メトリクス関連を配置)

- .env, .env.local (プロジェクトルートに置く想定)
- data/ (デフォルトの DB 保存先)
  - kabusys.duckdb (DUCKDB_PATH デフォルト)
  - monitoring.db (SQLITE_PATH デフォルト)

---

## 運用上の注意 / ベストプラクティス

- 環境変数は機密情報を含むため、`.env` をバージョン管理に含めないでください。`.env.example` を用意して必要項目を文書化するとよいです。
- J-Quants のレート制限（120 req/min）を遵守していますが、大量取得や複数プロセスによる同時実行は注意してください。
- DuckDB ファイルは単一プロセスでの高速アクセスに向いています。複数プロセスから同時書き込みが必要な場合は運用設計を検討してください。
- RSS 取得時の SSRF や XML 攻撃対策を組み込んでいますが、外部フィードの信頼性は常に監視してください。
- 品質チェックの結果は運用者による評価・対応を前提にしています。ETL 停止のポリシーは運用要件に合わせて実装してください。

---

## 付録 — よく使う関数まとめ

- DB スキーマ初期化
  - data.schema.init_schema(db_path)
- 監査スキーマ初期化
  - data.audit.init_audit_schema(conn) / data.audit.init_audit_db(db_path)
- 日次 ETL
  - data.pipeline.run_daily_etl(conn, target_date=None, ...)
- ニュース収集
  - data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- 品質チェック
  - data.quality.run_all_checks(conn, target_date=None, reference_date=None)

---

ご不明点や README に追記したい情報（例: CI 手順、Dockerfile、具体的な運用例、.env.example）の要望があれば教えてください。README をプロジェクトポリシーやデプロイ手順に合わせて拡張します。