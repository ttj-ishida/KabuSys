# KabuSys

日本株向けの自動売買システム（ライブラリ）。データ収集・ETL、特徴量作成、シグナル生成、ニュース収集、監査・実行レイヤまでを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを防ぐため、すべての処理は target_date 時点のデータのみを用いる。
- DuckDB を中心に冪等（idempotent）かつトランザクション志向でデータ永続化を行う。
- 外部 API 呼び出し（J-Quants 等）はレート制御・リトライ・トークン自動更新等を備える。
- Research 層は本番発注ロジックに依存しない（解析専用に設計）。

---

## 機能一覧

- データ収集（J-Quants）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - トークン自動更新、レートリミット、リトライロジック

- ETL パイプライン
  - 差分更新（最終取得日からの差分フェッチ）、バックフィル吸収
  - 品質チェック（欠損・スパイク等。quality モジュール）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）

- 特徴量（Feature）生成
  - research 層で計算した生ファクターを正規化・合成して `features` テーブルへ保存（build_features）

- シグナル生成
  - 正規化済みファクターおよび AI スコアを統合して final_score を算出、BUY/SELL シグナルを生成して `signals` テーブルへ格納（generate_signals）
  - Bear レジーム抑制、ストップロス等のエグジット判定を実装

- ニュース収集
  - RSS フィード収集、URL 正規化、SSRF 対策、gzip/サイズ制限、記事の DB 保存、銘柄抽出と紐付け

- 研究（Research）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリなど（外部ライブラリに依存しない実装）

- 監査（Audit）
  - シグナル→発注→約定のトレーサビリティを担保する監査テーブル群

---

## 必要条件（推奨）

- Python 3.10+
- DuckDB
- defusedxml

（パッケージ要件ファイルがある場合はそちらを参照してください。例: requirements.txt / pyproject.toml）

例（ローカルで動かす最低限）:
pip install duckdb defusedxml

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします（プロジェクトに requirements.txt や pyproject.toml があればそれを利用）。
   - pip install duckdb defusedxml
   - （その他、プロジェクトに合わせて追加の依存が必要）

3. 環境変数を設定します。プロジェクトルートに `.env` を置くと自動で読み込まれます（自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

必須の環境変数（ライブラリ内で _require() によりチェックされます）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード（発注連携を使う場合）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知連携を使う場合）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（通知連携を使う場合）

任意・デフォルト値あり:
- KABUSYS_ENV           : execution 環境 ("development" | "paper_trading" | "live"), デフォルト "development"
- LOG_LEVEL             : ログレベル ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"), デフォルト "INFO"
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite path for monitoring (デフォルト: data/monitoring.db)

サンプル .env:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単なコード例）

以下は典型的なワークフロー例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ":memory:" を使うことも可能
```

2) 日次 ETL（J-Quants からデータ取得→保存→品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を与えなければ今日を基準に実行
print(result.to_dict())
```

3) 特徴量の作成（target_date を指定）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, date(2025, 1, 10))
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals

total = generate_signals(conn, date(2025, 1, 10))
print(f"signals generated: {total}")
```

5) ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

6) J-Quants トークンを明示的に取得する場合
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # JQUANTS_REFRESH_TOKEN が env にある前提
```

ログや挙動の調整には環境変数（LOG_LEVEL, KABUSYS_ENV）を利用してください。

---

## 自動 .env ロードについて

- パッケージは起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動で読み込みます。
- 読み込み優先順位: OS 環境 > .env.local > .env
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパースはシェル形式（export KEY=val、クォート、コメント等）に対応しています。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src/kabusys 以下に実装がまとまっています。主要なファイル・モジュール:

- src/kabusys/
  - __init__.py
  - config.py        — 環境変数 / 設定管理（自動 .env ロード、Settings クラス）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得＋保存ユーティリティ）
  - news_collector.py — RSS ニュース取得・保存・銘柄抽出
  - schema.py         — DuckDB スキーマ定義 / init_schema / get_connection
  - pipeline.py       — ETL パイプラインの主要ロジック（run_daily_etl 等）
  - calendar_management.py — 市場カレンダー管理ユーティリティ
  - features.py       — data.stats の再エクスポート
  - stats.py          — z-score 等の統計ユーティリティ
  - audit.py          — 監査ログ（signal_events, order_requests, executions）DDL
  - その他（quality 等は別ファイルとして想定）
- src/kabusys/research/
  - __init__.py
  - factor_research.py — momentum/value/volatility 等のファクター計算
  - feature_exploration.py — 将来リターン計算・IC・統計サマリ
- src/kabusys/strategy/
  - __init__.py
  - feature_engineering.py — ファクター統合・正規化 → features テーブルへ
  - signal_generator.py    — final_score 計算 → signals テーブルへ
- src/kabusys/execution/
  - __init__.py
  - （発注・約定処理、ブローカー連携はここに実装予定）
- その他: monitoring / utils / examples 等が存在する想定

（上記はコードベースの現状を抜粋したもので、実際のリポジトリには追加ファイルやサブパッケージがある可能性があります）

---

## 開発・運用上の注意点

- DuckDB はシングルファイル DB を想定しているため、複数プロセスで同一ファイルへの同時書き込みを行う場合は排他制御に注意してください。
- J-Quants API のレート制限（120 req/min）に従うため、fetch 関数は内部でレート制御を行います。大量取得時は API 制限に注意してください。
- ニュース収集は外部 URL に依存するため、SSRF 対策や受信サイズ制限、XML パース例外処理が組み込まれていますが、外部フィードの変化により一時的に失敗することがあります。
- 本リポジトリに含まれる取引ロジック（発注・実行）は慎重に検証してください。実口座で使用する場合は paper_trading で十分にテストを行い、リスク管理（ストップロス、ポジション制限等）を実装してください。

---

## 参考・拡張

- StrategyModel.md / DataPlatform.md 等の設計ドキュメントに準拠した実装が行われています（リポジトリ内にあれば参照してください）。
- 監査ログ（audit.py）や execution 層は、ブローカー API との連携に合わせて拡張・カスタマイズしてください。
- tests / CI による自動検証を追加することで安全性を高めてください。

---

ご不明点や README に追加したい内容（例: CI、具体的な SQL スキーマ図、環境ごとの運用手順など）があれば教えてください。README をさらにプロジェクトの実運用向けに拡張できます。