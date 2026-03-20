# KabuSys — 日本株自動売買システム

注意: この README は与えられたコードベース（src/kabusys 以下）をもとに作成したドキュメントです。実行前に環境変数や依存ライブラリを正しく揃えてください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤のコアライブラリです。  
主な目的は以下の通りです。

- J-Quants 等の外部データソースから市場データ・財務データ・カレンダーを取得して DuckDB に保存（ETL）
- 取得データを加工してファクター・特徴量を生成（research / strategy 層）
- 特徴量と AI スコアを統合して売買シグナルを生成（strategy 層）
- ニュース収集・前処理と銘柄紐付け（news collector）
- 発注・約定・ポジションのためのスキーマ / 監査ログ（execution / audit 用スキーマ）
- マーケットカレンダー管理、品質チェック、監査トレーサビリティ

設計方針としては「冪等性」「ルックアヘッドバイアス回避」「外部 API のフェールセーフ」「DB トランザクションによる原子性確保」などが反映されています。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（ページネーション、レートリミット、リトライ、トークン自動更新）
  - 株価（OHLCV）、財務データ、マーケットカレンダーの取得と DuckDB への冪等保存
- ETL / パイプライン
  - 差分更新（最終取得日からの再取得）、バックフィル、品質チェック統合
  - 日次 ETL エントリポイント（run_daily_etl）
- データスキーマ
  - raw / processed / feature / execution 層のテーブル定義（DuckDB 用 DDL）
  - スキーマ初期化（init_schema）
- 特徴量・リサーチ
  - Momentum / Volatility / Value のファクター計算
  - クロスセクション Z スコア正規化
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 戦略（シグナル生成）
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム判定、BUY/SELL シグナル生成、エグジット（ストップロス等）
- ニュース収集
  - RSS 取得、前処理（URL 除去・正規化）、記事ID生成（URL 正規化＋SHA-256）
  - raw_news 保存、銘柄コード抽出・紐付け（news_symbols）
  - SSRF 対策・XML デフューズ対策・受信サイズ制限
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等のユーティリティ
  - 夜間バッチ更新ジョブ（calendar_update_job）
- 監査 / トレーサビリティ
  - signal_events / order_requests / executions 等、監査用スキーマ

---

## 要求環境・依存ライブラリ

- Python: 3.10 以上（型注釈に `X | None` を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml

インストール例（仮想環境内で）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージが pyproject にある場合: pip install -e .
```

（プロジェクトで追加ライブラリが必要な場合は pyproject / requirements を参照してください）

---

## 環境変数（設定）

config.py により環境変数から設定を読み込みます。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須の環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用の Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — execution 環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）、デフォルト INFO

.env 例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

config.Settings プロパティからこれらにアクセスできます（例: settings.jquants_refresh_token）。

---

## セットアップ手順

1. リポジトリをチェックアウト
2. Python 仮想環境を作成し有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定（`.env` をプロジェクトルートに作成）
5. DuckDB スキーマ初期化

スキーマ初期化例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# init_schema はテーブル作成を実行し、DuckDB 接続オブジェクトを返します
```

注意:
- ファイルパスの親ディレクトリがなければ自動生成されます。
- ":memory:" を渡すとインメモリ DB を使用します（テスト用）。

---

## 使い方（主要なユースケース）

以下は主要な機能を Python REPL / スクリプトから利用するための最小例です。

1) 日次 ETL（市場データ取得 → DB 保存 → 品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量生成（features テーブルの構築）
```python
from datetime import date
from kabusys.data.schema import get_connection, init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print("features upserted:", count)
```

3) シグナル生成（signals テーブルへの書き込み）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print("signals generated:", total)
```

4) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes: 銘柄コード集合（抽出時に使用）
results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(results)
```

5) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

6) J-Quants から直接データ取得（テスト・バッチ用）
```python
from kabusys.data import jquants_client as jq
# id_token を指定せずにキャッシュから取得（自動でリフレッシュ可能）
quotes = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## よくあるトラブルシューティング

- ValueError: 環境変数が未設定
  - config.Settings._require が未設定の必須キーで例外を出します。`.env` を作成し必要キーを埋めてください。

- DuckDB に接続できない / ディレクトリ作成エラー
  - 指定した DUCKDB_PATH の親ディレクトリに書き込み権限があるか確認してください。

- J-Quants API エラー（401）
  - リフレッシュトークンが無効な場合に発生します。JQUANTS_REFRESH_TOKEN を確認してください。get_id_token でトークン取得を手動実行して確認できます。

- RSS フェッチで失敗する（SSRF・ホスト制限）
  - news_collector はプライベートアドレス・非 http(s) スキームを拒否します。公開 URL を使ってください。

---

## ディレクトリ構成（抜粋）

ここでは src/kabusys 以下の主要なファイル構成と役割を示します。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント & 保存ユーティリティ
    - news_collector.py — RSS ニュース収集・前処理・DB 保存
    - schema.py — DuckDB スキーマ DDL と初期化（init_schema）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — マーケットカレンダー管理
    - features.py — zscore_normalize の再エクスポート
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログ（signal_events, order_requests, executions）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value の計算
    - feature_exploration.py — 将来リターン, IC, 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築（正規化・ユニバースフィルタ）
    - signal_generator.py — final_score 計算と signals 生成
  - execution/
    - __init__.py — 発注・約定処理（将来実装/分離想定）

（ファイルはリポジトリの提供コードに基づきます。詳細な追加モジュールや CLI がある場合は該当するドキュメントを参照してください。）

---

## 開発上の注意点 / 設計上の留意点

- ルックアヘッドバイアス防止: 全ての戦略計算・シグナル生成は target_date 時点のデータのみを使用する設計です。
- 冪等性: API からの保存処理は ON CONFLICT / INSERT … DO UPDATE 等を活用して冪等化されています。
- トランザクション: 置換処理（対象日分の削除→挿入）はトランザクションで原子性を保証します。
- セキュリティ: news_collector では SSRF 対策、defusedxml による XML の安全パース、受信サイズ制限を実装しています。
- 環境切替: KABUSYS_ENV による環境区別（development / paper_trading / live）をサポートします。

---

必要であれば、この README に以下の情報を追加できます:
- pyproject.toml / requirements.txt に基づくインストール手順
- CI / デプロイ手順
- 具体的なテーブル定義のドキュメント（DataSchema.md の要約）
- サンプル .env.example ファイル

追加が必要であれば指示してください。