# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ実装）。  
データ取得・ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ・スキーマ管理などを含むモジュール群を提供します。

## プロジェクト概要
KabuSys は、J-Quants 等の外部データソースからマーケットデータと財務データを取得し、DuckDB に保存して処理（ETL）を行い、研究（research）で構築した生ファクターを正規化・合成して戦略用特徴量を作成、さらに最終スコアに基づく売買シグナルを生成するためのライブラリ群です。発注層（broker API）への直接依存を持たない層設計になっています。

主な設計方針：
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- 冪等性（DB への保存は ON CONFLICT / トランザクションで安全）
- API レート制御・リトライ・トークン自動更新
- DuckDB を中心とした高速分析ワークフロー

## 機能一覧
- データ取得
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - RSS ベースのニュース収集（前処理・URL 正規化・銘柄抽出）
- ETL パイプライン
  - 差分取得（バックフィル含む）、保存、品質チェック
  - 日次 ETL エントリポイント（run_daily_etl）
- スキーマ管理
  - DuckDB 用スキーマ定義・初期化（init_schema）
- 研究用モジュール
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- 特徴量エンジニアリング
  - cross-sectional Z スコア正規化、ユニバースフィルタ、features テーブルへ保存
- シグナル生成
  - 複数コンポーネントスコアを重み付けして final_score を算出
  - Bear レジーム検出による BUY 抑制、SELL（エグジット）判定
  - signals テーブルへの冪等書き込み
- カレンダー管理（営業日判定、next/prev/get_trading_days）
- 監査ログ（signal_events / order_requests / executions などの DDL）
- 汎用ユーティリティ（Z スコア正規化、統計関数）

## 動作環境・依存関係
- Python 3.10+
- 必要な Python パッケージ（主要）
  - duckdb
  - defusedxml
- （J-Quants を使う場合）ネットワークアクセスが必要

例: requirements.txt（プロジェクトに合わせて調整してください）
```
duckdb>=0.7
defusedxml
```

## セットアップ手順
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt
   # 開発時またはパッケージ化がある場合:
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（config モジュールによる自動ロード。CWD に依存せず __file__ からプロジェクトルートを判別します）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID
設定例（.env）:
```
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

設定の参照は `from kabusys.config import settings` を使います（settings.jquants_refresh_token 等）。

## 使い方（主要ユースケース）
以下は最小限の使用例です。実際はログ設定・エラーハンドリング等を適宜追加してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ':memory:' も利用可
```

2) 日次 ETL 実行（市場カレンダー / 株価 / 財務 データの差分取得）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量生成（features テーブルの構築）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルの書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date.today(), threshold=0.60)
print(f"signals written: {total}")
```

5) ニュース収集ジョブ（RSS -> raw_news / news_symbols）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出用に検証済みコードセットを渡す（None なら抽出をスキップ）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)
```

6) J-Quants からのデータ取得（低レベル API）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
print(len(records))
```

### ログ／環境モード
- KABUSYS_ENV は `"development" | "paper_trading" | "live"` のいずれか。settings.is_dev / is_paper / is_live で判定可能。
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"

## ディレクトリ構成
リポジトリ内の主要なモジュール構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント
    - news_collector.py              — RSS ニュース収集
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - schema.py                      — DuckDB スキーマ定義 / init_schema
    - stats.py                       — 統計ユーティリティ（zscore_normalize）
    - features.py                    — features 再エクスポート
    - calendar_management.py         — 市場カレンダー管理
    - audit.py                       — 監査ログ用 DDL (signal_events 等)
    - (その他: quality, audit helpers などを想定)
  - research/
    - __init__.py
    - factor_research.py             — momentum / volatility / value の計算
    - feature_exploration.py         — 将来リターン / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         — features を生成して保存
    - signal_generator.py            — final_score 計算・signals 生成
  - execution/                       — 発注実装（空のパッケージ/拡張ポイント）
  - monitoring/                      — 監視・モニタリング用モジュール（想定）

（実際のファイルは src/kabusys 以下に多数含まれます。上記は主要モジュールの一覧です。）

## 開発メモ / 注意点
- DuckDB を利用しているため、分析クエリは可能な限り SQL で記述されています。大量データの読み書きはバルク操作を用い、冪等性を担保しています。
- J-Quants API はレート制限があるため、jquants_client 内で固定間隔スロットリングと再試行ロジックを実装しています。
- ニュース収集では SSRF / XML Bomb 等のセキュリティ対策（スキーム検証、プライベートホスト排除、defusedxml、受信サイズ制限）を組み込んでいます。
- テストや一時実行のため、env 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を用意しています。

---

ご要望があれば、README にサンプル .env.example、より詳しい API 使用例（関数シグネチャ一覧）、または運用手順（cron / Airflow での定期実行例）を追加できます。どの情報を優先して追記しますか？