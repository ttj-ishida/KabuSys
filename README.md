# KabuSys

KabuSys は日本株向けの自動売買/データプラットフォームです。  
DuckDB を利用したデータレイヤ、研究（research）用ファクター計算、特徴量合成、シグナル生成、バックテストフレームワーク、および J-Quants / RSS などからのデータ取得ユーティリティを備えています。

この README はコードベース（src/kabusys）に基づく概要、機能、セットアップ、基本的な使い方、ディレクトリ構成をまとめたものです。

注意: 本プロジェクトは実運用を想定した設計（ルックアヘッドバイアスの回避、冪等性、トランザクション保護、外部 API のレート制御など）を含みます。実際の運用や API トークンの取り扱いには十分ご注意ください。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（例）
  - データベース初期化
  - データ取得（J-Quants）
  - ETL（差分更新）
  - 特徴量作成 / シグナル生成
  - バックテスト実行（CLI）
  - ニュース収集
- 環境変数（.env）
- ディレクトリ構成（主要ファイルの説明）
- トラブルシューティング（よくある問題）

---

## プロジェクト概要

KabuSys は以下の層から構成される日本株自動売買プラットフォームのコアライブラリです。

- Data Platform（DuckDB を用いた Raw / Processed / Feature / Execution 層）
- Research（ファクター計算、IC 計測、将来リターン計算）
- Strategy（特徴量合成、シグナル生成）
- Backtest（ポートフォリオシミュレータ、評価メトリクス、バックテストエンジン）
- Data collection（J-Quants API クライアント、RSS ニュース収集）
- 設定管理（.env 読み込み、環境変数ラップ）

設計の主眼は「ルックアヘッドバイアスの排除」「冪等性」「運用向けの堅牢性（トランザクション/ロールバック）」「テスト容易性」です。

---

## 主な機能一覧

- DuckDB スキーマ定義と初期化（kabusys.data.schema.init_schema）
- J-Quants API クライアント（取得・保存・リトライ・レート制御）
  - 株価日足、財務データ、マーケットカレンダー取得
- RSS を使ったニュース収集（SSRF 対策、圧縮制限、ID・正規化を伴う冪等保存）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
- シグナル生成（特徴量 + AI スコア統合、BUY/SELL 判定、signals テーブルへの日付単位置換）
- バックテストエンジン（インメモリ DuckDB に部分データをコピー、シミュレータ、メトリクス算出）
- バックテスト用 CLI（python -m kabusys.backtest.run）
- ETL パイプライン（差分取得・保存・品質チェックの仕組み）
- 設定管理（.env 自動読み込み / 必須 env チェック / 環境フラグ）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | などを使用）
- pip が利用可能

推奨手順（仮想環境を推奨）

1. 仮想環境作成・有効化
   - Unix/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   - 例:
     ```bash
     pip install duckdb defusedxml
     ```
   - （必要に応じてロギングやテスト用ライブラリを追加）

3. パッケージのインストール（開発モード）
   - リポジトリルートに setup があれば通常の pip install -e . を実行します。
   - ない場合は、PYTHONPATH に src を追加して import できるようにするか、プロジェクトルートで実行するか、ローカルにコピーしてください。

4. データベース初期化（DuckDB）
   - 初回はスキーマを作成します。例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - もしくはスクリプトで:
     ```bash
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
     ```

---

## 使い方（例）

以下は代表的な利用例です。各関数はモジュールから直接インポートして利用できます。

### 環境変数 / .env の取り扱い
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` と `.env.local` を自動読み込みします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env.local` が `.env` の値を上書きします（ただし OS の環境変数は保護されます）。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

