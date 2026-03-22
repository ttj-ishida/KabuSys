# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのライブラリ群です。  
データ収集（J-Quants API / RSS）、データスキーマ（DuckDB）、リサーチ用ファクター計算、特徴量エンジニアリング、シグナル生成、バックテスト、ニュース収集・紐付けなど、戦略開発からバックテスト、運用に向けた一連の機能を提供します。

主な設計方針
- DuckDB を中心としたローカル／インメモリデータ管理
- ルックアヘッドバイアスの排除（各処理は target_date 時点のデータのみを使用）
- 冪等性（DB 書き込みは ON CONFLICT / トランザクションで安全に）
- 外部 API 呼び出しは data 層に集約（発注層や戦略層からの直接依存を回避）

---

## 機能一覧

- データ収集
  - J-Quants API クライアント（株価日足／財務データ／カレンダー）
  - RSS ベースのニュース収集（記事テキスト前処理・安全対策）
- データ管理
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（research.module）
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリー
- 特徴量エンジニアリング
  - 取得済みファクターの正規化（Zスコア）・ユニバースフィルタ・features テーブルへの保存
- シグナル生成
  - features + ai_scores を統合して final_score を計算、BUY / SELL シグナルを生成
  - Bear レジーム抑制、売買ルール（ストップロス等）
- バックテスト
  - シミュレータ（スリッページ・手数料を考慮）
  - 日次ループでのシグナル約定・ポートフォリオ管理
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, 勝率, Payoff Ratio）
  - CLI エントリポイント（モジュールとして実行可能）
- ニュース処理
  - RSS 取得、記事正規化、記事ID生成（URL 正規化 + SHA256）、DB 保存、銘柄抽出・紐付け

---

## 前提 / 必要要件

- Python 3.10 以上（型注釈で | 記法などを使用）
- 推奨パッケージ（最低限）
  - duckdb
  - defusedxml

（実行環境に応じて追加パッケージが必要になる場合があります。requirements.txt があればそれを使用してください。）

---

## セットアップ手順

1. リポジトリをクローン / 展開

   git clone <your-repo-url>
   cd <repo>

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージをインストール

   pip install --upgrade pip
   pip install duckdb defusedxml

   （プロジェクトで setup.py / pyproject.toml があれば `pip install -e .` を使用できます）

4. 環境変数設定（.env / .env.local）

   プロジェクトルートに `.env` を作成すると自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   例: `.env`（実運用では機密情報は安全に管理してください）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化

   Python REPL やスクリプトで次を実行して DB とテーブルを作成します:

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```

---

## 使い方（主な例）

### バックテスト（CLI）

バックテストはモジュールとして実行可能です。対象 DB は事前に prices_daily, features, ai_scores, market_regime, market_calendar 等を用意してください。

```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

主なオプション
- --start / --end: バックテスト開始／終了日（YYYY-MM-DD）
- --cash: 初期資金（デフォルト 10,000,000）
- --slippage: スリッページ率（デフォルト 0.001）
- --commission: 手数料率（デフォルト 0.00055）
- --max-position-pct: 1銘柄あたり最大比率（デフォルト 0.20）
- --db: 使用する DuckDB ファイルパス

### DuckDB スキーマ初期化（スクリプト）

```python
from kabusys.data.schema import init_schema
conn = init_schema(":memory:")  # インメモリ DB
# または init_schema("data/kabusys.duckdb")
# ... 使い終わったら
conn.close()
```

### ETL（データ取得）例

jquants_client と pipeline の関数を使って差分取得や保存を行えます。例:

```python
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
# run_prices_etl の引数で target_date, backfill_days, id_token を指定可能
# ここでは簡易な呼び出し例（詳細な呼び出しは pipeline モジュール参照）
# run_prices_etl(conn, target_date=date.today())
conn.close()
```

（pipeline モジュールには prices / financials / calendar の個別ジョブや総合ジョブが実装されています。詳しくはソース内 docstring を参照してください）

### ニュース収集（RSS）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
print(results)
conn.close()
```

### 特徴量構築 / シグナル生成 API

- 特徴量構築:

```python
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
conn.close()
```

- シグナル生成:

```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024, 1, 31))
conn.close()
```

### バックテストを Python API で実行

```python
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
# result.history / result.trades / result.metrics に結果が入る
conn.close()
```

---

## 設定（環境変数）

主に以下の環境変数を使用します（Settings クラス参照）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視等）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動で .env/.env.local をプロジェクトルートから読み込みます（有効なプロジェクトルートは .git または pyproject.toml を含む親ディレクトリで判定）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主なモジュールと概要です。

- src/kabusys/
  - __init__.py — パッケージ初期化（version 等）
  - config.py — 環境変数 / 設定管理（Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS ニュース取得・前処理・DB 保存・銘柄抽出
    - schema.py — DuckDB スキーマ定義・初期化（init_schema）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（差分取得・保存・品質チェック）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブルの構築（正規化・フィルタ）
    - signal_generator.py — final_score 計算と signals 生成
  - backtest/
    - __init__.py
    - engine.py — バックテストエンジン（run_backtest）
    - simulator.py — PortfolioSimulator / マークツーマーケット / 約定処理
    - metrics.py — バックテスト指標計算
    - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py — 将来用の SimulatedClock（現在未使用の拡張用）
  - execution/
    - __init__.py — 発注関連モジュールのエントリ（現状空）
  - monitoring/ — 監視・通知系モジュールを配置する想定（現状同梱なし）

（各ファイルには詳細な docstring／設計ノートが含まれているので、実装を確認しながら利用ください）

---

## 注意点 / 運用上の留意事項

- J-Quants API のレート制限・リトライ・トークンリフレッシュロジックは jquants_client に実装されています。ID トークンは内部でキャッシュします。
- DB 書き込みは基本的にトランザクションと ON CONFLICT（冪等）を使用していますが、本番運用ではバックアップ・監査ログを設けてください。
- news_collector は SSRF 対策・受信サイズ制限・XML パースの安全対策（defusedxml）を行っていますが、外部入力を取り扱うためログや運用監視を必ず行ってください。
- strategy 層（signal_generator）は features / ai_scores を参照します。AI スコアや regime 判定は外部処理で供給する想定です。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のみ有効です。live 実行時は特に設定ミスに注意してください。

---

## 貢献 / 開発

- コード中に豊富な docstring と設計コメントがあります。まずは各モジュールの docstring を確認してください。
- 単体テストや CI の導入を推奨します（特に ETL / API クライアント / ニュースパーサーはネットワークを伴うためモックが必要）。
- 外部シークレット（API トークン等）は .env で管理せず、Vault 等の安全ストレージを使うのが望ましいです。

---

この README はリポジトリ内のモジュール群（src/kabusys/*.py）の docstring と実装に基づいて作成しました。詳細な API の使い方やパラメータの説明は各モジュールの docstring を参照してください。質問や使い方の具体例が必要であれば、実行したいユースケース（例: ETL の自動化、バックテスト設定、ニュース収集ジョブの定期実行）を教えてください。