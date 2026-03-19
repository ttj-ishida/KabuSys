# KabuSys

日本株自動売買基盤（KabuSys）の Python パッケージ README（日本語）

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL・特徴量作成・シグナル生成・発注/監査までを想定したモジュール群を提供するライブラリです。  
主な設計方針は以下の通りです。

- J-Quants API を用いた市場データ取得（株価日足・財務・市場カレンダー）
- DuckDB を用いたローカルデータベース（冪等性・トランザクション重視）
- 研究（research）と運用（strategy/execution）を分離し、ルックアヘッドバイアスを排除
- RSS ニュース収集および銘柄紐付けのサポート
- ログ・監査（audit）・監視（monitoring）を考慮した設計

本リポジトリはライブラリ本体（src/kabusys/*）を含み、ETL／特徴量作成／シグナル生成等のユーティリティを提供します。

---

## 機能一覧

主要機能（モジュール別）

- config
  - .env / 環境変数の自動読み込み、必須値チェック（JQUANTS_REFRESH_TOKEN 等）
- data
  - jquants_client: J-Quants API クライアント（レート制御・リトライ・ページネーション・保存関数）
  - schema: DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution 層）
  - pipeline: 日次 ETL パイプライン（差分取得・backfill・品質チェック）
  - news_collector: RSS フィードからニュース取得・前処理・DB保存・銘柄抽出
  - calendar_management: JPX カレンダー管理、営業日判定・次/前営業日取得
  - features / stats: Z スコア正規化など統計ユーティリティ
  - audit: 発注〜約定のトレーサビリティ用テーブル定義・初期化
- research
  - factor_research: モメンタム／バリュー／ボラティリティ等のファクター計算（prices_daily/raw_financials 参照）
  - feature_exploration: 将来リターン計算・IC（Information Coefficient）・統計サマリー
- strategy
  - feature_engineering.build_features: 生ファクターを正規化・合成し features テーブルへ保存
  - signal_generator.generate_signals: features + ai_scores を統合して BUY/SELL シグナルを生成（signals テーブルへ保存）
- execution / monitoring（骨組み／初期化用のテーブルが含まれます）

主な設計上の注意点:
- DuckDB 上の SQL と純 Python の組合せで計算を実装（外部ライブラリへの依存を最小化）
- API レート制御、リトライ、トークン自動リフレッシュ
- DB 操作は可能な限り冪等（ON CONFLICT / トランザクション）を採用

---

## 要件

- Python 3.10 以上（typing の `|` 合成等を利用）
- 主要パッケージ（例）
  - duckdb
  - defusedxml

簡易インストール例:
pip を使う場合:
```
python3 -m pip install "duckdb" "defusedxml"
```

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存パッケージをインストール
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```
3. 環境変数の用意
   - プロジェクトルートに `.env` または `.env.local` を配置することで自動読み込みされます（config モジュールが .git / pyproject.toml を探索して自動ロード）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます（テスト用途など）。
4. 必須環境変数（.env に設定する例）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_token
   - SLACK_CHANNEL_ID=your_slack_channel
   - （任意）DUCKDB_PATH=data/kabusys.duckdb
   - （任意）SQLITE_PATH=data/monitoring.db
   - （任意）KABUSYS_ENV=development|paper_trading|live
   - （任意）LOG_LEVEL=DEBUG|INFO|...

example .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secretpassword
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化します:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
   conn.close()
   ```

---

## 使い方（代表的な操作例）

以下は主要な操作例です。実運用ではログ設定や例外処理、定期実行（cron / Airflow 等）を組み合わせてください。

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn を使ってさらに操作できます
conn.close()
```

- 日次 ETL 実行（J-Quants から市場カレンダー・株価・財務を差分取得して保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
conn.close()
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 上場銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)
conn.close()
```

- 特徴量構築（features テーブルへ日次 upsert）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 10))
print(f"upserted features: {count}")
conn.close()
```

- シグナル生成（features + ai_scores → signals テーブル）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2024, 1, 10))
print(f"signals written: {total_signals}")
conn.close()
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
conn.close()
```

注意:
- J-Quants API 呼び出しには `JQUANTS_REFRESH_TOKEN` が必須です。config.Settings が未設定を検出すると ValueError を投げます。
- ETL／API 呼び出しはネットワークに依存します。ログと例外処理を適切に行ってください。

---

## 主要環境変数

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — 通知用 Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — 通知先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development|paper_trading|live（デフォルト development）
- LOG_LEVEL (任意) — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（テスト用）

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイルと概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理・自動読み込みロジック（.env, .env.local の読み込み）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB 保存ユーティリティ
    - news_collector.py — RSS 収集・前処理・raw_news 保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema()
    - pipeline.py — 日次 ETL（run_daily_etl 等）
    - stats.py — zscore_normalize 等統計ユーティリティ
    - features.py — zscore_normalize の再エクスポート
    - calendar_management.py — market_calendar 管理と営業日ユーティリティ
    - audit.py — 監査ログ用テーブル定義（signal_events, order_requests, executions 等）
    - (その他 execution/monitoring 関連の補助モジュール)
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティ等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — 生ファクターを正規化して features テーブルへ保存
    - signal_generator.py — final_score 計算、BUY/SELL シグナル生成 → signals テーブルへ保存
  - execution/ (骨組み)
  - monitoring/ (骨組み)

※ 各モジュールのドキュメントや docstring に実装意図・制約・設計方針が詳細に記載されています。実装を拡張する際はそちらを参照してください。

---

## 開発メモ / 注意点

- DB 操作はトランザクションと冪等性（ON CONFLICT）を前提としています。スキーマ設計の制約（DuckDB のバージョン依存）に注意してください。
- research と production ロジックは分離されています。研究環境で得た生ファクターを features 作成処理へ取り込むフローが想定されています。
- ネットワーク／API 呼び出し部はリトライとレート制御を実装していますが、実運用ではモニタリングとアラートを設定してください。
- security: news_collector には SSRF・XML Bomb・サイズ上限など多数の防御策が入っています。外部フィードを追加する場合はホワイトリストや検証を強化してください。

---

## 貢献 / ライセンス

- 貢献方法（Issue / PR）を歓迎します。設計方針に従ってユニットテスト・型チェックを追加してください。
- ライセンス情報はリポジトリの LICENSE を参照してください（この README には含めていません）。

---

README の内容や使用例の追加・修正希望があれば、利用シナリオ（ETL スケジュール、シグナル→発注の運用フローなど）を教えてください。それに合わせて具体的な実行手順やベストプラクティスを追記します。