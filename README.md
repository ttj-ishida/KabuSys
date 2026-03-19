# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム基盤ライブラリです。J-Quants API から市場データを取得して DuckDB に蓄積し、研究用ファクターの計算、特徴量の正規化、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、発注／監査データ構造などを提供します。

主な目的は「再現性」「冪等性」「ルックアヘッドバイアス防止」を満たすデータパイプラインと戦略基盤を提供することです。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価・財務・カレンダー等）
  - 差分更新・バックフィル対応の ETL パイプライン（run_daily_etl 等）
  - DuckDB スキーマ定義・初期化（init_schema）
- データ品質とユーティリティ
  - 品質チェックフレームワーク（quality モジュール参照）
  - マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）
- 研究 / 特徴量
  - ファクター計算（momentum / volatility / value）
  - 特徴量正規化（Z スコア）と features テーブルへの書き込み（build_features）
  - ファクター探索・IC 計算・統計サマリー（research モジュール）
- シグナル生成
  - features と AI スコアを統合して final_score を算出し BUY/SELL シグナルを生成（generate_signals）
  - SELL（エグジット）判定ロジック（ストップロス等）
- ニュース収集
  - RSS からニュース取得、前処理、raw_news 保存、銘柄抽出と紐付け（news_collector）
  - SSRF / XML Bomb / 大容量レスポンス対策を備えた安全設計
- 発注・監査用スキーマ
  - signal_queue / orders / executions / audit テーブル等のスキーマ定義
- 設定管理
  - .env または環境変数から自動ロード（プロジェクトルート判定）および必須変数チェック

---

## セットアップ手順

1. リポジトリをクローン / パッケージを配置

   適宜クローンまたはパッケージ配布方法に従ってセットアップしてください。

2. Python 環境と依存パッケージをインストール

   依存ライブラリ（一例）:
   - duckdb
   - defusedxml

   pip を使う例:
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

   （プロジェクトが pyproject.toml / requirements.txt を持つ場合はそれに従ってください）

3. 環境変数の設定

   プロジェクトルートに `.env`（または `.env.local`）を作成することで自動読み込みされます。
   自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

   必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack ボットトークン（通知など）
   - SLACK_CHANNEL_ID: Slack チャンネル ID

   オプション:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`（機密情報は実際の値を設定）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化

   Python から schema.init_schema を呼んで DB を初期化します（デフォルトはファイル作成時に親ディレクトリ作成も行います）。

   例:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

---

## 使い方（代表的な操作例）

以下はライブラリを直接インポートして利用する例です。実運用スクリプト・ジョブから呼び出して利用します。

- DuckDB の初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = run_daily_etl(conn)
print(result.to_dict())
```

- 特徴量作成（build_features）
```python
from kabusys.strategy import build_features
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2026, 3, 1))
print(f"built features: {count}")
```

- シグナル生成（generate_signals）
```python
from kabusys.strategy import generate_signals
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
n = generate_signals(conn, date(2026, 3, 1))
print(f"generated signals: {n}")
```

- ニュース収集ジョブ（RSS 収集 → 保存 → 銘柄抽出）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market calendar saved: {saved}")
```

注意:
- これらはライブラリ関数の直接呼び出し例です。実運用ではスケジューラ（cron / Airflow / Prefect 等）から呼ぶ想定です。
- J-Quants API 呼び出しはレート制限・リトライ・トークン自動リフレッシュ等を組み込んでいます。ID トークンの管理は kabusys.data.jquants_client が行います。

---

## ディレクトリ構成

主要なコード位置（リポジトリの一例、src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 / 保存）
    - news_collector.py             — RSS ニュース収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義・初期化
    - stats.py                      — 統計ユーティリティ（zscore）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — 市場カレンダー管理・バッチ
    - audit.py                      — 監査ログ用スキーマ
    - features.py                   — features の公開ラッパ
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/volatility/value）
    - feature_exploration.py        — IC / 将来リターン / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        — 特徴量生成（build_features）
    - signal_generator.py           — シグナル生成（generate_signals）
  - execution/                      — 発注関連（将来的な実装の拡張ポイント）
  - monitoring/                     — 監視 / モニタリング関連（将来的な実装の拡張ポイント）

ドキュメントや設計メモ（外部参照）:
- DataPlatform.md
- StrategyModel.md
- Research/ 以下の研究ノート（実プロジェクトに同梱されていれば参照）

---

## 実運用上の注意点

- 環境（KABUSYS_ENV）に応じて挙動を分離してください（development / paper_trading / live）。
- 実際の発注処理は本ライブラリの execution 層と外部ブローカー API を組み合わせて実装する必要があります。本リポジトリのコードは発注 API に直接アクセスしない設計の箇所が多く、戦略は signals テーブルへ書き出すことで発注層と疎結合に保ちます。
- 機密情報は `.env` 等に保存する際に適切なアクセス制御を行ってください。
- DuckDB ファイルやログ等のバックアップ・ローテーションを検討してください。
- news_collector は外部 RSS に対する多数の安全対策（SSRF、XML attack、サイズ検査など）を実装していますが、運用環境のネットワーク制約やプロキシ設定に合わせた追加設定が必要になる場合があります。

---

## 開発・テスト向け

- config モジュールはプロジェクトルート（.git または pyproject.toml を起点）から `.env` を自動読み込みします。テストで自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 単体テストを書く際は jquants_client の HTTP 呼び出しや news_collector._urlopen のような I/O をモックして外部アクセスを遮断してください。
- DuckDB はインメモリ（":memory:"）での初期化も可能です（init_schema(":memory:")）。

---

この README はライブラリの概要と代表的な使い方を示したものです。詳細な仕様（StrategyModel.md、DataPlatform.md、各モジュールの docstring）はソース内のドキュメントを参照してください。質問や追加の使い方サンプルが必要であればお知らせください。