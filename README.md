# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群です。データ収集（J‑Quants）、ETL、ファクター計算、特徴量構築、シグナル生成、ニュース収集、監査用スキーマなど、研究〜運用に必要な主要コンポーネントを含みます。

## プロジェクト概要
- 目的: 日本株の市場データ取得から特徴量作成、シグナル生成、監査までを一貫して扱うためのモジュール群を提供する。
- 設計方針:
  - ルックアヘッドバイアスを防ぐため、target_date 時点までのデータのみを使用。
  - DuckDB をローカル DB として用い、スキーマは冪等に初期化。
  - API クライアントはレート制御・リトライ・トークン自動更新を備える。
  - ニュース収集は SSRF 等の安全対策を備えた実装。
  - 発注/実行/監査用テーブルを含む実運用を想定したスキーマ設計。

## 主な機能一覧
- データ取得・保存
  - J‑Quants からの株価（日足）、財務、マーケットカレンダー取得（jquants_client）
  - raw データ → DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック、日次 ETL 実行（data.pipeline）
- スキーマ管理
  - DuckDB スキーマ定義・初期化（data.schema.init_schema）
- ファクター計算 / 研究
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC、統計サマリ（research.feature_exploration）
- 特徴量作成
  - raw ファクターの正規化・ユニバースフィルタ適用・features テーブルへの書き込み（strategy.feature_engineering）
- シグナル生成
  - features / ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存（strategy.signal_generator）
- ニュース収集
  - RSS 取得、前処理、raw_news 保存、記事⇄銘柄紐付け（data.news_collector）
- ユーティリティ
  - Z スコア正規化、マーケットカレンダーヘルパー、監査ログ用 DDL など

## 必要条件 / 前提
- Python 3.10+
  - （コード上で | None などの構文を使用）
- 主要ランタイム依存パッケージ（最小）
  - duckdb
  - defusedxml
- ネットワークアクセス（J‑Quants API、RSS）

※ 実行環境や追加のパッケージは運用方針により変わります。requirements ファイルや Poetry/Poetry.lock がある場合はそれに従ってください。

## 環境変数 / 設定
`kabusys.config.Settings` で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

オプション（既定値あり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)、既定 development
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）、既定 INFO

.env の自動読み込み:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` と `.env.local` を自動読み込みします。
  - 読み込み優先順: OS 環境変数 > .env.local > .env
  - テストなどで自動ロードを無効化する場合:
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット

## セットアップ手順（例）
1. リポジトリをクローンして仮想環境を作成
   - git clone ...; python -m venv .venv; source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成（.env.example を参考）
   - 例 (.env):
     - JQUANTS_REFRESH_TOKEN=xxxxxxxx
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで schema.init_schema を呼ぶ（以下参照）

## 使い方（主要な操作例）
以下は簡単な Python スニペット例です。実運用ではアプリケーション層から呼び出してください。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（J‑Quants からデータを取得し保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())
```

- ファクター → 特徴量（features テーブル）構築
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2024, 1, 31))
print(f"features upserted: {count}")
```

- シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total_signals = generate_signals(conn, date.today())
print(f"signals written: {total_signals}")
```

- ニュース収集ジョブ実行（RSS から raw_news を保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
results = run_news_collection(conn)  # sources, known_codes を指定可能
print(results)
```

- J‑Quants から直接データを取得して保存（テスト時など）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
rows = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, rows)
print(saved)
```

## ロギング・デバッグ
- 設定: 環境変数 LOG_LEVEL で制御（既定 INFO）。
- モジュールごとのデバッグ出力を有効にするにはログ設定を行ってください（logging.basicConfig 等）。

## 注意点 / 運用上のポイント
- Python バージョンは 3.10 以上を推奨（構文依存）。
- J‑Quants API のレート制限（デフォルト 120 req/min）に従うよう RateLimiter を実装済み。多量のページング取得時は注意。
- get_id_token はリフレッシュトークンを使用して ID トークンを取得し、401 時には自動でリフレッシュします。
- ETL の差分ロジックは最終取得日を元にバックフィルを行い、API の後出し修正を取り込みます。
- ニュース収集は SSRF 対策、XML 安全対策（defusedxml）、受信サイズ上限などを備えています。
- DuckDB スキーマは多数のテーブルとインデックスを定義します。init_schema は冪等であり、既存テーブルがあれば上書きしません。
- 環境変数の自動ロードはプロジェクトルートの .env / .env.local を読み込みますが、テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## ディレクトリ構成
主要なソースファイルとモジュールの概要（パスは src/kabusys 配下）:

- __init__.py
  - パッケージ初期化（__version__ 等）
- config.py
  - 環境変数 / 設定管理（Settings）
  - .env 自動読み込みロジック
- data/
  - jquants_client.py — J‑Quants API クライアント、取得＆保存関数
  - schema.py — DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - news_collector.py — RSS 取得・前処理・raw_news 保存・銘柄抽出
  - features.py — zscore_normalize の公開ラッパ
  - stats.py — Z スコア正規化等の統計ユーティリティ
  - calendar_management.py — market_calendar 関連のユーティリティ、カレンダー更新ジョブ
  - audit.py — 監査ログ用スキーマ DDL（signal_events, order_requests, executions 等）
  - （その他）quality.py 等の品質チェックモジュール（存在する場合）
- research/
  - factor_research.py — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
- strategy/
  - feature_engineering.py — ファクターを正規化して features に書き込む
  - signal_generator.py — final_score 計算と signals 生成
- execution/
  - 発注/実行関連モジュール（将来的な実装・拡張を想定）
- monitoring/
  - 監視・アラート関連（監視 DB への接続など）

（上記はソース内の docstring / コメントを基にした主要ファイルの一覧です。）

## 貢献 / テスト
- 単体テスト、統合テストを整備することを推奨します（特に ETL、API 呼び出し、DB 書き込み、ニュースパーシング）。
- ネットワークや外部 API 呼び出しはモック可能な設計になっています（id_token 注入、_urlopen の差し替えなど）。

---

不明点や README の追記希望（例: CI、Docker、具体的な設定例、運用手順）などがあれば教えてください。必要に応じてサンプル .env.example も作成します。