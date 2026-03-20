# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ・監査ロギング等の機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

本ライブラリは以下のレイヤーを備えた設計になっています。

- Data layer：J-Quants API から株価・財務・マーケットカレンダー等を取得し DuckDB に保存
- Research layer：ファクター計算・特徴量解析（momentum / volatility / value 等）
- Feature layer：特徴量の正規化・合成（features テーブル）
- Strategy layer：正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- Execution / Monitoring（プレースホルダ）：発注・監視に関する仕組み

設計上の特徴として、ルックアヘッドバイアスを避けるために各処理は target_date 時点のデータのみを参照し、DuckDB への保存は冪等（ON CONFLICT / トランザクション）を意識しています。

---

## 主な機能一覧

- 環境変数／.env 自動読み込み（.env, .env.local、無効化可）
- J-Quants API クライアント
  - 株価日足・財務データ・マーケットカレンダーのページネーション取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン
  - 差分取得（最終取得日に基づく差分）・backfill サポート
  - 日次 ETL ジョブ（calendar / prices / financials + 品質チェック）
- DuckDB スキーマ定義と初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブルを作成
- 研究用ファクター計算
  - momentum（1m/3m/6m、MA200乖離）
  - volatility（ATR20、出来高比率、20日平均売買代金）
  - value（PER, ROE）
  - 将来リターン・IC（Spearman）・統計サマリー
- 特徴量エンジニアリング
  - ユニバースフィルタ（最低株価・最低売買代金）
  - Z スコア正規化・クリッピング・features テーブルへの UPSERT
- シグナル生成
  - momentum / value / volatility / liquidity / news を統合して final_score を算出
  - Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの書き込み
  - 保有ポジションのエグジット（ストップロス等）
- ニュース収集（RSS）
  - RSS フィードの取得・前処理・記事ID 正規化（URL 正規化＋SHA256）
  - SSRF 対策・レスポンスサイズ制限・XML 危険対策（defusedxml）
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理
  - 営業日判定、next/prev_trading_day、期間内営業日取得
- 監査ログ（audit）テーブル群（signal_events / order_requests / executions 等）

---

## セットアップ手順

前提
- Python 3.9+（typing の union 表記などに依存）
- DuckDB を使用するためネイティブパッケージの制約に注意

例）仮想環境作成と依存ライブラリのインストール:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要な依存パッケージ（例）
pip install duckdb defusedxml
# パッケージをローカル開発モードでインストールする場合
pip install -e .
```

依存パッケージはプロジェクトの要件に応じて requirements.txt を用意してください。上のコードベースでは少なくとも次が必要です：
- duckdb
- defusedxml

環境変数
- 必須:
  - JQUANTS_REFRESH_TOKEN：J-Quants 用リフレッシュトークン
  - KABU_API_PASSWORD：kabu ステーション API パスワード（execution 層で使用）
  - SLACK_BOT_TOKEN：Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID：通知先 Slack チャンネル ID
- 任意／デフォルトあり:
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）にある `.env` / `.env.local` が自動読み込みされます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途）。

例：`.env` の一例（実運用では秘匿に注意）

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=./data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（基本的な例）

以下は Python スクリプトやインタラクティブで使う簡単な例です。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

":memory:" を渡すとインメモリ DB になります。

2) 日次 ETL の実行（J-Quants トークンは settings 経由で取得）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量の構築（features テーブルへの登録）

```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成

```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
signals_count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {signals_count}")
```

5) ニュース収集ジョブ（既知銘柄セットを渡して紐付け）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（例: {'7203','6758',...}）
res = run_news_collection(conn, known_codes={'7203','6758'})
print(res)
```

6) JPX カレンダー更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点
- 各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。
- ETL や保存処理は冪等性を考慮しているため、再実行しても重複でデータが増えないように設計されています。
- 実運用ではログ設定（LOG_LEVEL）や例外の監視、監査ログの取り扱いを整備してください。

---

## ディレクトリ構成（抜粋）

以下はコードベースの主要ファイルとモジュールの構成（src/kabusys 配下）です。実際のリポジトリに応じて追加ファイルがある場合があります。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定管理（.env 自動読み込み等）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得＋保存ユーティリティ）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - schema.py               — DuckDB スキーマ定義・初期化（init_schema）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - news_collector.py       — RSS 収集・記事保存・銘柄抽出
    - calendar_management.py  — カレンダー管理・判定ユーティリティ
    - features.py             — data 側の特徴量公開インターフェース
    - audit.py                — 監査ログスキーマ定義
    - pipeline.py             — （ETL 関連、重複しているが上記）
  - research/
    - __init__.py
    - factor_research.py      — momentum/volatility/value の計算
    - feature_exploration.py  — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル構築（正規化・フィルタ）
    - signal_generator.py     — final_score 計算・BUY/SELL 生成
  - execution/                — 発注関連のエントリ（現状プレースホルダ）
  - monitoring/               — 監視関連（プレースホルダ）

---

## 開発・テストのヒント

- .env の自動ロードはプロジェクトルートを .git または pyproject.toml から探索します。CI やユニットテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを抑止するのが安全です。
- DuckDB の `:memory:` を使うとインメモリ DB で高速に単体テストできます。
- ネットワーク呼び出し（jquants_client.fetch_* / news_collector.fetch_rss）部分はモック可能なように設計されています（例: _urlopen を差し替え）。
- ニュース収集では defusedxml を用いて XML 関連の脆弱性に配慮しています。

---

## 注意事項

- 本リポジトリは実運用向けのインターフェースの骨組み・アルゴリズムを含みますが、実際に資金を扱う前に十分なテスト・監査を行ってください。
- API トークンやパスワード等の機密情報は `.env` や運用シークレットマネージャーで安全に管理してください。
- 本 README はソース内の docstring・コメントを基に作成しています。詳細な仕様（StrategyModel.md, DataPlatform.md, DataSchema.md 等）が別途存在する想定です。必要に応じて参照してください。

---

もし README に追加したい内容（例: CLI の使い方、CI の設定、例データの取得方法、schema のカラム一覧の自動生成など）があれば教えてください。README をその要件に合わせて拡張します。