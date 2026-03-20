# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
Data（データ収集・ETL・スキーマ）・Research（ファクター計算・解析）・Strategy（特徴生成・シグナル生成）・Execution（発注関連）などをモジュール化して提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主な役割は次の通りです。

- J-Quants API からの株価・財務・カレンダー等のデータ取得（差分取得・ページネーション対応・リトライ・レート制御）
- DuckDB によるデータ永続化（スキーマ定義・初期化・冪等保存）
- ETL パイプライン（差分更新、バックフィル、品質チェックの統合）
- ファクター計算・特徴量エンジニアリング（ルックアヘッドバイアス回避設計）
- シグナル生成（複数ファクター・AIスコアの統合、BUY/SELL ロジック）
- ニュース収集（RSS からの収集、SSRF 対策、テキスト前処理、銘柄抽出）
- マーケットカレンダー管理（営業日判定、Next/Prev 営業日の取得）
- 監査ログ（発注→約定までのトレース用スキーマ）

設計方針としては「冪等性」「ルックアヘッドバイアスの排除」「外部依存の最小化（可能な限り標準ライブラリ）」が重視されています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - schema: DuckDB のスキーマ定義と init_schema()
  - pipeline: 日次 ETL（run_daily_etl）や個別 ETL ジョブ
  - news_collector: RSS 収集・保存・銘柄紐付け
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration: 将来リターン、IC、統計サマリ等の解析ユーティリティ
- strategy/
  - feature_engineering.build_features(conn, target_date): raw factor を正規化して features に保存
  - signal_generator.generate_signals(conn, target_date, ...): features と ai_scores を統合して signals を生成
- monitoring / execution:
  - 発注・約定・ポジション周りのスキーマ・監査ログ（audit モジュール）

その他、ニュース収集のセキュリティ対策（SSRF ブロック・最大レスポンスバイト制限）や、DuckDB に対する冪等保存（ON CONFLICT）など多数の実用機能を備えます。

---

## 前提（動作環境／依存）

- Python 3.10 以上（型ヒントで | を使用しているため）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- ネットワーク経由の機能を使う場合は J-Quants API のリフレッシュトークン等が必要

（実プロジェクトでは requirements.txt / pyproject.toml を用意してください。ここでは最小限の依存を明記しています。）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

---

## 環境変数（.env の例）

config.Settings が参照する主要な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

自動ロード:
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡単な .env.example:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境の作成と依存インストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   # 実運用では他に requests 等が必要になる場合があります
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` を作成（上の例参照）
   - または環境変数を直接エクスポート

4. DuckDB スキーマ初期化
   Python REPL かスクリプトから:
   ```py
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   - ":memory:" を渡せばインメモリ DB が使えます。
   - init_schema はディレクトリを自動作成し、DDL を冪等で実行します。

---

## 使い方（主要 API の例）

以下は最小限の利用例です。実運用ではログ設定や例外処理を追加してください。

- DuckDB 接続取得 / スキーマ初期化
```py
from kabusys.data.schema import init_schema, get_connection
conn = init_schema("data/kabusys.duckdb")
# 既存DBへ接続のみ:
# conn = get_connection("data/kabusys.duckdb")
```

- 日次 ETL の実行（市場カレンダー取得・株価・財務の差分取得・品質チェック）
```py
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を渡さなければ today
print(result.to_dict())
```

- 特徴量の構築（features テーブルへ保存）
```py
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2025, 3, 1))
print("features upserted:", count)
```

- シグナル生成（signals テーブルへ保存）
```py
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, date(2025, 3, 1), threshold=0.6)
print("signals written:", n)
```

- ニュース収集（RSS 取得→raw_news 保存→news_symbols 紐付け）
```py
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コード（文字列）のセット（抽出用）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # 各ソースの新規保存件数
```

- カレンダー更新ジョブ
```py
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## 実装上のポイント / 注意事項

- J-Quants クライアントは 120 req/min のレート制限を守るため内部でスロットリングしています。また 408/429/5xx に対する指数バックオフリトライ、401 時はリフレッシュトークンでトークン再取得を行います。
- news_collector は SSRF 対策や gzip サイズ検査、XML の安全パーシング（defusedxml）等の安全措置を備えています。
- ETL パイプラインは差分更新とバックフィル（デフォルト 3 日）を行います。品質チェックは pipeline.run_daily_etl のオプションで有効化できます。
- features / signals への書き込みは日付単位で置換（DELETE + INSERT）することで冪等性を確保しています。
- 設定の自動読み込みは .env / .env.local を参照します。テスト時などに自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理（Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch_*/save_*）
    - schema.py                 — DuckDB スキーマ定義・init_schema/get_connection
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - news_collector.py         — RSS 収集・保存・銘柄抽出
    - calendar_management.py    — カレンダー更新・営業日判定ユーティリティ
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - features.py               — data.stats の再エクスポート
    - audit.py                  — 監査ログ用 DDL（signal_events, order_requests, executions 等）
    - quality.py (?)            — 品質チェック（pipeline から参照。今回抜粋に未表示の可能性）
  - research/
    - __init__.py
    - factor_research.py        — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py    — 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py    — build_features
    - signal_generator.py       — generate_signals
  - execution/
    - __init__.py               — 発注層（スケルトン）
  - monitoring/                 — モニタリング関連（ファイル抜粋では詳細不明）
  - その他モジュール多数（設計ドキュメント参照: DataPlatform.md / StrategyModel.md）

---

## 開発者向けメモ

- 単体テストでは config の自動.envロードを無効化することで環境依存を切り分けられます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- DuckDB 接続は軽量でスレッドセーフな箇所もありますが、長時間共有接続の取り扱いはアプリ設計に応じて検討してください。
- news_collector._urlopen 等はテスト時にモックしやすいように設計されています。
- schema.init_schema() は冪等にテーブル・インデックスを作成するため、マイグレーションはDDLの差分管理を行ってください。

---

必要であれば、セットアップ用の requirements.txt やサンプルスクリプト（cron/jupyter での ETL 実行例）、.env.example を作成してお渡しします。どの部分を優先的に詳述しましょうか？