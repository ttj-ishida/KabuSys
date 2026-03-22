# KabuSys

日本株向けの自動売買システム用ライブラリ（研究・データパイプライン・シグナル生成・バックテストを含む）

---

## プロジェクト概要

KabuSys は、日本株のデータ取得、ファクター計算（research）、特徴量作成（feature engineering）、シグナル生成、バックテスト、さらにニュース収集や J-Quants API クライアント等を備えたモジュール群です。DuckDB をストレージとして使い、ETL → feature → signal → execution（シミュレータ/バックテスト）までのワークフローをライブラリとして提供します。

主な設計方針は以下の通りです：
- ルックアヘッドバイアスの排除（target_date 時点のデータのみ使用）
- DuckDB を用いた冪等なデータ保存（ON CONFLICT / トランザクション）
- API 呼び出しに対するレート制御・リトライ・トークン自動更新
- テスト容易性（自動 env ロードの抑制など）

---

## 機能一覧

- データ取得／保存
  - J-Quants API クライアント（株価日足 / 財務情報 / 市場カレンダー）
  - raw_news（RSS）収集と銘柄抽出
  - DuckDB スキーマ定義・初期化（init_schema）
- データ処理（ETL）
  - 差分取得（バックフィル対応）・保存（冪等）
  - 品質チェック（quality モジュールを想定）
- 研究用ファクター計算
  - Momentum / Volatility / Value 等のファクター算出
  - forward returns, IC（Spearman）や統計サマリー
- 特徴量エンジニアリング
  - ファクター正規化（Z-score）・ユニバースフィルタ適用・features テーブルへの UPSERT
- シグナル生成
  - features と ai_scores の統合による final_score 計算
  - Bear レジーム検知による BUY の抑制、SELL（エグジット）判定
  - signals テーブルへの冪等書き込み
- バックテスト
  - インメモリ DuckDB にデータをコピーして日次ループでシミュレーション
  - スリッページ・手数料モデルを組み込んだ擬似約定シミュレータ
  - パフォーマンス指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ユーティリティ
  - 環境変数/設定管理（.env の自動ロード、必須チェック）
  - 統計ユーティリティ（zscore_normalize 等）

---

## 必要要件

- Python 3.9+
- 必須ライブラリ（一部）:
  - duckdb
  - defusedxml
- （ネットワークアクセスが必要な機能を使う場合）インターネット接続、J-Quants のリフレッシュトークンなどの環境変数

実行に必要な追加パッケージはプロジェクトに応じて増える可能性があります。セットアップ時に pip install で明示します。

---

## セットアップ手順

1. リポジトリをクローン／取得し、開発用仮想環境を作成・有効化します。

   macOS / Linux:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):
   ```
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. パッケージと最低限の依存関係をインストールします（プロジェクトに requirements ファイルがある場合はそちらを使用してください）。

   ```
   pip install -e .
   pip install duckdb defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env`（及び任意で `.env.local`）を作成してください。
   - 自動ロード: パッケージは起動時にプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数が優先され、`.env.local` は上書きされます）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（主なもの。詳細は下部の「環境変数一覧」を参照）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID

4. DuckDB スキーマの初期化

   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")  # デフォルトは data/kabusys.duckdb
   ```

   もしくはコマンドラインから：
   ```
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

---

## 使い方（主な例）

### バックテスト（CLI）

DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を用意した上で実行します。

```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

出力にバックテストの主要指標が表示されます。

### ETL：株価・財務データ取得（スクリプト例）

J-Quants API を使って差分取得→保存を行う例（要 JQUANTS_REFRESH_TOKEN）

```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
result = run_prices_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

（run_prices_etl の引数には id_token / date_from / backfill_days を渡すことができます）

### ニュース収集（RSS）と銘柄紐付け

```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄集合を用意
res = run_news_collection(conn, known_codes=known_codes)
print(res)
conn.close()
```

### 研究用 API（ファクター計算・IC 計算）

Python REPL／スクリプトから呼び出せます。

```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic

