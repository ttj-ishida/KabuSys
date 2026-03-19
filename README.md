# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ等のユーティリティ群を提供します。

## 概要

KabuSys は以下レイヤーを含むデータ・戦略プラットフォーム向けのコンポーネント群です。

- データ層（J-Quants クライアント、DuckDB スキーマ・保存処理、ETL パイプライン）
- リサーチ層（ファクター計算、特徴量探索、統計ユーティリティ）
- 戦略層（特徴量正規化・合成、シグナル生成）
- ニュース収集（RSS ベース、記事 -> 銘柄抽出）
- 監査 / 実行（スキーマ、トレーサビリティ設計）

設計上のポイント：
- DuckDB をデータストアとして想定（デフォルト DB: data/kabusys.duckdb）
- J-Quants API のレート制御・リトライ・トークンリフレッシュ対応
- ETL / DB 保存は冪等（ON CONFLICT / トランザクション）を意識
- ルックアヘッドバイアス対策（対象日時以前のデータのみ使用）
- 外部依存を最小化（標準ライブラリ + 必要なパッケージのみ）

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価・財務・市場カレンダー）
  - ページネーション／レート制御／リトライ／トークンリフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数
- ETL
  - 日次差分 ETL（run_daily_etl）
  - 市場カレンダー更新ジョブ（calendar_update_job）
  - 差分取得ロジック（バックフィル、営業日調整）
- リサーチ / 特徴量
  - モメンタム / ボラティリティ / バリュー計算（prices_daily / raw_financials のみ参照）
  - Z スコア正規化ユーティリティ
  - 前方リターン、IC、統計サマリー
- 戦略
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）：BUY/SELL 判定、Bear レジーム抑制、エグジット判定
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip 上限等）
  - raw_news / news_symbols への保存、タイトル/本文の前処理、銘柄抽出
- スキーマ / 監査
  - DuckDB 用の包括的スキーマ定義と初期化（init_schema）
  - 発注・約定・監査向けテーブル群

## 必要条件（例）

- Python 3.10+
- duckdb
- defusedxml

（プロジェクトの packaging / pyproject.toml に依存関係が定義されている想定です。実際のセットアップで必要なパッケージを確認してください。）

## 環境変数

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD に依存しないプロジェクトルート検出）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（ライブラリ内で _require() を通じて参照されるもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD      : kabuステーション API パスワード（execution 層で使用想定）
- SLACK_BOT_TOKEN        : Slack 通知用 BOT トークン（monitoring 等で使用）
- SLACK_CHANNEL_ID       : Slack チャンネルID

オプション:
- KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) - デフォルト: INFO
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視 DB 等（デフォルト: data/monitoring.db）

※ .env.example を作成して `.env` にコピーして利用する想定です。

## セットアップ手順（例）

1. リポジトリをクローン / ワークコピー
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - (ローカル開発パッケージとして) pip install -e .

4. 環境変数を用意
   - .env.example をプロジェクトルートに置き（存在しない場合は新規作成）、必須変数を設定
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_pw
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

## 初期化（DuckDB スキーマ作成）

簡単な例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照（デフォルト data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```

init_schema は必要なら親ディレクトリを作成し、全テーブル／インデックスを冪等的に作成します。

## ETL 実行（デイリーパイプライン）

日次 ETL を実行する簡単な例:

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- run_daily_etl は市場カレンダー、株価、財務データの差分取得 → 保存 → 品質チェックを行います。
- J-Quants API のトークンは settings.jquants_refresh_token（環境変数 JQUANTS_REFRESH_TOKEN）から自動的に取得されます。

## 特徴量構築（features）

research モジュールで計算した生ファクターを正規化・合成して `features` テーブルへ保存します。

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"built features for {count} codes")
```

- build_features は target_date 分を全削除してから挿入する日付単位の置換（冪等）。

## シグナル生成

`features` と `ai_scores` を統合して最終スコアを計算し、BUY / SELL を `signals` テーブルに書き込みます。

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"wrote {n} signals")
```

- weights を指定してコンポーネント比率を変更可能（辞書形式）。合計は自動で正規化される。
- Bear レジーム検知が True の場合、BUY シグナルは抑制されます。

## ニュース収集

RSS フィードからニュースを収集し raw_news / news_symbols へ保存します。

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema(settings.duckdb_path)
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

- URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip サイズ制限などを実装。
- 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を確保。

## カレンダー管理（夜間ジョブ）

```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"saved {saved} market calendar records")
```

- market_calendar テーブルを J-Quants から差分取得して更新します。

## 追加ユーティリティ

- data.stats.zscore_normalize: クロスセクション Z スコア正規化
- research.calc_forward_returns / calc_ic / factor_summary: リサーチ用統計・IC 計算
- data.jquants_client: fetch_* / save_* 系関数（ページネーション・保存ユーティリティ）
- data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL

## 注意点・設計メモ

- DB 保存は基本的にトランザクション + 冪等（ON CONFLICT）で行われますが、運用時はバックアップや適切なロギングを行ってください。
- J-Quants のレート制御（120 req/min）やリトライ戦略は実装済みですが、運用環境・トークンの取り扱いには注意してください。
- 環境変数は `.env` / `.env.local` より読み込まれます。自動ロードを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB は単一ファイルで軽量に運用できますが、運用時はディスク I/O やバックアップ戦略を検討してください。
- モジュールの多くは「発注 API（実際のブローカー呼び出し）」への依存を持たない設計になっています。execution 層は別途ブリッジ実装が必要です。

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・パッケージ構成（src ディレクトリを起点）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - news_collector.py             — RSS ニュース収集 / 保存
    - calendar_management.py        — カレンダー管理 / 夜間更新ジョブ
    - features.py                   — zscore_normalize 再エクスポート
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py        — 前方リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py        — 特徴量構築（build_features）
    - signal_generator.py           — シグナル生成（generate_signals）
  - execution/                      — 実行（発注）関連（雛形）
  - monitoring/                     — 監視 / Slack 通知等（雛形）

※ 上記はコードベースからの主要モジュール抜粋です。実際のプロジェクトには追加のユーティリティやドキュメントが含まれることがあります。

---

問題や追加の使用例（CI/CD、デプロイ、運用手順の追記など）が必要であれば、使い方の想定シナリオ（運用環境 or 研究用ローカル）を教えてください。用途に合わせて README を拡張します。