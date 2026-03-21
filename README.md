# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB をデータストアに用い、J-Quants などからマーケットデータ・財務データ・ニュースを取得して ETL → 特徴量作成 → シグナル生成までをサポートします。ライブラリは研究（research）、データ（data）、戦略（strategy）、発注/実行（execution）層に分かれた設計になっています。

## 特徴（Overview / Features）
- データ取得
  - J-Quants API クライアント（株価日足・財務・マーケットカレンダー） — レート制限・リトライ・トークン自動リフレッシュ対応
  - RSS ベースのニュース収集（SSRF対策・トラッキング除去・gzip対応）
- 永続化
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - 生データ → 整形済みデータ → 特徴量 までのレイヤードスキーマ（冪等保存）
- ETL パイプライン
  - 差分更新、バックフィル、品質チェック（quality モジュール呼び出し）
  - 市場カレンダー先読みと営業日調整
- 研究 / 戦略ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - クロスセクション Z スコア正規化ユーティリティ
  - シグナル生成（複数コンポーネントスコアの重み付け合成、BUY/SELL 生成、Bear フィルタ、エグジット判定）
  - 特徴量構築（features テーブルへの日次 UPSERT）
  - 研究用ユーティリティ（forward returns, IC, summary）
- セキュリティ / 信頼性
  - RSS の XML パースに defusedxml を使用、SSRF 転送先検査、レスポンスサイズ上限
  - API 呼び出しに固定間隔レートリミッタ、指数バックオフリトライ
- 監査（audit）設計（監査ログ用 DDL が用意され、UUID 連鎖でトレース可能）

---

## 必要な環境・前提
- Python 3.10 以上（型注釈で PEP 604 の union 型などを使用）
- 主要な依存ライブラリ（代表例）
  - duckdb
  - defusedxml
- J-Quants API のリフレッシュトークン等の環境変数（下記参照）

（プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを参照してください。ここに示したのは代表的な依存のみです）

---

## 環境変数（必須 / 任意）
設定は .env /.env.local または OS 環境変数から読み込まれます（読み込み順: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（Settings.require でチェックされるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知を使う場合

任意（デフォルトあり）
- KABUSYS_ENV — `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（デフォルト: data/monitoring.db）

例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（Setup）
1. リポジトリをクローン / 作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   - 実運用では pyproject.toml / requirements.txt を用意し、そこからインストールしてください。

4. 環境変数を設定（.env をプロジェクトルートに配置することを推奨）
   - 例は前節を参照

5. DuckDB スキーマ初期化（最初の一度だけ）
   - Python REPL やスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # :memory: も可能
   conn.close()
   ```

---

## 使い方（Usage）
以下は代表的な操作例です。実際のアプリケーションではログやエラー処理、スケジューラ（cron / Airflow 等）と組み合わせて運用します。

- DuckDB の初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得と品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- 特徴量作成（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 10))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date(2024, 1, 10), threshold=0.60)
print(f"signals written: {num}")
```

- ニュース収集ジョブ（RSS → raw_news / news_symbols）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 保持銘柄等、抽出に使う有効コードセット
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)
```

- J-Quants から株価を直接取得して保存する（テスト用）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,10))
saved = jq.save_daily_quotes(conn, records)
print(saved)
```

---

## ディレクトリ構成（抜粋）
主要モジュールと役割を一覧にします（実際のプロジェクトルートは src/kabusys 以下にパッケージが置かれています）。

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存）
    - news_collector.py              — RSS ニュース収集・保存・紐付け
    - schema.py                      — DuckDB スキーマ定義・初期化
    - stats.py                       — zscore_normalize 等の統計ユーティリティ
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py         — マーケットカレンダー管理
    - features.py                    — data.stats の再エクスポート
    - audit.py                       — 監査ログ用 DDL
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / ボラティリティ / バリューの計算
    - feature_exploration.py         — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — ロー→特徴量の合成と正規化（build_features）
    - signal_generator.py            — final_score 計算と signals 生成（generate_signals）
  - execution/                       — 発注 / ブローカー連携など（名前空間用）
  - monitoring/                      — モニタリング関係（SQLite 連携等、将来拡張）

---

## 設計上のポイント / 運用メモ
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テストや特殊用途では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- J-Quants API 呼び出しは内部でレート制限（120 req/min）を守るように実装されています。大規模取得やバッチスケジュール時は注意してください。
- DuckDB のスキーマは冪等（存在チェック → CREATE IF NOT EXISTS）なので、複数回 init_schema を実行しても安全です。
- シグナル生成は features / ai_scores / positions / prices_daily に依存します。ルックアヘッドバイアスを避けるため、target_date 時点のデータのみを参照する設計です。
- NewsCollector は外部 RSS の構造差やエンコーディング差に強い実装を目指していますが、ソースごとに前処理ルールを調整する必要が出る場合があります。
- 実際に発注を行う場合は execution 層と kabuステーション等ブローカー API の実装を組み合わせ、十分なテスト・リスク管理を行ってください。

---

## 貢献 / 変更履歴
- 開発中の README です。機能追加や設計変更に伴い README を更新してください。
- 実装に関する議論やバグ報告は issue を立ててください。

---

この README はコードベース（src/kabusys 以下）に基づいて作成しました。追加したい使用例やデプロイ手順（systemd / Docker / Airflow での運用など）があれば追記します。