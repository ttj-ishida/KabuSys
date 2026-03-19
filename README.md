# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
J-Quants などのマーケットデータを取得し、DuckDB に蓄積、特徴量生成・シグナル生成、ニュース収集、カレンダー管理、監査ログ等を提供します。

---

## 概要

KabuSys は以下の主要コンポーネントを含むモジュール群です。

- データ収集 (J-Quants API) と ETL パイプライン
- DuckDB を用いたスキーマ設計とデータ保存（Raw / Processed / Feature / Execution 層）
- ファクター計算・特徴量エンジニアリング（research / strategy 層）
- シグナル生成ロジック（final_score の計算、BUY/SELL 判定）
- ニュース収集・銘柄紐付け（RSS 収集、前処理、安全対策あり）
- 市場カレンダー管理（JPX）
- 監査ログ（signal → order → execution のトレーサビリティ）

設計方針として、ルックアヘッドバイアス防止、冪等性（DB 保存は ON CONFLICT ベース）、外部 API へのレート制御・リトライ、SSRF 等のセキュリティ対策を重視しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants から日次株価（OHLCV）、財務データ、マーケットカレンダーを取得（ページネーション対応・トークン自動リフレッシュ）
  - DuckDB に raw / processed / feature / execution 層のテーブルを冪等的に作成・更新
- ETL パイプライン
  - 差分更新（最終取得日ベース）・バックフィル対応の run_daily_etl
  - 品質チェックフレームワーク（quality モジュール参照）
- 特徴量 / 研究
  - momentum / volatility / value 等のファクター計算（research/factor_research）
  - Zスコア正規化 utilities（data.stats.zscore_normalize）
  - ファクター探索（IC 計算、将来リターン算出、統計サマリー）
- 戦略
  - feature_engineering.build_features: 正規化済み特徴量を features テーブルへ保存
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナルを生成し signals テーブルへ保存
- ニュース収集
  - RSS 取得、URL 正規化、記事 ID 生成（SHA-256）、raw_news 保存、銘柄コード抽出と紐付け
  - defusedxml を使った安全な XML パース、SSRF 対策、レスポンスサイズ制限
- カレンダー管理
  - market_calendar の更新・営業日判定・前後営業日探索等
- 監査ログ
  - signal_events, order_requests, executions 等によるトレーサビリティ

---

## 必要条件（推奨）

- Python 3.10 以上（PEP 604 の型合成などを使用）
- pip（パッケージ管理）
- 推奨依存パッケージ（最小限）:
  - duckdb
  - defusedxml

実際のセットアップではさらに requests 等が必要になる場合があります。プロジェクトに requirements.txt があればそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローン / コピーし、開発環境を用意します。

   (プロジェクトルート = pyproject.toml や .git があるディレクトリ)

2. 仮想環境を作成して有効化（例: venv / poetry 等）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール

   最低限:

   ```bash
   pip install duckdb defusedxml
   ```

   開発用に pyproject.toml / requirements.txt がある場合はそちらを利用してください。

4. 環境変数の設定

   プロジェクトルートに `.env` を置くことで自動的に読み込まれます（config モジュールが .env/.env.local を探索して読み込みます）。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須となる主な環境変数:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（必要な場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   省略可能 / デフォルトあり:

   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB 等に使う SQLite パス（デフォルト: data/monitoring.db）

5. DuckDB スキーマの初期化

   Python REPL やスクリプトから下記を実行します。

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
   ```

   init_schema は必要な全テーブル・インデックスを作成し、DuckDB 接続を返します。

---

## 簡単な使い方（例）

以下は主要ワークフローのサンプルコードです。日付には datetime.date を使用します。

- 日次 ETL（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量構築（features テーブルへ保存）

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema(settings.duckdb_path)
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへ保存）

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema(settings.duckdb_path)
total_signals = generate_signals(conn, target_date=date.today())
print(f"signals written: {total_signals}")
```

- ニュース収集ジョブ（既知の銘柄コードセットを渡して銘柄紐付け）

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ（夜間バッチ）

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須 for kabu API) — kabuステーション 接続用パスワード
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/..）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視DB等（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動ロードを無効化

config.Settings でプロパティとしてアクセス可能です（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成（主なファイル・モジュール）

プロジェクトは `src/kabusys` 以下に配置されています。主要なファイルと役割は以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（.env 自動ロード、Settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、レート制御、リトライ、保存関数）
    - news_collector.py
      - RSS 取得・前処理・raw_news 保存、銘柄抽出と紐付け
    - schema.py
      - DuckDB のスキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
    - features.py
      - data.stats.zscore_normalize の再エクスポート
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - audit.py
      - 監査ログテーブル定義（signal_events, order_requests, executions）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - その他: quality モジュール等（コードベース次第）
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（raw ファクターを統合し正規化して features へ保存）
    - signal_generator.py
      - generate_signals（features + ai_scores を統合して BUY/SELL を生成）
  - execution/
    - __init__.py
      - （発注・execution 層の実装箇所）
  - monitoring/
    - （監視・メトリクス関連の実装箇所）

各モジュールは DuckDB 接続を受け取り純粋にデータ処理を行うよう設計されており、本番発注 API 等への直接の副作用を持たない領域は分離されています。

---

## 実運用上の注意

- 実際の売買を行う場合は paper_trading → live 等の環境を慎重に切り替えてください。KABUSYS_ENV により挙動を分離しています。
- API レート制限やトークン管理は実装済みですが、長時間バッチや分散実行を行う場合は追加の監視・バックオフ戦略を加えてください。
- ニュース収集や外部 URL 処理については SSRF / XML BOM / 大容量レスポンス対策を組み込んでいますが、外部ソースの多様化時は設定やタイムアウトを見直してください。
- DuckDB のバージョンや SQL 構文互換性に注意してください（現状の DDL は DuckDB の仕様に合わせて作成されています）。

---

## 貢献 / ライセンス

- 貢献歓迎。Issue / Pull Request ベースで改善やバグ修正をお願いします。
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください。

---

この README はコードベースの主要機能と使い方の概要を示しています。詳細は各モジュール（特に data/schema.py, data/jquants_client.py, research/factor_research.py, strategy/*, data/news_collector.py）を参照してください。