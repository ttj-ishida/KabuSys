# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された、データ取得・加工・特徴量生成・シグナル生成を行う Python ライブラリです。J-Quants API や RSS ニュースを用いたデータパイプラインと、DuckDB を用いたローカルDBスキーマを中心に、研究（research）→特徴量（feature）→戦略（strategy）→発注（execution）の各レイヤーを備えています。

主な設計方針は次の通りです。
- ルックアヘッドバイアスを避けるため「対象日時点で利用可能だったデータのみ」を使用
- DuckDB を用いた冪等性のある保存（ON CONFLICT / トランザクション）
- API 呼び出しのレート制御・リトライ・トークン自動リフレッシュ
- ニュース収集における SSRF / XML bomb 等のセキュリティ対策

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API からの日次株価（OHLCV）、財務データ、マーケットカレンダーの取得（差分更新・バックフィル対応）
  - RSS フィードからのニュース収集（正規化・トラッキングパラメータ除去・記事ID生成）
- データ永続化
  - DuckDB 用スキーマ定義と初期化（init_schema）
  - raw / processed / feature / execution 層のテーブル群
- 研究用ユーティリティ
  - モメンタム／ボラティリティ／バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC 計算、ファクター統計サマリ（research.feature_exploration）
- 特徴量（feature）生成
  - 生ファクターの正規化（Z スコア）やユニバースフィルタ適用、features テーブルへの UPSERT（strategy.feature_engineering）
- シグナル生成
  - features と AI スコアを統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ保存（strategy.signal_generator）
  - Bear レジーム判定、エグジット（ストップロス等）の判定ロジック
- ニュース処理
  - RSS フェッチ、前処理、raw_news 保存、銘柄コード抽出と紐付け（data.news_collector）
- カレンダー管理（取引日判定、next/prev trading day 等）（data.calendar_management）
- 監査ログ（signal/order/execution のトレーサビリティ）スキーマ（data.audit）
- 汎用統計ユーティリティ（zscore_normalize）（data.stats）

---

## セットアップ手順

前提
- Python 3.10 以上（コード内で `X | None` の構文を使用）
- DuckDB を利用するため、ネイティブバイナリが動作する環境

推奨依存パッケージ（最低限）
- duckdb
- defusedxml

例：仮想環境を作成してインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# （任意）このリポジトリを編集可能インストールする場合
pip install -e .
```

環境変数
- 本プロジェクトは .env / .env.local / OS 環境変数を自動ロードします（プロジェクトルートに .git または pyproject.toml がある場合）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

必須環境変数（Settings により参照）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API パスワード（execution 層利用時）
- SLACK_BOT_TOKEN        : Slack 通知用トークン（必要に応じて）
- SLACK_CHANNEL_ID       : Slack チャンネルID

任意（デフォルトあり）
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH       : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH       : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV       : 実行環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL         : ログレベル（DEBUG/INFO/...）。デフォルト: INFO

初期 DB スキーマ作成
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成してテーブルを作る
conn.close()
```

---

## 使い方（簡単な例）

以下は最小限の操作フロー例です。

1) DuckDB 初期化（上記参照）

2) 日次 ETL 実行（市場カレンダー・株価・財務の差分取得と保存）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# 初回は init_schema を呼ぶ（既に作成済みならスキップ）
conn = init_schema(settings.duckdb_path)

# 当日 ETL を実行
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

conn.close()
```

3) 特徴量を作る（strategy.build_features）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features

conn = get_connection(settings.duckdb_path)
count = build_features(conn, target_date=date(2025, 3, 1))
print(f"features upserted: {count}")
conn.close()
```

4) シグナル生成（strategy.generate_signals）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals

conn = get_connection(settings.duckdb_path)
n_signals = generate_signals(conn, target_date=date(2025, 3, 1))
print(f"signals written: {n_signals}")
conn.close()
```

5) ニュース収集（RSS）
```python
from kabusys.config import settings
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection(settings.duckdb_path)
# known_codes はサイト内で有効な銘柄コード集合（例: all listed codes）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(results)
conn.close()
```

注意
- 上記はライブラリ呼び出し例です。実際の運用ではジョブスケジューラ（cron 等）やバッチランナーでスクリプトを実行します。
- execution 層（注文送信・約定処理）には kabu ステーションやブローカーの API 実装が必要です（このコードベースでは execution ディレクトリが存在しますが、外部連携実装を行ってください）。

---

## 主要モジュール（抜粋）

- kabusys.config
  - 環境変数の自動ロード、設定取得（settings オブジェクト）
- kabusys.data
  - schema.py        : DuckDB スキーマ定義・初期化（init_schema）
  - jquants_client.py: J-Quants API クライアント（取得 / 保存ユーティリティ）
  - pipeline.py      : 日次 ETL / 個別 ETL ジョブ
  - news_collector.py: RSS 収集・保存・銘柄抽出
  - calendar_management.py : 市場カレンダー操作（is_trading_day 等）
  - stats.py         : zscore_normalize 等の統計ユーティリティ
  - features.py      : 公開インターフェース re-export
  - audit.py         : 監査ログ用スキーマ DDL
- kabusys.research
  - factor_research.py    : mom/volatility/value のファクター計算
  - feature_exploration.py: 将来リターン・IC・統計サマリ
- kabusys.strategy
  - feature_engineering.py: features の正規化・アップサート処理
  - signal_generator.py   : final_score 計算と signals への書き込み
- kabusys.execution
  - （発注実装を追加する想定のプレースホルダ）
- kabusys.monitoring
  - （監視用実装を追加可能）

---

## ディレクトリ構成

以下はリポジトリ内の主要なファイル/ディレクトリの抜粋です（src 配下）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - schema.py
      - jquants_client.py
      - pipeline.py
      - news_collector.py
      - calendar_management.py
      - features.py
      - stats.py
      - audit.py
      - pipeline.py
      - (その他 data 関連モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/
      - (未実装/追加可能)
- pyproject.toml / setup.cfg / .gitignore など（プロジェクトルート）

---

## 開発・拡張のヒント

- テスト
  - 自動 env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。テスト用に設定を注入して利用してください。
- モック
  - ネットワーク呼び出し（jquants_client._request や news_collector._urlopen）はユニットテストで差し替え可能な設計です。
- パフォーマンス
  - DuckDB の SQL を活用して集約やウィンドウ関数で高速に計算します。大規模データ時は接続設定やメモリ設定を調整してください。
- セキュリティ
  - news_collector では SSRF 対策、XML パース時の defusedxml 使用、受信サイズ制限などを実装しています。外部 URL を扱う場合はこの設計方針を踏襲してください。

---

もし README に追加したいサンプルスクリプト（cron 用エントリ、Dockerfile、CI 設定など）があれば教えてください。必要に応じて具体的な実行スクリプトや運用手順を追記します。