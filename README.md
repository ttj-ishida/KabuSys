# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された軽量ライブラリ群です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、カレンダー管理、監査ログなどを含む一連の処理を DuckDB を中心に実装しています。

以下はこのリポジトリの README（日本語）です。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール群です。

- J-Quants API からの株価/財務/カレンダー等の取得（差分取得・ページネーション対応）
- DuckDB によるデータ保存（スキーマ定義・冪等保存）
- 研究 (research) 層で得たファクターを用いた特徴量（features）の作成
- 正規化済みファクターと AI スコアを統合して売買シグナルを生成
- RSS によるニュース収集と銘柄コード紐付け
- 市場カレンダー管理（営業日判定など）
- ETL パイプライン／品質チェック／監査ログの仕組み

設計方針としては「ルックアヘッドバイアスの回避」「冪等性」「外部発注層への直接依存を持たない（分離）」を重視しています。

---

## 主な機能一覧

- data
  - J-Quants クライアント（ページネーション・トークン自動更新・リトライ・レート制限）
  - DuckDB スキーマ定義と初期化（init_schema）
  - ETL パイプライン（差分更新・backfill・品質チェック）
  - ニュース収集（RSS、SSRF 対策、記事正規化、銘柄抽出）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 統計ユーティリティ（Z スコア正規化）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy
  - 特徴量構築（build_features）：research の raw factor を正規化して features テーブルへ保存
  - シグナル生成（generate_signals）：features と ai_scores を統合して BUY/SELL シグナルを作成
- news
  - RSS 取得・パース・前処理・raw_news 保存・news_symbols 紐付け
- その他
  - 監査ログ（signal_events / order_requests / executions 等のスキーマ）
  - 設定管理（環境変数・.env 自動ロード）

---

## 必要条件 / 推奨環境

- Python 3.10+
- DuckDB（Python パッケージ）
- defusedxml（RSS パース用）
- （依存はコード上で標準ライブラリが多いため最小限。追加の外部パッケージがあれば requirements.txt を参照してください）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージ全体を開発モードでインストールしている想定なら:
# pip install -e .
```

※ 実行環境に合わせて必要な依存を追加してください。

---

## 環境変数（設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

重要な環境変数（必須）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意／デフォルト:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG` / `INFO` / ...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite（デフォルト: `data/monitoring.db`）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. レポジトリをクローン、仮想環境を作成して有効化
2. 必要パッケージをインストール（duckdb, defusedxml 等）
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml

# 環境変数を .env に保存
cp .env.example .env
# .env を編集してトークン等を設定

python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

---

## 使い方（主要な API とワークフロー）

Python からモジュールをインポートして使います。下記は代表的な操作例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants から差分取得して保存）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # デフォルトは本日（内部で営業日に調整）
print(result.to_dict())
```

- 特徴量の構築（features テーブルへ書き込み）
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import build_features
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, date(2026, 3, 20))
print(f"features upserted: {count}")
```

- シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.data.schema import get_connection
from kabusys.strategy import generate_signals
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total_signals = generate_signals(conn, date(2026, 3, 20))
print(f"signals written: {total_signals}")
```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効なコードセット（例：prices_daily の code を集めたもの）
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)
```

- カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

ログレベルは環境変数 `LOG_LEVEL` で制御してください。

---

## 推奨ワークフロー（日次）

1. DuckDB のスキーマ初期化（初回のみ）
2. calendar_update_job（カレンダーを先読み）
3. run_daily_etl（prices, financials, calendar を差分取得して保存）
4. run_news_collection（ニュースを収集して raw_news に登録）
5. build_features（features を生成）
6. generate_signals（signals を生成）
7. (execution 層があれば) signal_queue → orders → executions の送信と監査ログ記録

上記は分離されたステップになっているため、監視・再実行や部分実行が容易です。

---

## ディレクトリ構成

以下は主要ファイルとモジュールの概要（src/kabusys 以下）です。

- kabusys/
  - __init__.py
  - config.py  — 環境変数・.env 自動ロードと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 + 保存ユーティリティ）
    - news_collector.py      — RSS 収集・前処理・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — data 層の特徴量公開インターフェース
    - calendar_management.py — 市場カレンダー管理（営業日判定、更新ジョブ）
    - audit.py               — 監査ログ関連スキーマ（signal_events 等）
    - (その他: quality.py 等を想定)
  - research/
    - __init__.py
    - factor_research.py     — momentum/volatility/value のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化・フィルタリング）
    - signal_generator.py    — generate_signals（スコア計算・BUY/SELL 判定）
  - execution/               — 発注／約定関連の実装（空のパッケージ/拡張点）
  - monitoring/              — 監視・アラート用モジュール（拡張点）

各モジュールはドキュメント文字列と関数の説明を含み、業務ドメイン（DataPlatform.md, StrategyModel.md 等）の仕様に基づいています。

---

## 注意事項 / 補足

- セキュリティ
  - news_collector は SSRF や XML Bomb を考慮した実装になっています（SSRF ブロック、defusedxml、サイズ制限等）。
  - J-Quants クライアントはトークン自動更新・リトライ・レート制御を実装しています。
- 冪等性
  - jquants_client.save_*、news_collector.save_raw_news などは DB 側で ON CONFLICT を使った冪等保存を行います。
- ルックアヘッドバイアス
  - research/strategy の関数は target_date 時点のデータのみを参照するよう設計されています。
- テスト
  - ネットワーク I/O のある箇所（_urlopen 等）はテスト時にモックして差し替え可能な設計です。
- 実運用
  - ライブ運用時は KABUSYS_ENV=live を設定し、ログ/監視・失敗時の自動リカバリ等を整備してください。

---

もし README に追記したい内容（例: 実際の CI/CD、Docker イメージ、追加の使用例、API の詳細仕様や DataModel の図など）があれば教えてください。必要に応じて .env.example のテンプレートや運用手順書も作成します。