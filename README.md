# KabuSys

日本株向けの自動売買システム（ライブラリ）。  
データ収集・ETL、ファクター計算、特徴量生成、シグナル生成、監査／実行レイヤの基盤を提供します。研究環境（research）でのファクター設計を本番ワークフローへつなぐことを目的としています。

## 概要
KabuSys は以下の主要コンポーネントで構成されています。

- data: J-Quants API クライアント、ETL パイプライン、ニュース収集、DuckDB スキーマ定義などのデータ基盤
- research: ファクター計算・特徴量探索・統計ユーティリティ
- strategy: 特徴量の正規化／合成（feature engineering）と最終スコア計算・シグナル生成
- execution: （発注・執行処理を実装するためのプレースホルダ）
- config: 環境変数・設定の自動読み込みとアクセス用ラッパー

設計上の方針として、ルックアヘッドバイアス回避、冪等性、API レート制限対応、トレーサビリティ（監査ログ）を重視しています。

## 主な機能一覧
- J-Quants API クライアント（ページネーション、リトライ、トークン自動リフレッシュ、レート制限）
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（市場カレンダー・日足・財務の差分取得、品質チェックとの連携）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量の Z スコア正規化とクリッピング（feature_engineering）
- シグナル生成（複数コンポーネントの重み付け合成、Bear レジーム抑制、エグジット判定）
- ニュース収集（RSS, トラッキングパラメータ削除、SSRF 対策、記事→銘柄の紐付け）
- マーケットカレンダー管理（営業日判定、next/prev/trading_days 等）
- 監査ログスキーマ（signal / order / execution のトレーサビリティ）

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の `X | Y` 型注釈などを使用）
- DuckDB（Python パッケージで提供）および必要なライブラリ

推奨手順（仮想環境内で実行）

1. リポジトリをチェックアウトし仮想環境を作成
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
```

2. 必要パッケージをインストール（例）
```bash
pip install duckdb defusedxml
# 開発用にローカル編集可能なインストール
pip install -e .
```
※ 実プロジェクトでは requirements.txt / pyproject.toml で管理してください。

3. 環境変数の設定
プロジェクトルートに `.env`（または `.env.local`）を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。必要な主要環境変数は以下です。

必須（本番／一部機能で必須）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション（デフォルト値あり）:
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト "development"）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト "INFO"）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト `data/monitoring.db`）

例 `.env`（テンプレート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマ初期化（Python）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

これで DB のテーブルが作成されます。

## 使い方（主な API と実行例）

Python スクリプト / REPL からライブラリを呼び出す形で利用します。

- 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量を構築（features テーブルへ保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2025, 1, 31))
print(f"features upserted: {n}")
```

- シグナルを生成（signals テーブルへ保存）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2025, 1, 31))
print(f"signals written: {count}")
```

- ニュース収集ジョブ（RSS 収集→ raw_news / news_symbols へ保存）
```python
from kabusys.data.news_collector import run_news_collection
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"}, timeout=30)
print(res)  # {source_name: saved_count}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- 多くの関数は DuckDB 接続を受け取る設計です。接続はアプリ側で管理してください。
- 環境変数/トークンが未設定だと Settings で例外が出ます（_require 関数）。.env を正しく準備してください。
- run_daily_etl 等は内部で複数の処理を順次実行し、例外は個別に捕捉してログに出すため、戻り値（ETLResult）を確認して状況判断してください。

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主要ファイルと役割です。

- kabusys/
  - __init__.py — パッケージ初期化、バージョン情報
  - config.py — 環境変数 / 設定管理（自動 .env ロード、Settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - schema.py — DuckDB スキーマ定義と init_schema/get_connection
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - news_collector.py — RSS 収集・パース・DB 保存
    - calendar_management.py — マーケットカレンダー管理・ジョブ
    - features.py — data 層の特徴量ユーティリティ再エクスポート
    - audit.py — 監査ログ（signal_events / order_requests / executions）スキーマ
    - pipeline.py — ETL 実行ロジック（差分更新・バックフィル・品質チェック呼び出し）
  - research/
    - __init__.py — research API の再エクスポート
    - factor_research.py — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — IC / forward returns / 統計サマリー
  - strategy/
    - __init__.py — strategy API のエクスポート
    - feature_engineering.py — features テーブル構築（正規化・フィルタ）
    - signal_generator.py — final_score 計算と signals テーブルへの書き込み
  - execution/ — 発注・execution 層（プレースホルダ）
  - monitoring/ — 監視関連（SQLite を使う実装など、コードベースに含まれる想定）

（上記はコードベースの主要モジュールを抜粋した一覧です。詳細は各ファイルの docstring を参照してください。）

## 設定・運用に関する補足
- 環境（KABUSYS_ENV）: development / paper_trading / live のいずれかを指定。live のときは発注系の有効化や Slack 通知等の動作に注意してください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。テスト時に無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ロギングは LOG_LEVEL で制御します。外部通信（J-Quants 等）はレート制限・リトライポリシーを備えていますが、API キーの取り扱いには十分ご注意ください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作られます。運用時はバックアップやファイル配置に気をつけてください。

## 開発・貢献
- 各モジュールはユニットテストしやすいように設計されています（例: id_token の注入、ネットワーク呼び出しの差し替えポイント）。
- 変更を加える際は既存の ETL フロー・SQL クエリへの影響（スキーマ、インデックス、パフォーマンス）に注意してください。

---

詳細は各ソースファイルの docstring に仕様・設計方針が含まれています。README でカバーしていない運用上の細かい挙動（例: 各種閾値、重み、クリッピング値など）は該当モジュールのコメントを参照してください。