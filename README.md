# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、DuckDB ベースのスキーマ／監査を含む一連のコンポーネントを提供します。

## プロジェクト概要
KabuSys は以下の責務を持つモジュール群から構成されます。

- データ取得・保存（J-Quants API 経由の OHLCV / 財務 / カレンダー）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究（ファクター計算・特徴量探索）と特徴量エンジニアリング
- シグナル生成（正規化済みファクター + AI スコアの統合 → BUY/SELL シグナル）
- ニュース収集（RSS → raw_news / news_symbols）
- DuckDB スキーマ・監査テーブル・実行ログ等の管理

設計上のポイント：
- ルックアヘッドバイアス防止（target_date 時点のデータのみ使用）
- 冪等性重視（DB への保存は ON CONFLICT で上書きまたはスキップ）
- 外部依存最小化（研究モジュールは標準ライブラリ + DuckDB のみを想定）
- API 呼び出しに対するレート制御・リトライ・トークン自動リフレッシュ実装

## 主な機能一覧
- kabusys.data.jquants_client: J-Quants API クライアント（取得・保存関数、ページネーション、トークンリフレッシュ、レートリミット）
- kabusys.data.pipeline: 日次 ETL（市場カレンダー、株価、財務）の差分取得 / 保存 / 品質チェック
- kabusys.data.schema: DuckDB のスキーマ初期化（raw / processed / feature / execution レイヤ）
- kabusys.data.news_collector: RSS 収集 → raw_news 保存、銘柄抽出（SSRF / Gzip / XML 漏洩対策を実装）
- kabusys.research.factor_research: Momentum / Volatility / Value 等のファクター計算
- kabusys.strategy.feature_engineering: 研究で計算した生ファクターの正規化・ユニバースフィルタ・features テーブルへの保存
- kabusys.strategy.signal_generator: features + ai_scores を統合して final_score を計算、BUY/SELL 生成し signals テーブルへ保存
- kabusys.data.stats: Z スコア正規化等の統計ユーティリティ
- 設定管理: kabusys.config（.env 自動ロード、必須環境変数の取得、環境モード判定）

## 必要な環境変数（代表）
設定は .env / .env.local または OS 環境変数で提供します。プロジェクトルートに `.env.example` を置く想定です。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード（kabu API を使用する場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知実装を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意／デフォルトあり:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 動作モード（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると、パッケージ読み込み時の .env 自動読み込みを無効にできます（テストなどで利用）

設定取得例（Python）:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
is_live = settings.is_live
```

## セットアップ手順（例）
1. Python 環境を用意（推奨: 3.9+）
2. 必要パッケージをインストール（代表的な依存）
   - duckdb
   - defusedxml
   - （その他、プロジェクトの requirements.txt があればそれを使用）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# ローカル開発: パッケージを editable インストール
pip install -e .
```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成（.env.example を参考に）
   - あるいは CI/実行環境で環境変数をセット

4. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```
init_schema(":memory:") でインメモリ DB を使えます。

## 使い方（主要ユースケース）
以下は代表的な呼び出し例です。実運用ではログ・例外処理・スケジューラ（cron / Airflow 等）と組み合わせます。

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定して日付を固定可能
print(result.to_dict())
```

- 特徴量の構築（target_date の features を作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2025, 1, 15))
print("features upserted:", count)
```

- シグナル生成（features と ai_scores を参照して signals テーブルへ書き込む）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, date(2025, 1, 15))
print("signals written:", total)
```

- ニュース収集（RSS から raw_news を保存し、既知銘柄と紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄のセット（例: {"7203", "6758", ...}）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)
```

- J-Quants からデータを直接取得して保存するサンプル
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
saved = jq.save_daily_quotes(conn, records)
```

## ディレクトリ構成（主要ファイル）
src/kabusys パッケージの主要モジュール:

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（.env 自動読み込み、必須変数チェック）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS 収集、記事前処理、銘柄抽出、DB 保存
    - schema.py — DuckDB スキーマ定義・初期化
    - stats.py — zscore_normalize 等統計ユーティリティ
    - pipeline.py — ETL（run_daily_etl、run_prices_etl 等）
    - features.py — data.stats の再エクスポート
    - calendar_management.py — カレンダー更新・営業日判定
    - audit.py — 監査ログ用テーブル定義（signal_events / order_requests / executions 等）
    - (その他: quality 等のモジュールを想定)
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py — final_score 計算、BUY/SELL 生成
  - execution/ — 発注・約定・ポジション管理（パッケージ留保/拡張用）
  - monitoring/ — 監視・Slack 通知等（実装拡張想定）

補足:
- DuckDB スキーマは raw / processed / feature / execution 層に分かれており、冪等的な保存（ON CONFLICT）やインデックス定義を含みます。
- news_collector は SSRF 回避・受信サイズ制限・XML の安全パース（defusedxml）など安全対策を実装しています。
- jquants_client はレート制御（120 req/min の固定スロットリング）・リトライ（指数バックオフ）・ID トークン自動リフレッシュを備えます。

## 運用上の注意
- 秘密情報（API トークン等）は .env 管理または環境変数で安全に扱ってください。リポジトリにトークンをコミットしないでください。
- 本リポジトリには実際の発注ロジック（ブローカー送信・実口座連携）の詳細が含まれている場合は、paper_trading / live モードでの十分なテストとガード（リスク管理）を行ってください。
- DuckDB ファイルはファイルロック等を適切に扱う運用を推奨します（複数プロセスでの同時書き込みには注意）。

## 貢献・拡張
- execution 層（ブローカー API / 注文監視）や監視（Slack 通知、メトリクス収集）は拡張ポイントとして用意されています。
- 研究モジュールは外部実験結果（research/）を取り込みやすい設計です。feature_engineering は研究で算出した生ファクターの正規化・合成を行います。

---

その他、より詳細な設計指針はコード中のドキュメンテーション文字列（docstring）と DataPlatform.md / StrategyModel.md 等の設計ドキュメントを参照してください。README に書かれていない操作や運用フローがある場合は補足で案内します。必要であればサンプルの docker-compose、CI ワークフロー、requirements.txt のテンプレートなども作成できます。