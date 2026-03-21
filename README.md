# KabuSys

バージョン: 0.1.0

日本株向けの自動売買プラットフォーム用ライブラリ（データ収集 / ETL / 研究用ファクター計算 / 戦略シグナル生成 / ニュース収集 / DuckDB スキーマ管理 等）です。  
このリポジトリは、J-Quants API を利用した市場データ取得、DuckDB を用いたデータ永続化、戦略用の特徴量構築とシグナル生成、ニュース収集のユーティリティを含みます。

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足、財務データ、JPX マーケットカレンダーの取得（ページネーション対応）
  - レートリミット遵守、リトライ・トークン自動更新
  - DuckDB への冪等保存（ON CONFLICT / upsert）

- ETL パイプライン
  - 差分ロード（最終取得日からの差分取得）／バックフィル／品質チェック
  - 市場カレンダー先読み（lookahead）

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - テーブル初期化ユーティリティ（init_schema）

- 研究（research）用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（スピアマンρ）計算、ファクター統計サマリ
  - Z スコア正規化ユーティリティ

- 戦略
  - 特徴量合成（正規化・ユニバースフィルタ）→ features テーブル保存
  - final_score 計算に基づく BUY / SELL シグナル生成（signals テーブルへ書込）

- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 制限、XML の安全パース）
  - raw_news / news_symbols への冪等保存、銘柄コード抽出

- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day 等の営業日ロジック
  - カレンダー更新ジョブ

---

## 要求環境 / 依存関係

- Python 3.10 以上（PEP 604 の型表記等を使用）
- 必須ライブラリ（例）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクトに requirements.txt があれば:
# python -m pip install -r requirements.txt
```

（パッケージ配布用に setup/pyproject を用意する場合は `pip install -e .` を想定）

---

## 環境変数 / 設定

設定は環境変数、またはプロジェクトルートの `.env` / `.env.local` より自動読み込みされます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意/デフォルト値を持つ環境変数:
- KABU_API_BASE_URL     : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite path（監視用 DB、デフォルト: data/monitoring.db）
- KABUSYS_ENV           : execution 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL             : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)（デフォルト: INFO）

例（`.env`）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

設定はコード中で `from kabusys.config import settings` を通じて参照可能です（例: `settings.jquants_refresh_token`, `settings.duckdb_path`）。

---

## セットアップ手順（ローカル）

1. リポジトリをクローン / 取得
2. Python 3.10+ 環境を準備（venv 推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```
4. 必要な環境変数を `.env` に設定（上記参照）
5. DuckDB スキーマ初期化（下記の使い方参照）

---

## 使い方（主要な操作サンプル）

以下は Python スクリプト / REPL からの使い方例です。

- DuckDB スキーマの初期化:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイルベース DB を初期化
conn = init_schema(settings.duckdb_path)

# インメモリ DB を使う場合
# conn = init_schema(":memory:")
```

- 日次 ETL 実行（J-Quants からの差分取得 → 保存 → 品質チェック）:
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（features テーブルへ書き込む）:
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 15))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへ書き込む）:
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2024, 1, 15))
print(f"signals written: {total_signals}")
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 有効な銘柄コードセット（例: 全銘柄リスト）
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)
```

- カレンダー更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- 研究・計算モジュール（kabusys.research.*）は prices_daily / raw_financials を参照するため、ETL 後に使用してください。
- データ取得系（J-Quants）を動かすには `JQUANTS_REFRESH_TOKEN` が必須です。

---

## 自動環境読み込み停止（テスト時等）

`kabusys.config` はパッケージのロード時にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みします。自動読み込みを無効にするには環境変数を設定して起動してください:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
# または .env に設定している場合はプロセス環境で上書き
```

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要モジュール構造（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py      -- RSS 収集 / 前処理 / DB 保存
    - schema.py              -- DuckDB スキーマ定義 / init_schema
    - stats.py               -- Z スコア等統計ユーティリティ
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py -- カレンダー更新・営業日ロジック
    - features.py            -- data 層の特徴量ユーティリティ再エクスポート
    - audit.py               -- 監査ログスキーマ（signal_events / order_requests / executions）
    - ...（その他データ関連）
  - research/
    - __init__.py
    - factor_research.py     -- モメンタム / ボラティリティ / バリュー 等の計算
    - feature_exploration.py -- 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py -- features の組成・Z 正規化・ユニバースフィルタ
    - signal_generator.py    -- final_score 計算・BUY/SELL シグナル生成
  - execution/               -- 発注 / 実行層（ディレクトリは存在、実装は別途）
  - monitoring/              -- 監視・メトリクス（将来的な実装領域）

（上記は抜粋です。詳細は各モジュールの docstring / ソースを参照してください。）

---

## 開発・貢献

- 静的型チェック・ユニットテスト・CI を整備することを推奨します。
- 変更を加える場合は、DB スキーマの互換性と冪等性に注意してください（DDL の変更はマイグレーションを検討）。

---

## 注意事項 / セキュリティ

- RSS フィード取得時は SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査）を実装しています。外部 URL の取扱いは慎重に行ってください。
- すべてのタイムスタンプは UTC を使用する設計になっています。運用時はログと DB の時刻基準を統一してください。
- 実際の発注（ライブ運用）を行う場合は、paper_trading / live の区別やログ・監査情報の取り扱いを厳密にしてください。
- 環境変数やトークンは漏洩しないように管理してください。

---

この README はコードベースから抽出した主要情報のサマリです。実際の仕様詳細（StrategyModel.md / DataPlatform.md / Research 文書等）がある場合、それらを参照してください。必要であれば README を拡張して CLI コマンドやサンプルジョブ、デプロイ手順を追加できます。