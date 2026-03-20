# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB をデータ層に利用し、J-Quants API や RSS を取り込んで特徴量を作成・正規化し、戦略シグナルを生成するためのモジュールを提供します。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 主な機能一覧
- 要件・依存関係
- セットアップ手順
- 使い方（例）
- 環境変数（設定）
- ディレクトリ構成（主要ファイル）
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants、RSS 等）→ ETL → 特徴量作成 → シグナル生成 → 発注監査までを想定したライブラリ群です。モジュールは次の層に分かれます。

- data: データ取得（J-Quants）、ETL、ニュース収集、DuckDB スキーマ、統計ユーティリティ
- research: ファクター計算・特徴量探索（研究用）
- strategy: 特徴量の正規化・統合とシグナル生成
- execution: 発注 / 約定 / ポジション管理（パッケージ内定義あり）
- monitoring: 監視・Slack 通知等（トークン管理など）

設計方針として、ルックアヘッドバイアス回避、冪等性（DB の INSERT は ON CONFLICT 処理）、API レート制御、ネットワーク安全対策（RSS の SSRF 対応）などが取り入れられています。

---

## 主な機能一覧

- J-Quants API クライアント（jquants_client）
  - 株価日足 / 財務データ / 市場カレンダーの取得（ページネーション対応）
  - トークン自動リフレッシュ、指数バックオフ付きリトライ、固定間隔レートリミッタ
  - DuckDB への冪等保存ユーティリティ（save_*）

- データスキーマ初期化（data.schema）
  - DuckDB 用の完全なスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema() で初期化可能

- ETL パイプライン（data.pipeline）
  - 差分取得ロジック（最終取得日からの再取得とバックフィル）
  - 日次 ETL 実行（run_daily_etl）＋品質チェックフック

- ニュース収集（data.news_collector）
  - RSS フィード収集、XML の安全パース（defusedxml）、URL 正規化、記事ID の SHA256 ベース生成
  - raw_news / news_symbols 保存（冪等・チャンク挿入）

- 統計ユーティリティ（data.stats）
  - クロスセクションの Z スコア正規化（zscore_normalize）

- 研究用モジュール（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）などの探索ユーティリティ

- 戦略モジュール（strategy）
  - build_features: raw ファクターを統合・フィルタ・正規化して features テーブルへ保存
  - generate_signals: features と ai_scores を組み合わせて final_score を計算し BUY/SELL シグナルを signals テーブルへ保存
  - エグジット判定（ストップロス等）を含む

- 監査（data.audit）
  - signal_events / order_requests / executions 等、トレーサビリティ用テーブル定義

---

## 要件・依存関係

- Python 3.10 以上（typing のパイプ型等を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- （任意）J-Quants API を利用する場合はインターネット接続と J-Quants のリフレッシュトークン

インストール例（venv 推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発インストール（パッケージ化されている想定）
pip install -e .
```

※ 実際の setup.py / pyproject.toml で依存関係が管理されている場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境作成・依存パッケージをインストール（上記参照）
3. 環境変数を用意（.env ファイル推奨、後述の例を参照）
4. DuckDB スキーマを初期化

DB 初期化例:

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 以降 conn を使って ETL / 特徴量計算 / シグナル生成等を実行
```

コマンドライン一行例:

```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

---

## 使い方（簡単な例）

DuckDB 接続を初期化し、日次 ETL を実行して特徴量・シグナルまで回す基本パイプライン例:

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.strategy import build_features, generate_signals

# DB 初期化（既存があればスキップされます）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL（J-Quants からデータ取得して保存）
result = run_daily_etl(conn)  # 引数で target_date や id_token を指定可能

# 特徴量構築（research のファクター計算結果を基に features を更新）
build_count = build_features(conn, date.today())

# シグナル生成（デフォルト閾値・重みを使用）
signals_count = generate_signals(conn, date.today())
```

個別ジョブの実行例:

- 市場カレンダーの夜間更新ジョブ:
  - data.calendar_management.calendar_update_job(conn)
- ニュース収集:
  - data.news_collector.run_news_collection(conn, sources=..., known_codes=...)

ログレベルは環境変数 LOG_LEVEL で制御できます（DEBUG / INFO / ...）。

---

## 環境変数（設定）

自動的にプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD に依存しない探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な設定項目（Settings クラスから）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例: .env (最小)

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

Settings API 使用例:

```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.is_live)
```

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュール・ファイルの概観です（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント（取得／保存）
    - schema.py                 # DuckDB スキーマ定義・init_schema
    - pipeline.py               # ETL パイプライン（run_daily_etl 他）
    - news_collector.py         # RSS 収集・保存
    - calendar_management.py    # 市場カレンダー管理
    - audit.py                  # 監査ログ/DML
    - features.py               # zscore_normalize の再エクスポート
    - stats.py                  # 統計ユーティリティ（zscore_normalize）
    - quality.py                # （品質チェック：pipeline から参照される想定）
  - research/
    - __init__.py
    - factor_research.py        # momentum/volatility/value 計算
    - feature_exploration.py    # forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py    # build_features
    - signal_generator.py       # generate_signals
  - execution/
    - __init__.py               # 発注・約定処理（拡張想定）
  - monitoring/
    - (モジュール: Slack 通知等の実装想定)

注: 一部ファイルはコードベースの一部のみを抜粋しています。quality モジュールなど、pipeline が参照する補助モジュールは別途存在する想定です。

---

## 設計上のポイント / 注意事項

- ルックアヘッドバイアス防止:
  - 特徴量・シグナル生成は target_date 時点までのデータのみを参照する設計です。
  - データ取得時には fetched_at を保存し、いつデータが取得可能になったかを追跡できます。

- 冪等性:
  - DB 保存処理は可能な限り ON CONFLICT / RETURNING を用いて冪等に実装されています。

- API リクエストの堅牢性:
  - jquants_client はレート制限、リトライ、トークン自動リフレッシュ（401 の場合）を備えています。

- ネットワーク安全:
  - RSS 取得では SSRF 対応のリダイレクト検査・プライベートアドレス拒否や受信サイズ制限を実装しています。

- DB 初期化:
  - init_schema は必要なディレクトリを作成し、全テーブル・インデックスを作成します。初回は init_schema を使ってから各種ジョブを実行してください。

- 環境区分:
  - KABUSYS_ENV によって is_live / is_paper / is_dev の振る舞いを分けられます。実際の発注処理を行う際は live 環境での慎重な運用が必須です。

---

## 追加の開発メモ

- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると .env 自動読み込みを無効化できます（ユニットテストで環境を制御したい場合に便利）。
- duckdb 接続はスレッドセーフ性・同時接続制限を考慮して扱ってください（アプリケーション設計次第で接続プールやプロセス分離を検討してください）。

---

ご不明点や追加してほしい利用例（cron での日次実行例、Slack 通知の設定方法、発注フローのサンプル等）があれば教えてください。README を拡張して具体的な運用手順や運用チェックリストも作成できます。