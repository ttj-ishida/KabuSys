# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants や RSS 等からデータを取得して DuckDB に蓄積し、研究（factor 計算・探索）、特徴量生成、シグナル生成、発注監査などを一貫して扱えるよう設計されています。

主な設計方針:
- ルックアヘッドバイアス回避（各処理は target_date 時点のデータのみを利用）
- 冪等性（DB への保存は ON CONFLICT/UPSERT 等で上書きや重複防止）
- 外部依存を最小化（標準ライブラリ + 必要最低限の外部パッケージ）
- DuckDB を中心にオンマシンで高速に処理

バージョン: 0.1.0

---

## 機能一覧

- データ取得 / 保存（J-Quants API クライアント）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーのページネーション対応取得
  - レート制限・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得（バックフィル対応）、保存（冪等）、品質チェック統合
  - 日次 ETL エントリポイント（run_daily_etl）
- DuckDB スキーマ定義と初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブルとインデックス
- ニュース収集
  - RSS フィード収集、URL 正規化、SSRF 対策、raw_news 保存、銘柄抽出（4桁コード）
- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 特徴量エンジニアリング（feature_engineering）
  - 複数ファクターの統合、ユニバースフィルタ（最低株価・売買代金）、Z スコア正規化、clip、features テーブルへの UPSERT
- シグナル生成（signal_generator）
  - 正規化済み特徴量 + AI スコアを統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL シグナルの生成、signals テーブルへの冪等書き込み
- カレンダー管理（market calendar）
  - 営業日判定、前/次営業日取得、カレンダー更新ジョブ
- 監査ログ（audit）
  - signal → order_request → executions のトレース用スキーマ設計
- 汎用統計ユーティリティ（zscore_normalize など）

---

## 依存関係

必須（最低限）
- Python 3.10+（PEP 604 の union 型（|）や型ヒントを利用）
- duckdb
- defusedxml

インストール例（pip）:
```bash
pip install duckdb defusedxml
```

（パッケージを pip などで配布する場合は `pyproject.toml` / requirements を参照してください）

---

## セットアップ手順

1. リポジトリをクローンし、ソースを配置
2. Python 3.10+ 環境を用意
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定
   - `.env` または OS 環境変数を利用します。パッケージ起動時に自動でプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` を読み込みます。
   - 自動ロードを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
5. DuckDB 初期化（任意のパスでデータベースを作成）

必須の環境変数（Settings により参照・必須チェックされます）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabu API パスワード（発注関連を実装する際）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視/モニタリング用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化するフラグ（"1" 等）

サンプル .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=xxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（主要なワークフローと簡単なコード例）

以下は Python REPL やスクリプトからの利用例です。適宜 logging 設定を行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# またはメモリ DB
# conn = init_schema(":memory:")
```

2) 日次 ETL 実行（J-Quants からデータを取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量生成（feature engineering）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"upserted features: {n}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection(settings.duckdb_path)
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(results)
```

6) J-Quants API を直接使う（取得 → 保存）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(saved)
```

注意点:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。スレッドセーフ性やコネクション管理は呼び出し側で制御してください。
- ETL は可能な限り例外を個別に扱い、部分実行でも他処理を継続する設計です。戻り値や ETLResult を参照してエラー/品質問題を把握してください。

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内の主要モジュール一覧（src/kabusys）です。実際のリポジトリではさらにドキュメントや CI 設定等が存在する想定です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / Settings
    - data/
      - __init__.py
      - jquants_client.py          — J-Quants API クライアント（取得・保存）
      - news_collector.py          — RSS 収集・前処理・保存
      - schema.py                  — DuckDB スキーマ定義と init_schema
      - stats.py                   — zscore_normalize 等の統計ユーティリティ
      - pipeline.py                — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py     — 市場カレンダー管理（is_trading_day 等）
      - audit.py                   — 監査ログスキーマ（signal/order/execution トレース）
      - features.py                — public re-export（zscore_normalize）
    - research/
      - __init__.py
      - factor_research.py         — momentum/volatility/value ファクター計算
      - feature_exploration.py     — 将来リターン / IC / 統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py     — features テーブル作成（build_features）
      - signal_generator.py        — generate_signals（BUY/SELL ロジック）
    - execution/
      - __init__.py                — 発注層（将来的な実装箇所）
    - monitoring/                  — モニタリング関連（未表示 / 実装ファイル想定）

---

## 開発・拡張のヒント

- research モジュールは外部ライブラリ（pandas 等）に依存しない実装ですが、解析や可視化には pandas / matplotlib を利用すると便利です。
- 発注（execution）層は外部ブローカー API（kabuステーション等）との統合ポイントです。現在はスキーマとプレースホルダが用意されています。
- AI スコア等を統合する際は ai_scores テーブルを用い、generate_signals は該当テーブルを参照して最終スコアを計算します。
- テスト：config の自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。ユニットテストでは環境変数をモックして利用してください。

---

## ライセンス / 責任範囲

- 本プロジェクトは研究・学習用途を主眼に設計されています。実運用（実際の発注）に使用する場合は、入念なテスト・監査・法的・コンプライアンス確認が必要です。
- 実際の資金を投入する前にペーパートレードや十分なバックテストを行ってください。

---

質問や補足したい項目（例: 具体的な運用手順、追加のサンプル、テスト方針など）があれば教えてください。README に追記します。