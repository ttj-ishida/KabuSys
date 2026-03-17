# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETL、データ品質チェック、監査ログなどを提供し、戦略・約定レイヤと連携できる土台を目的としています。

---

## 概要

KabuSys は日本株を対象としたデータプラットフォーム兼自動売買の基盤ライブラリです。主に以下を提供します。

- J-Quants API からの株価（OHLCV）、財務データ、マーケットカレンダー取得クライアント（リトライ・レート制御・自動トークン更新対応）
- RSS からのニュース収集（正規化・トラッキングパラメータ除去・SSRF対策・DuckDB への冪等保存）
- DuckDB スキーマ定義と初期化ユーティリティ（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティを保持）
- 環境設定管理（.env 自動読み込み、必須環境変数ラッパー）

このリポジトリはライブラリ層（strategy / execution / monitoring などを含む）を提供し、実際の戦略実装やブローカー連携はこの上に構築します。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - レート制限（120 req/min 固定スロットリング）
  - リトライ（指数バックオフ、最大3回、401 時はトークン自動更新して1回再試行）
  - DuckDB への冪等保存関数（save_*）

- data.news_collector
  - RSS フィード取得・XML パース（defusedxml）
  - URL 正規化（トラッキングパラメータ除去）、記事 ID は URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム制限・プライベートIPブロック・リダイレクト検査）
  - DuckDB への冪等保存（INSERT ... ON CONFLICT / RETURNING を使用）

- data.schema / data.audit
  - DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit）
  - 監査ログ用テーブルの初期化（UTC タイムゾーン設定、インデックス）

- data.pipeline
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル・営業日調整（market_calendar を利用）
  - 品質チェックモジュール（data.quality）との連携

- data.quality
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue 型で検出結果を返す

- config
  - .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml）
  - 環境変数ラッパー（必須値チェック、デフォルト値・検証）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要条件

- Python 3.10 以上（型注釈に | を使用しているため）
- 必要な外部パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, datetime, logging, hashlib 等

requirements.txt が無い場合は最低限以下をインストールしてください（例）:

pip install duckdb defusedxml

（実際の導入ではプロジェクトの要件に応じて追加パッケージを用意してください）

---

## セットアップ手順

1. リポジトリをクローン／取得

2. Python 環境を作成（推奨: venv / pyenv / conda）
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   またはパッケージ管理ツールを使う場合は適宜 requirements.txt / pyproject.toml を準備してインストールしてください。

4. 開発インストール（オプション）
   - プロジェクトルートで: pip install -e .

5. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` または `.env.local` を置くと自動で読み込まれます（デフォルトで OS 環境変数より優先度低）。
   - 自動読み込みを無効にするには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env に設定する主なキー例:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用途 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)

.env.example を参考に作成してください（リポジトリに用意されているケースを想定）。

---

## 使い方（簡単なサンプル）

以下はライブラリ API の主要な使い方例です。実行は Python スクリプト内またはインタラクティブシェルで行います。

1) DuckDB スキーマの初期化

```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリが自動で作成されます）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) J-Quants から株価を取得して保存（ETL の一部を直接呼ぶ例）

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
import duckdb

conn = schema.get_connection("data/kabusys.duckdb")
# トークンは環境変数から取得されます（settings.jquants_refresh_token）
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
jq.save_daily_quotes(conn, records)
```

3) 日次 ETL（推奨: data.pipeline の run_daily_etl を使用）

```python
from kabusys.data import pipeline, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) RSS ニュース収集と銘柄抽出

```python
from kabusys.data import news_collector as nc
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# 既知の銘柄コードをセットで渡すと article -> stock の紐付けが行われる
known_codes = {"7203", "6758", "9432"}
results = nc.run_news_collection(conn, known_codes=known_codes)
print(results)  # 各ソースごとの新規保存数
```

5) 品質チェックの実行（個別）

```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today(), reference_date=date.today())
for issue in issues:
    print(issue)
```

---

## 環境変数と自動読み込みの補足

- 自動読み込み: kabusys.config はプロジェクトルート（.git または pyproject.toml）を基に `.env` / `.env.local` を自動で読み込みます。OS 変数が優先され、.env.local は .env をオーバーライドします。
- テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを抑止できます。
- settings オブジェクトから値を取得できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかでなければなりません。

---

## 実装上の設計ノート（開発者向け）

- J-Quants クライアントはレート制限（120 req/min）の固定スロットリングを実装しており、ページネーション間で ID トークンをキャッシュします。401 エラー時はトークンを自動更新して1回だけ再試行します。
- news_collector は SSRF と XML Bomb 対策（defusedxml、受信サイズ制限、gzip 解凍後のサイズチェック、リダイレクト先検査）を行っています。
- DuckDB への保存は冪等（ON CONFLICT）で行う関数が多数用意されています。大量挿入はチャンク分割しています。
- ETL は Fail-Fast を採らず、品質チェック結果を収集して呼び出し元で判断できる設計です。
- 監査ログ（audit）モジュールはシグナル→発注→約定のトレーサビリティを保つためのテーブル群とインデックスを提供します。全て UTC でのタイムスタンプ保管を想定しています。

---

## ディレクトリ構成

リポジトリの主要ファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
      (戦略実装用のモジュールを配置)
    - execution/
      - __init__.py
      (約定・ブローカー連携用モジュールを配置)
    - monitoring/
      - __init__.py
      (監視・メトリクス関連)
- pyproject.toml / setup.cfg / README.md 等（プロジェクトルート）

各モジュールの責務:
- config.py : 環境変数読み込み・検証
- data/*.py : データ取得・ETL・品質チェック・スキーマ定義・監査ログ
- strategy/* : 戦略ロジック（このテンプレートでは未実装）
- execution/* : 発注ロジック・ブローカーラッパー（未実装）
- monitoring/* : 運用監視（未実装）

---

## 開発・貢献

- バグ修正、機能追加やドキュメント改善は歓迎します。プルリクエストの前に issue を立てて議論してください。
- 大きな変更を行う場合は互換性とデータマイグレーション（DuckDB スキーマ変更）に注意してください。

---

この README はコードベースから抽出した情報に基づいて作成しています。実運用時は .env.example、requirements.txt、CI 設定、テスト用データ・モックを別途用意してください。必要があれば README に追加したいセクション（例: ブローカー接続例、Slack 通知設定、FAQ）を教えてください。