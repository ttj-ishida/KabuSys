# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
本リポジトリはデータ取得（J-Quants）、ETL、特徴量生成、シグナル作成、ニュース収集、監査ログ・スキーマ定義などを含むモジュール群を提供します。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

## 概要

KabuSys は以下の目的を持つコンポーネントを備えたプロジェクトです。

- J-Quants API から日足・財務・カレンダー等の市場データを取得し DuckDB に保存する ETL。
- 取得データを整形して特徴量（features）を構築する研究/運用向けモジュール。
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成する戦略ロジック。
- RSS フィードからニュースを収集して記事・銘柄紐付けを行うニュースコレクター。
- DuckDB のスキーマ（Raw / Processed / Feature / Execution / Audit）定義と初期化ユーティリティ。
- 各種ユーティリティ（Zスコア正規化、カレンダー管理、監査ログなど）。

設計方針の一例:
- ルックアヘッドバイアスを防ぐため、各処理は target_date 時点の情報のみ参照する。
- DuckDB を永続ストレージとして使用し、SQL と Python の組合せで処理を実装。
- API 呼び出しはレート制御・リトライ・トークン自動更新を備えたクライアントで安全に行う。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・リトライ・レート制限対応）
  - pipeline: 差分 ETL（prices / financials / calendar）と日次 ETL 実行
  - schema: DuckDB スキーマ定義 & init_schema()
  - news_collector: RSS 取得・前処理・記事保存・銘柄抽出
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - stats: zscore_normalize（クロスセクション正規化）
- research/
  - factor_research: momentum / volatility / value ファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・ファクター統計サマリ
- strategy/
  - feature_engineering.build_features: raw factor を合成して features テーブルへ保存
  - signal_generator.generate_signals: features + ai_scores を統合し signals を作成
- monitoring / execution / audit: 発注・ポジション・監査ログ用スキーマや雛形（モジュール群）

---

## 前提・依存関係

- Python 3.10 以上（型ヒントで | 演算子を使用）
- 必要な Python パッケージ（主にランタイム）:
  - duckdb
  - defusedxml
- その他: 標準ライブラリ（urllib, datetime, logging 等）

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発用にパッケージ化されていれば:
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数（設定）

自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

必須環境変数（Settings クラス参照）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu API のパスワード（発注連携を行う場合）
- SLACK_BOT_TOKEN : Slack 通知用ボットトークン（通知を使う場合）
- SLACK_CHANNEL_ID : Slack 送信先チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB 等の SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合は "1"

簡易 .env.example:
```
JQUANTS_REFRESH_TOKEN=xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをチェックアウト:
   ```bash
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境作成・依存パッケージインストール:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

3. 環境変数設定:
   - プロジェクトルートに `.env` を作成するか、環境変数をセットします（上記参照）。

4. DuckDB スキーマ初期化（Python REPL またはスクリプトで）:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # デフォルトパスと一致
   conn.close()
   ```

---

## 使い方（よく使う API）

以下は代表的な利用例です。すべて DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を渡して操作します。

1. DB の初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL 実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # date を指定しないと今日（自動で営業日に調整）
print(result.to_dict())
```

3. 個別 ETL ジョブ
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
from datetime import date
d = date(2026, 1, 20)

# 株価差分ETL
fetched, saved = run_prices_etl(conn, d)

# 財務差分ETL
fetched_f, saved_f = run_financials_etl(conn, d)

# カレンダー ETL
fetched_c, saved_c = run_calendar_etl(conn, d)
```

4. 特徴量構築（strategy.feature_engineering）
```python
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2026, 1, 20))
print(f"{count} 銘柄の features を保存しました")
```

5. シグナル生成（strategy.signal_generator）
```python
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, date(2026, 1, 20))
print(f"signals テーブルへ {n} 件書き込みました")
```

6. ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
# known_codes に有効な銘柄コードセットを渡すと記事→銘柄紐付けを試みます
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: 新規保存数}
```

7. J-Quants 生データ取得（低レベル）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from datetime import date
quotes = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,1,20))
```

8. スキーマ接続を取得（既存 DB に接続）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## ロギング / 実行モード

- KABUSYS_ENV 環境変数で実行モードを切り替え（development / paper_trading / live）。
- LOG_LEVEL でログレベルを指定（例: DEBUG）。
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから環境を明示的にセットしてください（テスト用途など）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとファイルの一覧（今回のコードベースから抜粋）:

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
      - stats.py
      - features.py
      - calendar_management.py
      - audit.py
      - audit... (続く)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/           # 発注・実行関連（未詳細実装ファイルあり）
    - monitoring/         # 監視用コード（空ファイルが存在）
    - ... その他モジュール

（上記は要約です。実際のリポジトリで詳細な階層を確認してください。）

---

## 開発のヒント / 注意点

- DuckDB のスキーマ初期化は冪等です。既存テーブルは上書きされません。
- J-Quants API のレート制限（120 req/min）とリトライロジックは jquants_client に実装済みです。高頻度での同時実行は避けてください。
- News collector は SSRF 対策や XML 安全パーサ（defusedxml）を使用していますが、外部 URL を使う際は環境ネットワークのポリシーに注意してください。
- generate_signals は features テーブルと ai_scores, positions 等を参照します。実運用ではポジション管理やリスク管理（注文ブロック等）との連携が必要です。
- 環境変数が不足すると settings のプロパティで ValueError が発生します。CI/デプロイ環境での変数管理に注意してください。

---

## お問い合わせ / 貢献

- バグ報告や機能要望は Issue を立ててください。
- プルリクエストは歓迎します。設計方針やテストを尊重した変更をお願いします。

---

この README は現行コードベース（src/kabusys/*.py）を基に作成しています。実行例や運用手順は環境・ポリシーに応じて調整してください。