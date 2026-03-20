# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
DuckDB をデータ層に用い、J-Quants API や RSS ニュースを取り込み、特徴量エンジニアリング、シグナル生成、ETL、カレンダー管理、監査ログなど自動売買に必要な基盤処理を提供します。

---

## プロジェクト概要

KabuSys は以下を主眼に設計された Python モジュール群です。

- データ取得（J-Quants API）と DuckDB への冪等保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- Research 層のファクター計算・探索（モメンタム、ボラティリティ、バリュー等）
- 戦略層の特徴量生成とシグナル生成（BUY / SELL 判定）
- ニュース収集（RSS）と銘柄紐付け
- マーケットカレンダー管理（JPX）
- 発注・約定・ポジション管理および監査ログ（スキーマ定義）

設計上のポイント：
- 冪等（idempotent）な DB 操作
- ルックアヘッドバイアス対策（取得時刻の記録 / target_date ベースの計算）
- 外部依存を最低限に（標準ライブラリ中心、DuckDB を利用）
- テストしやすい設計（依存注入、明確な API）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・トークン自動更新付き）
  - schema: DuckDB スキーマ定義・初期化
  - pipeline: 日次 ETL（価格・財務・カレンダー）と差分取得ロジック
  - news_collector: RSS 収集／正規化／DB 保存・銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: 各種ファクター（momentum, volatility, value）の計算
  - feature_exploration: 将来リターン、IC、ファクター要約
- strategy/
  - feature_engineering: raw ファクターを正規化して features テーブルへ保存
  - signal_generator: features／ai_scores を統合して BUY/SELL シグナルを生成
- execution/（発注層用プレースホルダ）
- monitoring/（監視・Slack 通知等の実装想定）
- config.py: 環境変数管理（.env 自動読み込み・検証）
- audit.py: 監査ログ用スキーマ（トレーサビリティ）

---

## 必要な環境変数

下記は必須（実行する機能に応じて必要なものが異なります）。

- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD : kabuステーション API パスワード（execution 層）
- SLACK_BOT_TOKEN : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID : 通知先のチャンネル ID

任意・デフォルトあり：

- KABUSYS_ENV : 実行環境（development / paper_trading / live）。デフォルト `development`
- LOG_LEVEL : ログレベル（DEBUG / INFO / ...）。デフォルト `INFO`
- DUCKDB_PATH : DuckDB ファイルパス。デフォルト `data/kabusys.duckdb`
- SQLITE_PATH : 監視用 SQLite パス。デフォルト `data/monitoring.db`
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合 `1`

.env の読み込み優先順位: OS 環境変数 > .env.local > .env

簡易 .env.example（README 用）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. Python の準備
   - 推奨: Python 3.9+（コードは型アノテーション等を使用）
   - 仮想環境を作成して有効化を推奨

2. 依存パッケージのインストール
   - 必要な主なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # Windows: .venv\Scripts\activate
     pip install duckdb defusedxml
     ```
   - （プロジェクトに pyproject.toml / requirements.txt がある場合はそちらを参照）

3. 環境変数の設定
   - 上の .env.example を参考に `.env`（または `.env.local`）をプロジェクトルートに作成
   - もしくは OS 環境変数として設定

4. データベーススキーマ初期化
   - Python から DuckDB 接続を作成してスキーマを初期化します。例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - ":memory:" を渡すとインメモリ DB を使えます（テスト向け）

---

## 使い方（基本例）

以下は代表的なワークフローの例です。実運用ではジョブスケジューラ（cron 等）で定期実行します。

1) スキーマ初期化（1回）
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（価格・財務・カレンダーの差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量構築（strategy.feature_engineering）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
num_signals = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals generated: {num_signals}")
```

5) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー更新ジョブ（夜間）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## ディレクトリ構成（簡易）

（src 以下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                : 環境変数 / .env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py      : J-Quants API クライアント（取得・保存ユーティリティ）
    - schema.py              : DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            : ETL パイプライン（run_daily_etl 等）
    - news_collector.py      : RSS 収集 / 正規化 / 保存 / 銘柄抽出
    - calendar_management.py : JPX カレンダー管理 / 営業日判定
    - stats.py               : zscore_normalize 等の統計ユーティリティ
    - features.py            : features の公開インターフェース（再エクスポート）
    - audit.py               : 監査ログ用スキーマ DDL（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py     : モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py : 将来リターン / IC / サマリー統計
  - strategy/
    - __init__.py
    - feature_engineering.py : raw factor を正規化して features へ保存
    - signal_generator.py    : final_score 計算と BUY/SELL 判定
  - execution/               : 発注層（プレースホルダ）
  - monitoring/              : 監視・通知（プレースホルダ）

※ 実装ファイルは README に要約したとおり多数のサブ機能を持ちます。詳細は各モジュールの docstring を参照してください。

---

## 注意事項・運用上のヒント

- 環境変数は機密情報を含むため管理に注意してください（Vault や CI シークレット等を使用）。
- J-Quants のレート制限（120 req/min）を守る設計になっていますが、運用時は API 実行頻度に注意してください。
- DuckDB ファイルのバックアップ（スナップショット）やサイズ管理を実施してください。
- 本ライブラリは発注（execution）周りに参照用スキーマ／ユーティリティを提供しますが、実際のブローカー API 実装／接続処理は別途実装が必要です。
- 本リポジトリのコードは型注釈・log 出力等を備えています。実運用前にユニットテスト・統合テスト・ペンディングの監査を行ってください。

---

## 開発・貢献

- 変更を加える場合はテスト／ロギングを充実させてから PR してください。
- 大きな設計変更（スキーマ・主要アルゴリズム）は事前に issue で議論してください。

---

この README はコード冒頭の docstring と実装から要点をまとめたものです。各モジュールのドキュメント（docstring）を参照すると詳細な仕様・注意点が記載されています。必要であれば具体的なユースケースやデプロイ手順（systemd / コンテナ化 / CI ジョブ）についても追記します。