conn = init_schema("data/kabusys.duckdb")
date0 = date(2024, 1, 31)
moms = calc_momentum(conn, date0)
fwd = calc_forward_returns(conn, date0, horizons=[1,5,21])
ic = calc_ic(moms, fwd, factor_col="mom_1m", return_col="fwd_5d")
print("IC:", ic)
conn.close()
```

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)：J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須)：kabuステーション API パスワード（execution を使う場合）
- KABU_API_BASE_URL：kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)：Slack 通知用トークン
- SLACK_CHANNEL_ID (必須)：Slack 通知先チャンネル ID
- DUCKDB_PATH：デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite のパス（data/monitoring.db）
- KABUSYS_ENV：実行環境（development | paper_trading | live）
- LOG_LEVEL：ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD：1 にすると .env 自動ロードを無効化

※ Settings は kabusys.config.Settings として提供されています。環境変数が未設定のときは ValueError が発生します（必須項目）。

---

## ディレクトリ構成

主要ファイル・モジュールとその役割：

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の管理（.env 自動ロード、Settings クラス）
  - data/
    - jquants_client.py : J-Quants API クライアント（取得・保存ユーティリティ含む）
    - news_collector.py : RSS 収集・記事正規化・DB 保存・銘柄抽出
    - schema.py : DuckDB スキーマ定義・init_schema
    - pipeline.py : ETL ワークフロー（差分取得・保存・品質チェック）
    - stats.py : z-score 正規化などの統計ユーティリティ
  - research/
    - factor_research.py : Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py : forward returns / IC / 統計サマリー等
  - strategy/
    - feature_engineering.py : raw factor を正規化・合成して features に保存
    - signal_generator.py : features と ai_scores を統合して signals を生成
  - backtest/
    - engine.py : バックテスト実行ループ（in-memory copy + 日次ループ）
    - simulator.py : ポートフォリオシミュレータ（擬似約定、スリッページ、手数料）
    - metrics.py : バックテスト指標計算
    - run.py : CLI エントリポイント（python -m kabusys.backtest.run）
  - execution/ (発注実装を置くプレースホルダ)
  - monitoring/ (監視・メトリクス関連を置くプレースホルダ)

簡易ツリー（抜粋）:

```
src/kabusys/
├─ config.py
├─ data/
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ schema.py
│  ├─ pipeline.py
│  └─ stats.py
├─ research/
│  ├─ factor_research.py
│  └─ feature_exploration.py
├─ strategy/
│  ├─ feature_engineering.py
│  └─ signal_generator.py
├─ backtest/
│  ├─ engine.py
│  ├─ simulator.py
│  ├─ metrics.py
│  └─ run.py
└─ execution/
```

---

## 開発・運用のヒント

- .env の自動ロードは config.py 内で行われます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで自動読み込みを抑制できます。
- DuckDB スキーマは冪等に作成されるため、何度でも init_schema を呼べます。既存 DB を壊さずに初期化可能です。
- J-Quants API 呼び出しはレート制御（120 req/min）とリトライ、401 自動リフレッシュを組み込んでいます。大量取得時はレート上限に注意してください。
- RSS 収集は SSRF や XML Bomb 対策を施していますが、公開フィードを登録する際は信頼できるソースのみを推奨します。
- バックテストは原則として DuckDB 上のデータを start_date - 300 日分程度コピーして実行します（本番テーブルを汚染しないため）。大規模実行ではメモリに注意してください。
- ロギングは各モジュールで logger を利用しています。ログレベルは環境変数 LOG_LEVEL で制御できます。

---

この README はコードベースの主要な使い方と構成を簡潔にまとめたものです。詳しい API（関数引数や戻り値の仕様）は各モジュールの docstring を参照してください。何か追加したいセクションや具体的な使用例（たとえば ETL の完全な実行手順など）があれば教えてください。