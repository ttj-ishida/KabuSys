# KabuSys

KabuSys は日本株の自動売買・データプラットフォーム向けライブラリ群です。  
J-Quants などの外部データソースから市場データを取得し、DuckDB に格納、ファクター計算・特徴量生成・シグナル生成を行う研究〜本番向けの基盤機能を提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（target_date 時点のみ参照）
- DuckDB を単一ソースオブトゥルース（SSOT）として利用
- 冪等性（ON CONFLICT / トランザクション）を重視
- 外部依存は最小限（標準ライブラリ中心、必要に応じて duckdb / defusedxml 等）

---

## 主な機能一覧

- 環境変数 / 設定管理
  - 自動 .env ロード（プロジェクトルートを .git または pyproject.toml から探索）
  - 必須設定を明示的に取得する Settings API

- データ取得・保存（J-Quants クライアント）
  - 株価日足、財務データ、マーケットカレンダー取得（ページネーション対応、レートリミット・リトライ実装）
  - DuckDB へ冪等保存（raw → processed レイヤ）

- ETL パイプライン
  - 差分更新（最終取得日に基づく差分取得 + backfill）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェック（quality モジュール：欠損・スパイク等の検出）

- データスキーマ管理
  - DuckDB 向けのスキーマ初期化（raw / processed / feature / execution 層）

- 研究用ファクター計算 & 特徴量生成
  - momentum / volatility / value 等のファクター計算（prices_daily / raw_financials を参照）
  - クロスセクション Z スコア正規化

- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム抑制、BUY / SELL（エグジット）判定
  - signals テーブルへの冪等書き込み

- ニュース収集
  - RSS フィード収集（SSRF/サイズ/圧縮/XML脆弱性対策）
  - 記事の正規化・ID生成・raw_news 保存、銘柄抽出・紐付け

- マーケットカレンダー管理
  - 営業日判定、next/prev_trading_day、カレンダー更新ジョブ

- 監査（audit）用スキーマ（シグナル→発注→約定のトレースを保証）

---

## 必要条件

- Python 3.10 以上
  - （注）コード内で型注釈に `|` を使用しているため 3.10+ を想定しています。
- 必要なパッケージ（最低限）
  - duckdb
  - defusedxml

簡単なインストール例:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# 開発中であればプロジェクトルートから
# pip install -e . を使う想定（setup / pyproject がある場合）
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## 環境変数

設定は環境変数または .env ファイルから読み込まれます（自動ロードはプロジェクトルートを探索して行われます）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（必須は明記）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", ...)

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## セットアップ手順（最小手順）

1. リポジトリをクローン / プロジェクトを取得
2. 仮想環境を作る（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```
4. .env を作成（上記の環境変数を設定）
5. DuckDB スキーマを初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（主要API例）

以下はライブラリの代表的な呼び出し例です。実運用では適切なロギング・例外処理を行ってください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL（市場カレンダー／株価／財務の差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルトで today を対象
print(result.to_dict())
```

- マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved rows:", saved)
```

- ニュース収集（既知銘柄コードセットを渡す）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例
result = run_news_collection(conn, known_codes=known_codes)
print(result)
```

- 特徴量構築（strategy 層）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, date(2024, 1, 31))
print(f"upserted {n} features")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, date(2024, 1, 31))
print(f"generated {count} signals")
```

- J-Quants からのデータ取得（低レベル）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from datetime import date

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って自動取得
quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ディレクトリ構成（概観）

リポジトリのルート想定（src レイアウト）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - data/
    - __init__.py
    - schema.py                    — DuckDB スキーマ定義・init_schema / get_connection
    - jquants_client.py            — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - news_collector.py            — RSS 収集・raw_news 保存・銘柄抽出
    - calendar_management.py       — マーケットカレンダー管理（判定 / 更新ジョブ）
    - stats.py                     — zscore_normalize 等統計ユーティリティ
    - features.py                  — features インターフェース（再エクスポート）
    - audit.py                     — 監査ログスキーマ（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py           — momentum / volatility / value の計算
    - feature_exploration.py       — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       — build_features（正規化・フィルタ・UPSERT）
    - signal_generator.py          — generate_signals（final_score, BUY/SELL）
  - execution/                      — 発注 / ブローカー連携周り（空パッケージ / 拡張想定）
  - monitoring/                     — 監視・アラート周り（空パッケージ / 拡張想定）
- pyproject.toml / setup.cfg 等（プロジェクトルートにある想定）
- .env, .env.local, .env.example（機密は .env で管理）

各モジュールはドキュメントストリングで設計方針・処理フローが詳細に書かれているため、利用箇所の docstring を参照してください。

---

## 注意事項 / 運用上のヒント

- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。運用時は適切な永続領域を確保してください。
- J-Quants のレートリミット（120 req/min）や API の仕様に合わせて ETL スケジュールを設計してください。
- 本リポジトリには実際の発注（ブローカー接続）部分に関する実装は限定的です。特に live 環境ではリスク管理・冗長性を十分検討の上で実装・テストを行ってください。
- .env に機密情報を置く場合はリポジトリに含めないよう .gitignore 設定を行ってください。
- 自動 .env ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で便利です）。

---

以上が README.md の概要です。必要があれば、README に含めるサンプルコマンドや .env.example の具体的なテンプレート、CI/デプロイ手順、詳細な API ドキュメント抜粋などを追加します。どの情報を優先して追加しますか？