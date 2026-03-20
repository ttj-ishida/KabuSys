# KabuSys

日本株向けの自動売買／データ基盤ライブラリセットです。  
データ取得（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、監査用スキーマなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・自動リトライ・トークン自動更新）
- DuckDB を利用したデータスキーマ（Raw / Processed / Feature / Execution 層）の定義と初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）および特徴量正規化
- 戦略用のシグナル生成（コンポーネントスコアの統合・Bear レジーム抑制・エグジット判定）
- RSS ベースのニュース収集および銘柄紐付け
- 発注・約定・監査ログ向けスキーマ（監査トレーサビリティ設計）

設計上の特徴：
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 冪等性（DB保存は ON CONFLICT / トランザクションで保証）
- 外部依存を最小化（標準ライブラリ中心、DuckDB をデータエンジンとして使用）
- セキュリティ考慮（RSS の SSRF 対策、XML パースの安全化など）

---

## 機能一覧

主要機能（モジュール別）

- kabusys.config
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 環境変数経由の設定取得（トークン・DB パス・環境フラグ等）
- kabusys.data.jquants_client
  - J-Quants API 呼び出し（レート制御、トークン取得・更新、ページネーション対応）
  - fetch/save helper（株価・財務・カレンダーの取得と DuckDB 保存）
- kabusys.data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema() による初期化
- kabusys.data.pipeline
  - 日次 ETL（差分取得、バックフィル、品質チェック）
  - run_daily_etl() による一括パイプライン
- kabusys.data.news_collector
  - RSS からのニュース収集、前処理、raw_news 保存、銘柄抽出と紐付け
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（研究支援）
  - zscore_normalize（正規化ユーティリティ）
- kabusys.strategy
  - build_features(conn, target_date) — 特徴量作成・正規化・features テーブルへの UPSERT
  - generate_signals(conn, target_date, ...) — features と ai_scores を統合して signals を作る
- kabusys.execution / monitoring
  - 実行・監視周りのインターフェース（スケルトン・スキーマが含まれる）

---

## 要求環境 / 依存パッケージ

- Python 3.9+
- duckdb
- defusedxml
- （標準ライブラリを中心に設計されていますが、実行環境に合わせ以下をインストールしてください）

例（pip）:
```bash
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / ソースを配置
2. Python 環境を用意（venv 推奨）
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` / `.env.local` を配置できます。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
5. DuckDB スキーマを初期化

例：Python REPL / スクリプトで初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # デフォルトパス（環境変数で変更可）
```

---

## 環境変数

主に使用する環境変数（Settings から）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API 用パスワード（発注連携時）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知用チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）

注意:
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml から検出して行います。
- 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（抜粋例）

以下はライブラリの代表的な利用フロー例です。実運用ではログ設定、エラーハンドリング、スケジューリング（cron / Airflow 等）を追加してください。

1) DB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（build_features）
```python
from kabusys.strategy import build_features
from datetime import date

n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成（generate_signals）
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", ...}  # 有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) J-Quants の個別データ取得（テスト等）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from datetime import date

token = get_id_token()  # settings から refresh token を使って取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なモジュール配置（src/kabusys 以下抜粋）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - features.py            — features ユーティリティ（再エクスポート）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - stats.py               — 統計ユーティリティ（zscore 等）
    - audit.py               — 監査ログスキーマ
  - research/
    - __init__.py
    - factor_research.py     — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 特徴量作成（build_features）
    - signal_generator.py    — シグナル生成（generate_signals）
  - execution/ (空のパッケージ位置)
  - monitoring/ (空のパッケージ位置)
  - その他ユーティリティ群...

（上記はコードベースに含まれる主なモジュールで、さらに細分化された関数群・ユーティリティが存在します）

---

## 運用上の注意点 / ベストプラクティス

- 環境分離
  - KABUSYS_ENV を利用して本番（live）と検証（paper_trading / development）を明確に分ける。
- DB バックアップ
  - DuckDB ファイルは定期的にバックアップを取得してください。監査ログは削除しない前提です。
- API レート制限
  - J-Quants のレート上限を超えないよう内部でスロットリングを実装していますが、大規模バッチや同時プロセス実行時は注意してください。
- セキュリティ
  - .env に機密情報（トークン等）を保存する際はファイルのアクセス権に注意。
  - news_collector は SSRF 対策や defusedxml を利用していますが、外部フィードを大量に扱う場合は監視を実装してください。
- テスト
  - kabusys.config の自動 .env ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。関数に id_token を注入できる設計のため、外部呼び出しをモックしてユニットテストが可能です。

---

必要であれば README に含める実行例（cron / systemd / Airflow のジョブ定義）、より詳細なスキーマ図や StrategyModel.md / DataPlatform.md の抜粋、サンプル .env.example を追加できます。どの追加情報がほしいか教えてください。