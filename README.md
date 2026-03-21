# KabuSys

KabuSys は日本株の自動売買プラットフォーム用ライブラリ群です。  
J-Quants からの市場データ取得（ETL）、DuckDB によるデータ管理、特徴量作成、シグナル生成、ニュース収集、マーケットカレンダー管理、発注／監査のスケルトン等を提供します。研究（research）用途のユーティリティも含み、戦略開発から実運用（paper/live）まで想定した設計です。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ参照）
- DuckDB を単一ソースとして冪等（idempotent）に保存
- 外部 API 呼び出しは専用クライアントでラップ（レート制御・リトライ・トークン自動更新）
- セキュリティ配慮（RSS の SSRF 対策、XML デコード防御など）

---

## 機能一覧

- データ取得・保存（J-Quants）
  - 日次株価（OHLCV）、財務データ、JPX カレンダーのフェッチと DuckDB 保存（差分／バックフィル対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応

- ETL パイプライン
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック

- データスキーマ管理
  - DuckDB のスキーマ初期化（raw / processed / feature / execution 層）

- 特徴量エンジニアリング
  - calc_momentum / calc_volatility / calc_value（research）
  - build_features: 正規化・ユニバースフィルタ・features テーブルへの UPSERT

- シグナル生成
  - generate_signals: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ書き込む（Bear レジーム抑制、エグジット条件判定）

- ニュース収集
  - RSS 収集、テキスト前処理、raw_news 保存、銘柄抽出（4桁コード）と紐付け
  - SSRF 対策、受信サイズ上限、XML パース防御（defusedxml）

- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内の営業日取得、夜間カレンダー更新ジョブ

- 監査／発注スキーマ（audit）
  - signal_events / order_requests / executions 等のテーブル定義（監査ログ・トレーサビリティ）

- 研究ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー、Z スコア正規化

---

## 必要条件（Prerequisites）

- Python 3.10 以上（ソース内で `X | None` 型注釈等を利用）
- DuckDB（Python パッケージ: duckdb）
- defusedxml（RSS パーサで使用）
- （標準ライブラリでほぼ実装済み、追加依存は最小限）

推奨インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```
プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローン（またはソースを配置）
2. 仮想環境作成・依存インストール（上記参照）
3. 環境変数を設定（.env ファイルをプロジェクトルートに置くと自動ロードされます）
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（主要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意／既定値あり:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 初期化（DuckDB スキーマ作成）

Python REPL かスクリプトから DuckDB スキーマを初期化します。

例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリも可
```

init_schema は親ディレクトリを自動で作成します（ファイル版を使う場合）。

---

## 使い方（主要な API サンプル）

以下は基本的なワークフロー例です（インタラクティブ / スクリプトで実行）。

1) 日次 ETL の実行
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date, id_token など指定可能
print(result.to_dict())
```

2) 特徴量作成（build_features）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date.today())
print(f"features updated: {count}")
```

3) シグナル生成（generate_signals）
```python
from kabusys.strategy import generate_signals

n_signals = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals written: {n_signals}")
```

4) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄抽出に用いる有効コード集合（存在するコードのみ紐付け）
results = run_news_collection(conn, known_codes={"7203","6758"})
print(results)  # {source_name: saved_count}
```

5) マーケットカレンダー更新
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

6) J-Quants クライアントの直接利用例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings を読む
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date.today())
# 保存は jq.save_daily_quotes(conn, records)
```

注意点:
- 各 ETL / 書き込み関数は冪等性（ON CONFLICT 等）を重視しています。
- run_daily_etl などは例外を内部で捕捉して進めるため、戻り値の ETLResult で品質問題やエラーを確認してください。
- 環境によっては J-Quants API のレート制限（120 req/min）に注意してください（クライアント側で制御あり）。

---

## ディレクトリ構成

リポジトリの主要ファイル・モジュール（src/kabusys 以下）概要:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / settings 管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（レート制御／リトライ／保存ユーティリティ）
    - news_collector.py        — RSS 収集・前処理・保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義／初期化
    - stats.py                 — Zスコア等統計ユーティリティ
    - pipeline.py              — ETL 実行フロー（差分取得／品質チェック等）
    - features.py              — data.stats の再エクスポート
    - calendar_management.py   — カレンダー更新・営業日判定ユーティリティ
    - audit.py                 — 発注／監査ログ用スキーマ（監査トレーサビリティ）
    - ...（quality 等のモジュールがある想定）
  - research/
    - __init__.py
    - factor_research.py       — momentum / value / volatility のファクター計算
    - feature_exploration.py   — 将来リターン・IC・統計サマリ等の研究ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py   — features の作成（正規化・ユニバースフィルタ）
    - signal_generator.py      — final_score 計算・BUY/SELL 生成
  - execution/                 — 発注実行層（スケルトン。kabuステーション連携等を実装）
  - monitoring/                — 監視 / メトリクス（想定）

（実際のツリーはリポジトリに依存します。上記はコードベースからの抜粋と説明です。）

---

## 設定とデバッグのヒント

- 環境変数は .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（config._find_project_root により .git や pyproject.toml を探索）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテストを容易にしてください。
- ログレベルは LOG_LEVEL で制御（DEBUG/INFO/…）。問題解析時は DEBUG にすると内部挙動を詳細にログ出力します。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb。バックアップやバージョン管理には注意してください。

---

## 貢献・改善案

- execution 層（kabu API 連携、注文送信・レスポンス処理）の実装拡充
- 品質チェック（quality モジュール）のルール追加
- AI スコア生成パイプライン（ai_scores 填充）
- テストスイート（ユニット／統合テスト）と CI の整備

---

質問や追加ドキュメント（各モジュールの詳細、データモデル図、運用手順など）が必要であれば教えてください。README に追記して整理します。