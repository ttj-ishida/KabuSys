# KabuSys — 日本株自動売買システム

軽量な研究〜本番までを想定した日本株向け自動売買フレームワークです。  
データ取得（J-Quants）、ETL、ファクター計算、シグナル生成、バックテスト、ニュース収集といった機能をモジュール化して提供します。

主な設計方針
- ルックアヘッドバイアス防止（計算は target_date 時点のデータのみを使用）
- DuckDB を中心としたローカル DB にデータを蓄積
- 冪等性（DB 挿入は ON CONFLICT/DO UPDATE 等を利用）
- 研究モジュールは発注層や外部 API に依存しない（安全に解析可能）

---

目次
- プロジェクト概要
- 機能一覧
- 要件
- セットアップ手順
- 環境変数 (.env) 例
- 使い方（主要ワークフロー）
  - DB 初期化
  - ETL（J-Quants からの差分取得）
  - 特徴量構築 / シグナル生成
  - バックテスト（CLI / プログラム）
  - ニュース収集
- 自動 .env 読み込みの振る舞い
- 主要ファイル・ディレクトリ構成
- 補足（設計メモ）

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコアライブラリです。  
主要コンポーネントは以下の通りです。

- data: J-Quants クライアント、ニュース収集、ETL パイプライン、DuckDB スキーマ、統計ユーティリティ
- research: ファクター計算・探索（モメンタム、ボラティリティ、バリュー等）
- strategy: 特徴量エンジニアリング、シグナル生成
- backtest: ポートフォリオシミュレーション、メトリクス、バックテスト実行用CLI
- execution / monitoring: 発注・監視層のためのパッケージ（将来的な拡張）

---

## 機能一覧

- J-Quants API クライアント（レート制限・自動リトライ・トークンリフレッシュ対応）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェックフック）
- ニュース収集（RSS、SSRF/サイズ/圧縮対策、記事→銘柄紐付け）
- ファクター計算（momentum / volatility / value 等）
- クロスセクション Z スコア正規化ユーティリティ
- シグナル生成（複数コンポーネントを重み付けして final_score を算出、BUY/SELL 生成）
- バックテストエンジン（模擬約定・スリッページ/手数料・ポジション管理・評価指標）
- バックテスト用 CLI（python -m kabusys.backtest.run）

---

## 要件

- Python 3.10 以上（型ヒントで PEP 604 の union 型を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib 等を使用

（プロジェクトの requirements.txt がある場合はそれを使用してください）

インストール例（仮）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
pip install -e .
```

---

## セットアップ手順（Quickstart）

1. リポジトリをクローン／配置する
2. 仮想環境を作成して依存をインストール（上記参照）
3. DuckDB の初期スキーマを作成
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
4. 環境変数を設定（.env をプロジェクトルートに配置）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
   - 任意: DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
5. データ取得／ETL を実行して prices_daily, raw_financials, market_calendar などを準備
6. 特徴量作成 → シグナル生成 → バックテスト の順で検証

---

## 環境変数 (.env) の例

プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

例 (.env.example):
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabu ステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境・ログ
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

必須の環境変数は config.Settings のプロパティから参照され、未設定の場合 ValueError が投げられます。

---

## 使い方（主要ワークフロー）

以下は代表的な利用例です。全てプログラムから呼び出すことも、バックテスト CLI を使うこともできます。

### DB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

### ETL（株価差分取得の例）
データ取得〜保存は kabusys.data.jquants_client と kabusys.data.pipeline を利用します。
（J-Quants の API トークンは環境変数に設定しておく）

例（簡易）:
```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
# target_date は取得終了日（通常は当日）
prices_fetched, prices_saved = run_prices_etl(conn, target_date=date.today())
```

run_prices_etl は差分取得ロジックを持ち、既存データを考慮して backfill を行います。

### 特徴量構築（features テーブル作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print(f"{count} 銘柄の features を生成しました")
```

- build_features は research の calc_* 関数から raw ファクターを取得し、ユニバースフィルタ・正規化・クリップを行い features テーブルへ UPSERT（トランザクションで日付単位の置換）します。

### シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)
print(f"生成したシグナル数: {total}")
```

- generate_signals は features と ai_scores を参照して final_score を計算し、BUY/SELL を signals テーブルへ書き込みます。Bear レジーム検出等のロジックを含みます。

### バックテスト（CLI）
用意された CLI を使ってバックテストを実行できます。

実行例:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

主要引数:
- --start / --end : バックテスト期間（YYYY-MM-DD）
- --cash : 初期資金
- --slippage / --commission : スリッページ・手数料率
- --max-position-pct : 1 銘柄あたり最大ポートフォリオ比率
- --db : DuckDB ファイルパス

プログラム的に run_backtest を呼ぶことも可能です（戻り値は BacktestResult）。

### ニュース収集（RSS）
RSS から記事を取得して raw_news に保存、銘柄紐付けする処理を提供しています。

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
print(results)  # {source_name: 新規保存件数, ...}
```

- fetch_rss は SSRF 対策、gzip サイズチェック、XML パーサの保護（defusedxml）等を行います。
- save_raw_news はチャンク挿入・INSERT ... RETURNING を使って実際に保存された記事の ID リストを返します。

---

## 自動 .env 読み込みの振る舞い

- 実行時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - OS 側に既にあるキーはデフォルトで保護されます
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

.env のパースはシェル風の export KEY=val やクォート内のエスケープに対応しています。

---

## 主要ディレクトリ / ファイル構成

（パッケージ内の主なファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 取得・記事保存・銘柄抽出
    - pipeline.py — ETL パイプライン（差分取得・品質チェック）
    - schema.py — DuckDB スキーマ初期化 / テーブル定義
    - stats.py — zscore 正規化ユーティリティなど
  - research/
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — 将来リターン / IC / サマリー
  - strategy/
    - feature_engineering.py — features テーブル作成
    - signal_generator.py — final_score 計算と signals 生成
  - backtest/
    - engine.py — run_backtest（全体ループ）
    - simulator.py — 擬似約定・PortfolioSimulator
    - metrics.py — バックテスト評価指標
    - run.py — CLI エントリポイント
  - execution/ (空の __init__.py がある構成)
  - monitoring/ (将来の監視関連)

---

## 補足 / 注意事項

- research モジュールは DB の prices_daily / raw_financials のみを参照し、実際の発注や外部 API 呼び出しはしません（安全に解析可能）。
- J-Quants クライアントはレート制限（120 req/min）に従う実装と自動トークン更新ロジックを備えています。
- 各 DB 保存関数は冪等性を重視しており、ON CONFLICT / DO UPDATE を利用しています。
- バックテストは本番 DB を直接汚さないよう、run_backtest 内でインメモリの DuckDB に必要データをコピーして実行します。
- Python の型ヒントや一部の機能は Python 3.10+ を前提としています。

---

質問や README の追加情報（例: CLI の詳細なオプション説明、開発フロー、テスト方法）をご希望であれば教えてください。README のサンプル .env.example ファイルやデプロイ手順のテンプレートも作成できます。