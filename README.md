# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。  
データ取得（J-Quants）、ETL（DuckDB）、特徴量作成、戦略シグナル生成、ニュース収集、カレンダー管理、監査ログなどの基盤機能を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数 / 設定
- 注意点・設計方針
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けの共通ライブラリ群です。  
主な目的は次の通りです。

- J-Quants API からの株価・財務・カレンダーの取得
- DuckDB を用いたローカルデータベース管理（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究用ファクター計算・特徴量正規化
- 戦略のシグナル生成（BUY/SELL 判定・エグジット判定）
- RSS ベースのニュース収集と記事→銘柄紐付け
- 監査ログ / 発注追跡（トレーサビリティ）

設計上、研究（research）層と実行（execution）層を分離し、ルックアヘッドバイアスを避けるために「target_date 時点のデータのみを使用する」などの配慮がされています。

---

## 機能一覧

- データ取得・保存
  - J-Quants から日次株価、財務データ、マーケットカレンダーを取得（ページネーション対応・レート制御・リトライ）
  - raw_prices / raw_financials / market_calendar 等の Raw テーブルに冪等的に保存（ON CONFLICT）
- データベーススキーマの初期化
  - DuckDB に必要なテーブル・インデックスを作成する `init_schema`
- ETL
  - 差分更新（最終取得日からの差分取得）とバックフィル
  - 日次 ETL の統合エントリポイント `run_daily_etl`
- 研究用ファクター計算
  - Momentum / Volatility / Value などのファクターを計算（prices_daily, raw_financials 参照）
  - ファクター探索ツール（将来リターン計算・IC 計算・統計サマリ）
- 特徴量エンジニアリング
  - ファクターの正規化（Zスコア）・ユニバースフィルタ適用・features テーブルへの UPSERT（冪等）
- シグナル生成
  - features と AI スコアを統合して final_score を計算し BUY/SELL を生成、signals テーブルへ書き込み
  - Bear レジーム抑制、エグジット（ストップロス等）
- ニュース収集
  - RSS フィードから記事を取得・前処理・raw_news へ保存
  - 記事 URL 正規化・SSRF 対策・gzip サイズ制限などのセキュリティ対策
  - 記事と銘柄の紐付け（news_symbols）
- カレンダー管理
  - JPX カレンダーの差分更新、営業日判定・前後営業日取得ユーティリティ
- 監査ログ（audit）
  - signal_events / order_requests / executions など、発注から約定までのトレース性を担保するテーブル設計

---

## セットアップ手順

前提
- Python 3.9+（コードは型ヒント等でモダンな Python を想定）
- DuckDB を利用するため duckdb パッケージが必要
- defusedxml（RSS パースのセキュリティ強化）など

推奨手順（簡易）

1. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（最小）
   ```
   pip install duckdb defusedxml
   ```
   実際のプロジェクトでは追加依存がある可能性があります（ロギング、HTTP クライアント等）。requirements.txt があればそれを使用してください。

3. ソースをインストール（開発モード）
   プロジェクトルートに setup.cfg / pyproject.toml がある想定で:
   ```
   pip install -e .
   ```
   なければ直接 PYTHONPATH に src を追加して利用してください。

4. 環境変数の設定
   プロジェクトルートに `.env` を作成するか、環境変数を設定します（下記の「環境変数」参照）。

5. DuckDB スキーマ初期化
   Python REPL やスクリプトで以下を実行して DB を初期化します（デフォルトは data/kabusys.duckdb）。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 簡単な使い方（例）

以下は代表的なワークフローのサンプルです。

- DB 初期化（先述）
- 日次 ETL を実行してデータを取得・保存
- 特徴量を構築
- シグナルを生成

サンプルコード:
```python
from datetime import date
import duckdb

from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

# 初期化（1回）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（今日）
etl_result = run_daily_etl(conn, target_date=date.today())
print(etl_result.to_dict())

# 特徴量作成（例: 今日分）
n_features = build_features(conn, date.today())
print("features:", n_features)

# シグナル生成（閾値や重みは変更可能）
n_signals = generate_signals(conn, date.today(), threshold=0.6)
print("signals:", n_signals)

conn.close()
```

ニュース収集の実行例:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効なコードセット（例: 上場銘柄コードリスト）
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

カレンダー更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

---

## 環境変数 / 設定

自動で .env をプロジェクトルート（.git または pyproject.toml を基準）から読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（Settings.require により未設定時はエラー）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション API のパスワード（発注連携がある場合）
- SLACK_BOT_TOKEN        : Slack 通知用トークン
- SLACK_CHANNEL_ID       : Slack 通知先チャンネルID

その他の設定（デフォルトあり）
- KABUSYS_ENV : 実行環境。`development` / `paper_trading` / `live` のいずれか（デフォルト: development）
- LOG_LEVEL   : ログレベル。`DEBUG|INFO|WARNING|ERROR|CRITICAL`（デフォルト: INFO）
- KABUS_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH  : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH  : 監視用 SQLite のパス（デフォルト: data/monitoring.db）

サンプル .env（抜粋）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 注意点・設計方針（抜粋）

- ルックアヘッドバイアス回避
  - ファクター計算やシグナル生成は target_date 時点の情報のみを使用する設計です。
- 冪等性
  - raw データの保存は ON CONFLICT DO UPDATE 等で冪等を確保しています。
- レート制御 / リトライ
  - J-Quants API クライアントはレートリミット（120 req/min）を守り、リトライとトークン自動刷新を実装しています。
- セキュリティ
  - RSS パーサーは defusedxml を使用し、SSRF / gzip bomb / 外部リダイレクトの検査を行います。
- DB スキーマは DuckDB を前提に作られており、初期化関数で必要なテーブル・インデックスを作成します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py         # J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py        # RSS → raw_news / news_symbols
  - pipeline.py              # ETL パイプライン（run_daily_etl 等）
  - schema.py                # DuckDB スキーマ定義 / init_schema
  - stats.py                 # 統計ユーティリティ（zscore_normalize）
  - features.py              # data.stats の再エクスポート
  - calendar_management.py   # 市場カレンダー管理
  - audit.py                 # 監査ログ用 DDL（signal_events 等）
  - audit... (一部ファイルは file で分割済)
- research/
  - __init__.py
  - factor_research.py       # Momentum/Volatility/Value の計算
  - feature_exploration.py   # 将来リターン・IC・統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py   # features テーブル構築（正規化・ユニバースフィルタ）
  - signal_generator.py      # final_score 計算・signals 書込
- execution/
  - __init__.py              # 発注連携のエントリ（実装は別途）
- monitoring/                 # monitoring は __all__ に含まれています（将来実装想定）

（上記は本 README が参照するコードベースの抜粋です。実際のリポジトリには追加ファイルやテスト等が存在する可能性があります。）

---

## 貢献 / 開発メモ

- 開発環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env 自動ロードを無効にできます（テスト等で有用）。
- DuckDB のスキーマ初期化は破壊的操作ではなく冪等に設計されていますが、データのバックアップを推奨します。
- 大きな変更（特にスキーマ・ETL ロジック）は品質チェック（quality module）や既存データへの影響を十分に検討してください。

---

問題・改善要望や README の追記希望があれば、どの部分を詳しく記載するか教えてください。