オプション
- KABUSYS_ENV — development / paper_trading / live (デフォルト development)
- LOG_LEVEL — DEBUG/INFO/… (デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env の自動読み込みを無効化
- DUCKDB_PATH / SQLITE_PATH — デフォルト保存先

### 1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
conn.close()
```

### 2) J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

records = fetch_daily_quotes(date_from=None, date_to=None)  # 引数で絞る
saved = save_daily_quotes(conn, records)
print("saved price rows:", saved)
conn.close()
```

実務では ETL パイプライン（kabusys.data.pipeline）を使って差分更新を自動化します。

### 3) ETL（差分更新）の利用（パイプライン）
パイプラインは差分取得・保存・品質チェックを行います。API トークンを注入することも可能です（テスト向け）。
例（簡易）:
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl, ETLResult
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
res = run_prices_etl(conn, target_date=date.today())
print(res.to_dict())
conn.close()
```
（run_prices_etl などの詳細は pipeline モジュールを参照してください）

### 4) 特徴量作成 / シグナル生成
DuckDB 接続を渡して features テーブルを構築し、signals テーブルへシグナルを生成します。
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features, generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
t = date(2024, 1, 31)

# 特徴量の構築（features テーブルに upsert）
count = build_features(conn, t)
print("features upserted:", count)

# シグナル生成（signals テーブルに upsert）
signals_count = generate_signals(conn, t)
print("signals written:", signals_count)
conn.close()
```

### 5) バックテスト（CLI）
バックテスト用 CLI が提供されています。
```bash
python -m kabusys.backtest.run \
  --start 2023-01-04 --end 2023-12-29 \
  --cash 10000000 \
  --db data/kabusys.duckdb
```
出力は CAGR、Sharpe、Max Drawdown、勝率などのサマリを表示します。

プログラムから実行する場合は run_backtest を直接呼べます：
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
print(result.metrics)
conn.close()
```

### 6) ニュース収集
RSS から記事を収集して raw_news / news_symbols を更新します。
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", ...}  # 既知銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
conn.close()
```

---

## 環境変数（.env のキー例）

以下はコードから参照される主なキーの一覧です（.env.example 相当）。

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション:
- KABUSYS_ENV (development | paper_trading | live)  — 動作モード
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 で .env 自動読み込みを無効化
- KABUSYS_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db

.env の自動読み込み順:
OS 環境 > .env.local > .env

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 内の主要モジュールと役割の概略です。

- kabusys/
  - __init__.py  — パッケージ定義・バージョン
  - config.py  — 環境変数 / .env の読み込みと Settings 抽象
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - news_collector.py  — RSS 取得・解析・raw_news 保存・銘柄抽出
    - pipeline.py  — ETL パイプライン（差分取得・品質チェック）
    - schema.py  — DuckDB スキーマ定義と init_schema
    - stats.py  — zscore_normalize などの統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py  — 将来リターン, IC 計算, 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py  — features テーブル構築（正規化・フィルタ）
    - signal_generator.py  — features と ai_scores を統合して signals を生成
  - backtest/
    - __init__.py
    - engine.py  — run_backtest（インメモリコピー・日次ループ）
    - simulator.py  — PortfolioSimulator（擬似約定・スナップショット）
    - metrics.py  — バックテスト評価指標算出
    - run.py  — CLI エントリポイント
    - clock.py — シミュレート用時計（将来拡張用）
  - execution/  — (存在するがここでは空 __init__ のみ)
  - monitoring/ — 監視系（今回のコードベースでは公開ファイルなし）

（ファイル間の依存は概ね data → research → strategy → backtest の流れを想定）

---

## トラブルシューティング / 注意点

- 必須環境変数が未設定だと Settings のプロパティが ValueError を投げます。開発中は .env を用意してください。
- .env のパースはシェル互換の簡易実装を行っています。クォートやエスケープは一部サポートしていますが、複雑なケースは注意してください。
- J-Quants API のレート制御は実装されていますが、API 利用料金・利用制約は J-Quants 側の規約に従ってください。
- DuckDB のスキーマは初回実行で自動作成されますが、既存 DB を使う場合は init_schema を重複実行しないでください（init_schema は冪等です）。
- ニュース収集は外部アクセスを伴うため SSRF 対策やサイズ制限等の安全機構を備えています。プロダクションでは接続先・プロキシの挙動に注意してください。
- バックテストでは日次単位（終値 / 始値）を使ったシミュレーションです。分足シミュレーション等は現状未実装です。

---

この README はコードベースの主要点をまとめたものです。各モジュールの詳細な使用方法や引数仕様は該当する Python モジュールの docstring を参照してください。さらに補足やサンプルが必要であれば、どの機能について詳しく記載するか教えてください。