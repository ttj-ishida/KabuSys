# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（バックテスト／ETL／特徴量計算／シグナル生成／ニュース収集）。  
このリポジトリは、データ取得（J-Quants）→ データ整備（DuckDB スキーマ）→ 研究用ファクター計算 → 特徴量生成 → シグナル生成 → バックテスト の一連のワークフローを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを使用）
- DuckDB を中心としたローカル DB によるデータ管理（冪等性を重視）
- API 呼び出しはレート制限・リトライ・トークン自動更新に対応
- 研究用コード（research）と運用用コード（strategy / execution / backtest）を分離

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（よく使うコマンド / API 呼び出し例）
- ディレクトリ構成（主要モジュールの説明）
- 環境変数一覧（必須 / 任意）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を支援するためのコンポーネント群です。  
主な用途は以下です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS ベースのニュース収集と銘柄紐付け
- 研究（ファクター計算 / 特徴量探索）用ユーティリティ
- 特徴量の正規化と features テーブルの作成
- features と AI スコアを統合して売買シグナルを生成
- シミュレーション用バックテストエンジン（ポートフォリオシミュレータ・指標計算）
- DuckDB スキーマの初期化スクリプト

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（レートリミット管理、リトライ、トークン更新）
  - RSS フィードからのニュース収集（SSRF対策、gzip 制限、トラッキングパラメータ除去）
- DB（DuckDB）関連
  - スキーマ定義と初期化（init_schema）
  - raw / processed / feature / execution 層を含むテーブル群
- ETLパイプライン
  - 差分更新ロジック、バックフィル、品質チェックを含む ETL ヘルパー
- 研究（research）
  - モメンタム / ボラティリティ / バリューのファクター計算
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量作成（build_features）
  - シグナル生成（generate_signals） — final_score の計算、Bear レジームでの BUY 抑制、SELL（エグジット）判定
- バックテスト（backtest）
  - 日次ループによるシミュレーション（PortfolioSimulator）
  - スリッページ・手数料モデル、約定処理、ポジション管理
  - メトリクス計算（CAGR / Sharpe / MaxDD / Win Rate / Payoff / Trades）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- その他
  - Slack / kabuステーション 連携用設定（設定読み込みと管理）

---

## セットアップ手順

前提：
- Python 3.10 以上（typing における PEP604 の union 型表記（|）を使用）
- DuckDB を利用可能な環境

1. リポジトリをチェックアウトして仮想環境を作成・有効化
   - macOS / Linux:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

2. 必要なパッケージをインストール
   - 最低限必要となるパッケージ例：
     ```bash
     pip install duckdb defusedxml
     ```
   - その他、プロジェクトで使用するパッケージがあれば追加してください。

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成（.env.example を参照する想定）
   - 必須環境変数（詳細は下部「環境変数一覧」参照）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 自動で .env / .env.local を読み込む挙動は code 内で実装されています。自動ロードを無効化する場合は環境変数を設定してください:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトから schema を初期化します（ファイル版 DB を使う例）:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```

---

## 使い方 / よく使うコマンド

### バックテスト実行（CLI）
DuckDB に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar など）が揃っていることを前提に実行します。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```

出力例（終了後に表示されるメトリクス）:
- CAGR, Sharpe Ratio, Max Drawdown, Win Rate, Payoff Ratio, Total Trades

---

### 特徴量生成（build_features）
DuckDB 接続と target_date を与えて features テーブルを生成します。

```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, date(2024, 1, 31))
print(f"upserted features: {n}")
conn.close()
```

実装ポイント：
- prices_daily / raw_financials を元に calc_momentum / calc_volatility / calc_value を呼び出す
- ユニバースフィルタ（最低株価・最低売買代金）を適用
- Z スコア正規化・±3 クリップ
- 日付単位で置換（DELETE + bulk INSERT）して冪等性を確保

---

### シグナル生成（generate_signals）
features と ai_scores、positions を参照して signals テーブル（buy / sell）を生成します。

```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
total = generate_signals(conn, date(2024, 1, 31))
print(f"generated signals: {total}")
conn.close()
```

パラメータ：
- threshold: BUY に必要な final_score の閾値（デフォルト 0.60）
- weights: component（momentum/value/volatility/liquidity/news）の重み辞書（合計は自動リスケール）

Bear レジーム検知時は BUY を抑制します。

---

### ETL（J-Quants データ取得）
jquants_client を通じてデータを取得し、save_* 関数で DuckDB に保存します。例：

```python
import duckdb
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print("saved rows:", saved)
conn.close()
```

注意：
- API レート制限（120 req/min）を内部で制御
- リトライ、トークン自動更新（401 の場合）に対応
- save_* 系は冪等（ON CONFLICT DO UPDATE）で設計

---

### ニュース収集（RSS）
RSS 取得と保存（run_news_collection）を使って raw_news と news_symbols を更新します。

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
print(res)
conn.close()
```

セキュリティ対策：
- SSRF 対策のリダイレクト検査、プライベートアドレス拒否
- gzip/bomb 対策（最大読み込みバイト数の制限）
- URL 正規化とトラッキングパラメータ除去

---

## ディレクトリ構成（主要ファイルと役割）

簡易ツリー（src/kabusys）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定の読み込み / validation（KABUSYS_ENV / LOG_LEVEL 等）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存機能）
    - news_collector.py
      - RSS 収集・前処理・保存
    - pipeline.py
      - ETL 差分更新ロジック、個別 ETL ジョブ
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - mom/vol/value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算 / IC / summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py
      - raw ファクターを正規化して features テーブルへ保存
    - signal_generator.py
      - final_score 計算と signals 生成（BUY/SELL）
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（インメモリ DB コピーして日次シミュレーション）
    - simulator.py
      - PortfolioSimulator（擬似約定・時価評価・TradeRecord）
    - metrics.py
      - バックテスト指標計算
    - run.py
      - CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py
      - SimulatedClock（将来拡張用）
  - execution/
    - __init__.py
    - （発注周りは別途実装想定）
  - monitoring/
    - （監視・アラート系は別途実装想定）

---

## 環境変数一覧（主なもの）

必須（稼働時）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（execution 層）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり：
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- DUCKDB_PATH — デフォルト DB path（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite path（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると自動 .env ロードを無効化

注意:
- config.Settings は未設定の必須変数について ValueError を投げます。開発時は .env を作成してください。

---

## 実装メモ / 注意点（開発者向け）

- DuckDB の DATE/TIMESTAMP の扱いや ORDER BY / WINDOW 関数を多用しているため、データのスキーマ整合性が重要です。
- jquants_client はレート制限とリトライロジックを実装していますが、実運用での大量同期間隔呼び出しには注意してください。
- news_collector は外部ネットワークのデータを扱うため、SSRF・XML インジェクション対策を施しています（defusedxml の利用等）。
- generate_signals 内の weights の扱いは堅牢化されています（未知キーや NaN/負値は無視、合計を 1.0 に正規化）。
- バックテストは実 DB を壊さないようにインメモリ接続を作ってデータをコピーして実行します（_build_backtest_conn）。
- ポジションのエグジット判定等は現状いくつかの拡張（トレーリングストップ、時間決済）を未実装としてコメントされています。

---

もし README に追加してほしい具体的な情報（CI/テスト手順、デプロイ方法、具体的な .env.example の内容、サンプルデータの準備スクリプトなど）があれば教えてください。必要に応じてサンプル .env や初期データロード手順を追記します。