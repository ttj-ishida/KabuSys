# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ロギングなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築に必要なデータ基盤と戦略層の共通処理を集約したライブラリです。主に以下の機能を提供します。

- J-Quants API を利用した株価・財務・カレンダー取得（レートリミット & リトライ対応、トークン自動リフレッシュ）
- DuckDB ベースのスキーマ定義と初期化（冪等）
- 日次 ETL パイプライン（差分取得・品質チェック）
- ニュース（RSS）収集と記事の正規化 / 銘柄抽出
- 研究向けファクター計算（Momentum / Volatility / Value）
- 特徴量の正規化（Z スコア）と features テーブルへの格納
- シグナル生成（複数コンポーネントの重み付け合成、売買・エグジットロジック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal → order → execution のトレース設計）

設計方針として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT 等）、テスト容易性（トークン注入等）を重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、レート制御、トークンリフレッシュ）
  - schema: DuckDB のテーブル定義と init_schema()
  - pipeline: 日次 ETL run_daily_etl() と個別 ETL ジョブ（prices/financials/calendar）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats: zscore_normalize（クロスセクション Z スコア）
  - features: zscore_normalize の再エクスポート
- research/
  - factor_research: momentum / volatility / value の計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、要約統計
- strategy/
  - feature_engineering.build_features: research の生ファクターを統合・正規化して features テーブルへ UPSERT
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナルを作成
- execution/ および monitoring/（拡張用プレースホルダ）
- config: 環境変数管理（.env 自動読み込み、必須変数チェック）

---

## 必須環境変数（例）

config.Settings が参照する主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（execution 層で使用）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

注意: パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（README 用の簡易例）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 必要な依存パッケージ（主要）

- Python >= 3.10（PEP 604 の union types (X | Y) を使用）
- duckdb
- defusedxml

（ネットワーク・HTTP は標準ライブラリ urllib を使用しています）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発インストール（プロジェクトに setup/pyproject がある場合）
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール（duckdb, defusedxml など）
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化の例（Python スクリプト / REPL）:
```python
from kabusys.data.schema import init_schema
# デフォルトパスを使う場合
conn = init_schema("data/kabusys.duckdb")
# またはメモリDBでテスト
# conn = init_schema(":memory:")
```

`.env.local` に開発専用の上書きを置けます。OS 環境変数が優先され、`.env.local` は上書き（override=True）で読み込まれます。

---

## 使い方（サンプル）

以下は主要なユースケースの簡単なサンプルコードです。

- 日次 ETL の実行（run_daily_etl）:
```python
from datetime import date
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（既に初期化済みならスキップして接続を取得）
conn = init_schema("data/kabusys.duckdb")

# 当日分の ETL を実行（id_token を省略するとモジュールキャッシュを利用）
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量の構築（build_features）:
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 5))
print(f"Upserted features for {count} symbols")
```

- シグナル生成（generate_signals）:
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
total_signals = generate_signals(conn, target_date=date(2024, 1, 5))
print(f"Generated {total_signals} signals (BUY+SELL)")
```

- RSS ニュース収集（run_news_collection）:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- J-Quants からの取得（直接利用例）:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings からリフレッシュトークンを取得して ID トークンを取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 実装上の注意点 / 設計メモ

- J-Quants クライアントは 120 req/min の制限に合わせて固定間隔スロットリングを行います。429/408/5xx は指数バックオフでリトライします。401 はトークン自動リフレッシュを行い1回リトライします。
- ETL は差分更新を行い、既存の最終取得日時から backfill（デフォルト 3 日）分を再取得して API の後出し修正を吸収します。
- 特徴量・シグナル生成はルックアヘッドバイアス防止のため target_date 時点までの情報のみを使用する設計です。
- DB 操作は冪等性（ON CONFLICT）やトランザクション（BEGIN / COMMIT / ROLLBACK）に配慮しています。
- RSS 収集は SSRF や XML Bomb を考慮した実装（スキーム検証、ホストのプライベート判定、defusedxml、受信サイズ上限）です。

---

## ディレクトリ構成

（主要ファイル / モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - (その他 data 関連モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/
      - (監視関連のプレースホルダ)
- pyproject.toml / setup.py (プロジェクトメタデータ、存在する想定)
- .env.example (設定テンプレート, README を参照)

---

## 開発・テスト時のヒント

- テストや CI で .env の自動読み込みを無効化したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB をインメモリで使えばテストが簡単です（db_path=":memory:"）。
- jquants_client のネットワーク呼び出しはテストでモック可能（_request / _urlopen 等を差し替え）。

---

## ライセンス / 貢献

この README はコードベースの簡易ドキュメントです。実運用する際はセキュリティ（API トークンの管理、実口座の誤発注防止）、監査要件、バックテスト・リスク管理ルールを十分に整備してください。貢献方法やライセンス表記はリポジトリのトップレベル README / LICENSE を参照してください。

---

必要に応じて、README にサンプル .env.example、より詳細な API 使用例、運用フロー（夜間バッチ、監視・アラート、Slack 通知）を追加できます。どの情報を拡充したいか教えてください。