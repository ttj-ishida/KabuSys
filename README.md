# KabuSys

日本株向けの自動売買システム用ライブラリ / ツールセットです。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査・発注記録などを含むモジュール群を提供します。  
このリポジトリは主に研究（research）、データプラットフォーム（data）、戦略（strategy）、発注実行（execution）層を想定した実装を含みます。

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数 (.env)
- 使い方（簡単な実行例）
- ディレクトリ構成
- 開発者向けノート

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの市場データ・財務データ・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータベーススキーマ定義 / 初期化
- ETL（差分取得・保存・品質チェック）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量正規化（Zスコア）と features テーブルへの保存
- シグナル生成（複数コンポーネントのスコア統合、買い/売り判定、sell エグジット判定）
- RSS からのニュース収集と銘柄抽出（SSRF 対策・gzip/サイズ制限・トラッキング除去）
- 監査ログ / 発注履歴・約定ログのスキーマ

設計方針として、ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）や冪等性（DB への upsert）、外部 API 呼び出しのレート制御・リトライなどの堅牢性を重視しています。

---

## 機能一覧

主な機能（モジュール）:

- kabusys.config
  - .env / 環境変数読み込み、自動ロード（プロジェクトルート検出）、必須設定取得
- kabusys.data.jquants_client
  - J-Quants API クライアント（トークン取得、ページネーション、リトライ、レート制御）
  - fetch/save: 日足、決算データ、マーケットカレンダー
- kabusys.data.schema
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- kabusys.data.pipeline
  - run_daily_etl 等の差分 ETL パイプライン（差分取得・保存・品質チェック）
- kabusys.data.news_collector
  - RSS フィード取得・記事正規化・raw_news への保存・銘柄抽出
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary（探索用ユーティリティ）
- kabusys.strategy
  - build_features（raw ファクター→正規化→features テーブルへ）
  - generate_signals（features + ai_scores → final_score → signals テーブルへ）
- kabusys.data.stats
  - zscore_normalize（クロスセクション正規化）

その他: カレンダー管理、監査ログ、ETL 結果クラス、ヘルパー群。

---

## 必要条件

- Python 3.9+
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリで多くを賄う設計ですが、実行環境に応じて依存を追加してください）

（requirements.txt がある場合はそれを利用してください）

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - あるいは repository に requirements.txt があれば:
     - pip install -r requirements.txt

3. 環境変数を設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くか、OS 環境変数を設定します。自動読み込みはデフォルトで有効です（下参照）。

4. データベース初期化
   - DuckDB ファイルを用いる場合:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - インメモリ:
     - from kabusys.data.schema import init_schema; init_schema(':memory:')

---

## 環境変数 (.env)

以下の環境変数を設定してください（必須・任意を明記）。`.env` / `.env.local` から自動で読み込まれます（プロジェクトルートは .git または pyproject.toml を基準に検出）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）

注意:
- 設定が不足していると Settings プロパティが ValueError を投げます。
- .env の読み込みロジックはシェル風の export KEY=val、引用符・コメント処理などに対応しています。

---

## 使い方（簡単な実行例）

以下は代表的なワークフローの Python コード例です。実行前に環境変数と DuckDB の初期化を行ってください。

1) DB 初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path を返す
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を走らせる
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

3) 特徴量作成（feature 作成）
```python
from datetime import date
from kabusys.strategy import build_features

# target_date を指定
n = build_features(conn, target_date=date(2024, 1, 5))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date

count = generate_signals(conn, target_date=date(2024, 1, 5))
print(f"signals written: {count}")
```

5) RSS ニュース収集
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes を渡すと記事 -> 銘柄紐付けを行う（有効銘柄セット）
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) J-Quants から日足を取得して保存（低レベル API）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from kabusys.data.schema import get_connection

# id_token を省略すると internal cache / refresh を利用
recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, recs)
```

---

## ディレクトリ構成

主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理
  - data/
    - __init__.py
    - schema.py                     — DuckDB スキーマ定義 / init_schema
    - jquants_client.py             — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py                   — 日次 ETL パイプライン
    - news_collector.py             — RSS 取得・raw_news 保存・銘柄抽出
    - stats.py                      — zscore_normalize 等
    - features.py                   — 再エクスポート
    - calendar_management.py        — market_calendar 管理 / 営業日判定
    - audit.py                      — 監査ログ用スキーマ
    - audit (途中定義) ...
  - research/
    - __init__.py
    - factor_research.py            — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py        — calc_forward_returns / calc_ic / factor_summary
  - strategy/
    - __init__.py
    - feature_engineering.py        — build_features
    - signal_generator.py           — generate_signals
  - execution/
    - __init__.py                   — （発注実装層、実装はここに統合予定）
  - その他テスト補助 / モジュール

（README 中では主要ファイルのみ列挙しています。実際のリポジトリにはさらに多くのユーティリティ・未掲載ファイルがあります）

---

## 開発者向けノート

- 自動 .env ロード
  - モジュール import 時にプロジェクトルートを探索して `.env`/.env.local を自動で読み込みます。テスト等で無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 環境（KABUSYS_ENV）
  - 有効値: development, paper_trading, live。settings.is_live / is_paper / is_dev が利用可能。
- DuckDB
  - init_schema(db_path) は必要なディレクトリを自動作成します。":memory:" を指定することでインメモリ DB を利用できます。
- 冪等性
  - DB 保存関数（save_*）は ON CONFLICT / DO UPDATE を用いて冪等に保存するよう設計されています。
- ネットワークの堅牢化
  - jquants_client はレート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ、ページネーション対応を実装しています。
  - news_collector は SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査）、gzip サイズチェック、XML パース防御（defusedxml）を実装しています。

---

ご不明点や追加したい機能（たとえば broker 結合・発注ロジックの実装、バックテストユーティリティ、CI 用のサンプルスクリプト等）があればお知らせください。README の内容はプロジェクトの進展に合わせて更新できます。