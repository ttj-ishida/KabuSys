# KabuSys

日本株向けの自動売買/データ基盤ライブラリ（KabuSys）。  
J-Quants API からのデータ取得、DuckDB ベースのスキーマ、ファクター計算・特徴量合成、シグナル生成、ニュース収集などの機能を提供します。

---

## 概要

KabuSys は以下の役割を持つモジュール群から構成されるパッケージです。

- データ収集（J-Quants API）・保存（DuckDB）
- データ品質チェック・ETL パイプライン
- ファクター計算（Momentum / Volatility / Value 等）
- 特徴量の正規化・合成（features テーブル）
- シグナル生成（final_score に基づく BUY / SELL 判定）
- ニュース収集（RSS）と銘柄紐付け
- マーケットカレンダー管理、監査ログスキーマ

設計上のポイント:
- ルックアヘッドバイアス回避（target_date 時点のみを使用）
- 冪等性（DB への INSERT は ON CONFLICT を利用）
- ネットワークリトライ / レート制限 / トークン自動リフレッシュ対応
- 外部依存を最小化（標準ライブラリ中心、duckdb, defusedxml 等を利用）

---

## 機能一覧

- data.jquants_client
  - J-Quants API との通信（ページネーション / レート制限 / リトライ / id_token 自動更新）
  - 株価（daily_quotes）・財務（statements）・マーケットカレンダー取得
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- data.schema
  - DuckDB のスキーマ定義と初期化（init_schema）
  - 各レイヤー（raw / processed / feature / execution）のテーブル定義
- data.pipeline
  - 差分取得・保存・品質チェックを行う ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- data.news_collector
  - RSS 収集（fetch_rss）・前処理・raw_news 保存・銘柄抽出と紐付け（run_news_collection）
  - SSRF 対策、レスポンスサイズ上限、XML パース安全化等の防御策を実装
- data.calendar_management
  - 営業日判定・次営業日/前営業日・カレンダー更新ジョブ
- data.stats
  - zscore_normalize（クロスセクションの Z スコア正規化）
- research.factor_research / feature_exploration
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- strategy.feature_engineering
  - 生ファクターを統合して features テーブルへ UPSERT（Z スコア正規化・クリップ含む）
- strategy.signal_generator
  - features と ai_scores を統合して final_score 計算、BUY/SELL シグナル生成、signals テーブルへの書き込み
- audit / execution / monitoring（監査・発注・監視用のスキーマ・ユーティリティ）

---

## セットアップ手順

前提
- Python 3.10+（PEP 604 の `X | Y` 型注釈を使用しているため）
- duckdb（Python パッケージ）
- defusedxml（RSS の安全パース用）
- （任意）仮想環境の利用を推奨

1. リポジトリをチェックアウト
   - 例: git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - 開発時は pip install -e . でローカルパッケージとしてインストールできます（setup.py / pyproject.toml がある前提）。

4. 環境変数 (.env) を用意
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動ロードされます（読み込み順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

推奨の最小 .env（例）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token の取得に使用。
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード。
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン（使用する場合）。
- SLACK_CHANNEL_ID (必須)
  - Slack チャンネル ID（使用する場合）。
- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）。
- SQLITE_PATH (任意)
  - 監視等で用いる sqlite のパス（デフォルト: data/monitoring.db）。
- KABUSYS_ENV (任意)
  - 動作モード: development | paper_trading | live（デフォルト: development）。
- LOG_LEVEL (任意)
  - ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない。

---

## 使い方（基本例）

以下はパッケージの主な関数の呼び出し例です。実運用ではログ設定やエラーハンドリングを適切に追加してください。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

2) 日次 ETL を実行（J-Quants から差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量（features）を構築
```python
from kabusys.strategy import build_features
from datetime import date

count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナルを生成
```python
from kabusys.strategy import generate_signals
from datetime import date

num_signals = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals generated: {num_signals}")
```

5) ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセットを準備
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

6) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

注意点:
- run_daily_etl は内部で market_calendar を先に更新し、営業日調整を行ってから prices/financials を処理します。
- J-Quants API の呼出しはモジュール内でレート制限（120 req/min）やリトライを制御します。
- features / signals の書き込みは日付単位で削除→挿入するため冪等です。

---

## 主要ディレクトリ構成

(抜粋) ソースは src/kabusys 以下に格納されています。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得 + 保存）
    - news_collector.py             — RSS 収集・前処理・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義・初期化
    - pipeline.py                   — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py        — マーケットカレンダー管理
    - stats.py                      — zscore_normalize 等の統計ユーティリティ
    - features.py                   — zscore_normalize の再エクスポート
    - audit.py                      — 監査ログスキーマ（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py            — モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py        — 将来リターン / IC / 要約統計
  - strategy/
    - __init__.py
    - feature_engineering.py        — features 作成・正規化処理
    - signal_generator.py           — final_score 計算・BUY/SELL シグナル生成
  - execution/
    - __init__.py                   — 発注・約定・ポジション管理（将来の実装・連携用）
  - monitoring/                      — 監視・メトリクス関連（プレースホルダ）

（実際のリポジトリでは上記以外の補助モジュールやテストが存在する可能性があります）

---

## 実装上の注意 / 仕様メモ

- DuckDB を使用しているため、データはファイルベースで永続化できます（デフォルト path: data/kabusys.duckdb）。
- jquants_client はページネーション・トークンキャッシュを実装。HTTP 401 受信時はリフレッシュトークンで自動再取得します。
- news_collector は SSRF 対策・XML パースの安全化・レスポンスサイズ制限など多数の防御策を実装しています。
- strategy の設計はルックアヘッドバイアスを避けるため、target_date 時点で利用可能なデータのみを使用します。
- signals / features への書き込みは日付単位で削除→挿入を行い冪等を保証します（トランザクション使用）。

---

## 開発・貢献

- 新機能やバグ修正はまずローカルでテストし、可能であれば既存の規約に合わせたユニットテストを追加してください。
- 環境変数や外部 API への依存がある部分は、テスト時に該当モジュールをモックして実行することを推奨します（例: jquants_client の _urlopen / _request の差し替え）。

---

不明点や README に追加してほしいサンプル（例えば具体的な ETL スケジュール例や docker-compose 例など）があれば教えてください。必要に応じて追記します。