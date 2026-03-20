# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。  
J-Quants 等の外部データソースから市場データを取得して DuckDB に蓄積し、リサーチ／特徴量作成／シグナル生成／（発注）監査までのワークフローを提供します。  
このリポジトリはデータ取得・ETL、研究用ファクター計算、特徴量エンジニアリング、シグナル生成、ニュース収集、マーケットカレンダー管理、スキーマ／監査ロジックなどを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 主な機能一覧

- データ取得
  - J-Quants API クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レート制御・リトライ・トークン自動リフレッシュ
- ETL パイプライン
  - 差分取得（バックフィル対応）・品質チェック・日次 ETL 実行（run_daily_etl）
- DuckDB スキーマ管理
  - init_schema によるスキーマ作成（Raw / Processed / Feature / Execution 層）
- 研究・ファクター計算
  - momentum / volatility / value 等のファクター計算（research/factor_research.py）
  - 将来リターン、IC、統計サマリー（research/feature_exploration.py）
- 特徴量エンジニアリング
  - 生ファクターの正規化・フィルタリング・features テーブルへの UPSERT（strategy/feature_engineering.py）
- シグナル生成
  - features と ai_scores の統合、最終スコア算出、BUY/SELL シグナル生成（strategy/signal_generator.py）
  - Bear レジーム抑制、エグジット（ストップロス等）
- ニュース収集
  - RSS 取得・前処理・記事保存・銘柄抽出（data/news_collector.py）
  - SSRF 対策・XML 脆弱性対策・サイズ制限など安全実装
- マーケットカレンダー管理
  - 営業日判定 / 翌営業日・前営業日取得 / カレンダー更新ジョブ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義（永続的なトレーサビリティ）

---

## 要件（推奨）

- Python 3.10 以上（PEP 604 の型表記や型ヒントを利用しているため）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリのみで動く部分も多いですが、上記は必須です。

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージ化されている場合:
# pip install -e .
```

---

## 環境変数（設定）

パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（任意、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（任意、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（任意、デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

（.env.example を用意して必要値を設定してください）

---

## セットアップ手順（概要）

1. Python 仮想環境を作成・有効化
2. 依存パッケージをインストール（duckdb, defusedxml など）
3. プロジェクトルートに `.env`（または `.env.local`）を作成し必要な環境変数を設定
4. DuckDB スキーマ初期化（init_schema を呼ぶ）

サンプル（Python スクリプト）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数やデフォルトから取得されます
conn = init_schema(settings.duckdb_path)
print("DuckDB initialized:", settings.duckdb_path)
conn.close()
```

---

## 使い方（簡単な例）

以下は主要なユースケースの最小例です。実運用ではログやエラーハンドリングを追加してください。

- DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL の実行（市場カレンダー・株価・財務の差分取得＋品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())
```

- 特徴量作成（build_features）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date(2024, 1, 5))
print("features upserted:", n)
```

- シグナル生成（generate_signals）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date(2024, 1, 5))
print("signals written:", count)
```

- RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes に有効銘柄コードセットを渡すと記事と銘柄の紐付けも行う
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)
```

- カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## よく使う API（抜粋）

- kabusys.config.settings: 環境設定アクセサ
- kabusys.data.schema.init_schema(db_path): DuckDB スキーマ初期化
- kabusys.data.schema.get_connection(db_path): 既存 DB への接続
- kabusys.data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...)
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold, weights)
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
- kabusys.data.calendar_management.calendar_update_job

各関数はドキュメンテーション文字列が詳細な使い方と引数説明を含んでいますので、開発中は IDE の補完や `help()` を参照してください。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード含む）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 収集・保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py — zscore_normalize 等統計ユーティリティ
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - features.py — data.stats の再エクスポート
    - audit.py — 監査ログ（signal_events / order_requests / executions）
    - (他: quality.py 等の補助モジュールが想定される)
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（正規化・フィルタ）
    - signal_generator.py — final_score 計算 & signals 書き込み
  - execution/ — 発注周りの実装（パッケージ骨組み）
  - monitoring/ — 監視用モジュール（パッケージ骨組み）

---

## 注意事項 / 実運用におけるポイント

- 環境変数に機密情報（トークン等）が含まれるため管理に注意してください。
- DuckDB ファイルは共有アクセスに注意（同時書き込みやロック）。
- J-Quants API レート制限（120 req/min）に従う実装が組み込まれていますが、追加のエンドポイント利用時は負荷に注意してください。
- シグナル → 発注周り（execution 層）は外部ブローカー API と接続するための実装が必要です（骨組みは用意）。
- テスト環境では自動 .env ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用できます。

---

## 開発 / 貢献

- 各モジュールはユニットテスト可能な形（外部依存の注入、id_token の注入など）で設計されています。  
- 新機能追加やバグ修正の際は既存の ETL・スキーマ・研究ロジックの整合性（ルックアヘッドバイアス防止など）に注意してください。

---

必要であれば README に以下を追加できます：
- 具体的な .env.example（テンプレート）
- docker-compose / systemd ユニット例（バッチ自動化）
- CI / テスト実行方法（pytest 等）
- 実行例のより詳細なワークフロー（cron での run_daily_etl、シグナル→発注フロー例）

用途に合わせて追記します。必要な箇所を教えてください。