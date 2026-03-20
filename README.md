# KabuSys

日本株向けの自動売買システム基盤（ライブラリ）。データ取得（J-Quants）、ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成される Python パッケージです：

- J-Quants API からの日次株価・財務・カレンダー取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 特徴量計算（Momentum / Value / Volatility 等）と Z スコア正規化
- シグナル生成（複数コンポーネントの重み付け合成、Bear レジーム抑制、SELL エグジット判定）
- RSS ベースのニュース収集・前処理・銘柄紐付け（SSRF 対策・XML セキュアパース）
- マーケットカレンダー管理（営業日判定、next/prev/trading days）
- 監査ログ／発注トレーサビリティ（signal → order → execution の追跡）
- 簡易な設定管理（.env または環境変数）

設計上の重要点：
- ルックアヘッドバイアス回避のため、各処理は target_date 時点までの情報のみを使用する設計
- DuckDB に対する保存は可能な限り冪等（ON CONFLICT / INSERT … DO UPDATE / DO NOTHING）を保つ
- ネットワーク外部呼び出しは jquants_client や news_collector に集中。戦略ロジックは API に依存しない

---

## 機能一覧（主要）

- 環境/設定管理
  - 自動でプロジェクトルートから `.env` / `.env.local` を読み込む（無効化可）
  - 必須環境変数のアクセサ（settings オブジェクト）

- データ取得 / 永続化
  - J-Quants API クライアント（fetch + save、ページネーション、リトライ、トークン自動更新、レート制御）
  - raw_prices / raw_financials / market_calendar などの保存ユーティリティ
  - DuckDB スキーマ定義と初期化（init_schema）

- ETL / データパイプライン
  - 差分取得（最終取得日ベース）・バックフィル・品質チェック
  - 日次 ETL のワンストップ実行（run_daily_etl）

- フィーチャー / 研究
  - ファクター計算（momentum / volatility / value）
  - Z スコア正規化ユーティリティ（クロスセクション）
  - 将来リターン・IC（スピアマン）計算、ファクター統計サマリ

- 戦略
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals）：コンポーネントスコア計算、AI スコア統合、BUY/SELL の判定と signals テーブル保存

- ニュース収集
  - RSS フィード取得（gzip 対応・サイズ上限・SSRF/リダイレクト検査）
  - 文章前処理、記事ID のハッシュ化による冪等保存、銘柄抽出と紐付け

- マーケットカレンダー
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - カレンダーの差分更新ジョブ（calendar_update_job）

- 監査ログ（audit）
  - signal_events / order_requests / executions 等でトレーサビリティを保持

---

## セットアップ手順

前提
- Python 3.10+（typing の一部ヒントで | 型などを使用）
- DuckDB を使用（パッケージ依存）

1. リポジトリをクローン（またはパッケージをインストール）
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （その他必要なパッケージがある場合は pyproject.toml / requirements.txt を参照）
4. 環境変数を設定
   - 推奨: プロジェクトルートに `.env` を作り設定を記述（下記参照）
   - 自動で .env をロード：パッケージの config モジュールが .git または pyproject.toml を探索して .env をロードします
   - テスト等で自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数（Settings 参照。未設定時は ValueError を送出）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API パスワード（発注連携時）
- SLACK_BOT_TOKEN : Slack 通知用トークン
- SLACK_CHANNEL_ID : Slack チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV : development / paper_trading / live （デフォルト development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite DB パス（デフォルト data/monitoring.db）

---

## 使い方（基本例）

以下はパッケージ API を利用した基本的なワークフロー例です。

1) DuckDB スキーマ初期化
- Python REPL / スクリプトで：

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ DB も可

2) 日次 ETL の実行

from kabusys.data.pipeline import run_daily_etl
from datetime import date
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

3) 特徴量作成（build_features）

from kabusys.strategy import build_features
from datetime import date
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")

4) シグナル生成（generate_signals）

from kabusys.strategy import generate_signals
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {count}")

5) ニュース収集ジョブ（RSS）

from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄候補セット（例: set of "7203","6758",...）
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)

6) カレンダージョブ（夜間バッチ）

from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")

注意点：
- jquants_client は内部でレート制御／リトライ／トークン自動更新を行います。
- run_daily_etl 等は内部で例外を捕捉して処理を継続し、ETLResult にエラー情報を格納します。
- .env 自動ロードはプロジェクトルート（.git / pyproject.toml があるディレクトリ）を基準に行われます。

---

## 設定 (.env) の例

.env.example を参考に作成してください（例）:

JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

自動ロードが不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してパッケージロード時の自動読み込みを無効化できます。

---

## トラブルシューティング（よくある問題）

- ValueError: 環境変数 'XXX' が設定されていません。
  - 必須の環境変数が未設定です。.env を作成するか環境変数をエクスポートしてください。

- J-Quants API エラー / タイムアウト
  - ネットワークやトークン期限切れの可能性があります。jquants_client は 401 受信時にトークンを自動更新しますが、refresh token が無効だと失敗します。

- RSS 取得でリダイレクトや接続失敗
  - news_collector は SSRF 対策（プライベートアドレス禁止）やリダイレクト検査、サイズ上限を設けています。該当ログを確認してください。

- DuckDB スキーマ/テーブルがない
  - init_schema() を呼んで初期化してください。get_connection() は単に接続を返すだけでスキーマ初期化は行いません。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys/ 以下）

- __init__.py
- config.py
  - Settings、.env 自動ロードロジック、環境変数アクセサ
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（fetch/save、rate limit、retry、token）
  - news_collector.py         — RSS 取得・前処理・raw_news 保存、銘柄抽出
  - schema.py                 — DuckDB スキーマ定義・init_schema / get_connection
  - pipeline.py               — ETL パイプライン（run_daily_etl 他）
  - stats.py                  — zscore_normalize 等の統計ユーティリティ
  - features.py               — zscore_normalize の公開ラッパ
  - calendar_management.py    — マーケットカレンダー操作と更新ジョブ
  - audit.py                  — 監査ログ（signal_events / order_requests / executions）
  - (その他 data.*)
- research/
  - __init__.py
  - factor_research.py        — momentum/volatility/value のファクター計算
  - feature_exploration.py    — 将来リターン計算、IC、ファクター統計
- strategy/
  - __init__.py
  - feature_engineering.py    — ファクター正規化・フィーチャー作成・features テーブルへの upsert
  - signal_generator.py       — final_score の算出と BUY/SELL シグナル生成、signals テーブルへの保存
- execution/
  - __init__.py
  - （発注・ブローカー連携用モジュールを配置想定）
- monitoring/
  - （監視・アラート用モジュールを配置想定）

---

## 開発 / 貢献

- コードスタイルや設計意図は各モジュールのドキュメンテーション文字列（docstring）に詳述しています。新しい機能追加や修正は docstrings と一貫した単体テストを追加してください。
- .env の取り扱いや実運用時の機密情報は環境変数管理サービス（Vault など）を推奨します。

---

必要であれば、README に以下を追加できます：
- pyproject.toml / requirements.txt に基づく依存一覧
- CI / テストの実行方法
- デプロイ・本番運用（kabuステーション連携、Slack 通知の使い方）
- 具体的なコマンドラインツール・サンプルジョブの例

どの追加情報が必要か教えてください。