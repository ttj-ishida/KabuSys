# KabuSys

日本株向けの自動売買 / データ基盤 / バックテスト用ライブラリです。  
価格・財務・ニュース等の取得・保存、ファクター計算、シグナル生成、バックテストシミュレータを備え、DuckDB を中心にデータパイプラインと戦略実行ロジックを提供します。

---

## プロジェクト概要

KabuSys は以下のレイヤーを含むモジュール群で構成されています。

- Data Layer（データ取得・保存）
  - J-Quants API から株価・財務・マーケットカレンダーを取得し DuckDB に保存
  - RSS ベースのニュース収集と銘柄紐付け
  - データ品質チェック・ETL パイプライン
- Research / Feature（研究用ファクター計算）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターンやIC（Information Coefficient）の計算、統計要約
- Strategy（戦略）
  - ファクター正規化・合成（features のビルド）
  - 最終スコア計算と BUY/SELL シグナル生成
- Backtest（バックテスト）
  - データをコピーしたインメモリ DuckDB 上で日次シミュレーション
  - 約定モデル（スリッページ・手数料）、ポートフォリオ管理、メトリクス算出
- Execution / Monitoring（発注・監視）
  - 発注・約定・ポジション管理用スキーマ（実装は拡張向け）

設計上、ルックアヘッドバイアスを防ぐため「target_date 時点で利用可能なデータのみ」を用いる方針が徹底されています。DuckDB をデータ永続化に用い、冪等な保存（ON CONFLICT）やトランザクションで整合性を確保しています。

---

## 機能一覧

主な機能（抜粋）：

- J-Quants API クライアント
  - 株価（日足）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar）
- ニュース収集
  - RSS フィード取得、テキスト前処理、記事ID の一意化、銘柄抽出・紐付け
  - SSRF 対策やサイズ上限、XML 脆弱性対策（defusedxml）
- データスキーマ（DuckDB）
  - raw / processed / feature / execution の各レイヤーテーブル定義と初期化
- Feature エンジニアリング
  - calc_momentum / calc_volatility / calc_value を組み合わせて features テーブル作成
  - Z スコア正規化、ユニバースフィルタ（株価・売買代金）
- シグナル生成
  - ファクター＋AI スコアを統合して final_score 計算
  - Bear レジーム検出による BUY 抑制、SELL（ストップロス等）判定
  - signals テーブルへの日付単位の置換（冪等）
- バックテスト
  - インメモリ DB を作成して日次ループでシミュレーション
  - 実行順序（SELL→BUY）、ポジションサイジング、マーク・トゥ・マーケット
  - メトリクス（CAGR、Sharpe、MaxDrawdown、勝率、Payoff ratio）

---

## 要求環境 / 依存関係

- Python 3.10 以上（型注釈に | を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- （プロジェクトにより追加の依存がある場合があります。必要に応じて requirements を用意してください。）

pip 例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 編集可能インストール（パッケージ化されている場合）
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンする
```bash
git clone <repo-url>
cd <repo>
```

2. Python 仮想環境作成・有効化
```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
# Windows:
# .venv\Scripts\activate
```

3. 必要パッケージをインストール
```bash
pip install duckdb defusedxml
# あるいはプロジェクトの提供する requirements.txt があれば:
# pip install -r requirements.txt
```

4. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
# ファイル DB を作成してスキーマを初期化
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

5. 環境変数の準備
- プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（ただしテストで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- 主な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (監視用途)
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方

ここでは代表的なユースケースの実行例を示します。

1) DuckDB の初期化（上記手順）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

2) データ取得（J-Quants）→ 保存
- jquants_client にある fetch_* / save_* を組み合わせて ETL を行います。
- 例（株価差分 ETL を呼ぶ DataPipeline を利用する場合）:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
today = date.today()
fetched, saved = run_prices_etl(conn, target_date=today)
conn.close()
```

3) features のビルド
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
conn.close()
print(f"upserted features: {count}")
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date(2024, 1, 31))
conn.close()
print(f"generated signals: {num}")
```

5) バックテスト（CLI）
リポジトリに用意されているエントリポイントを使用してバックテストを実行できます。
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
バックテストは内部でデータをインメモリ DuckDB にコピーしてシミュレーションを行います。実行後に CAGR / Sharpe / MaxDrawdown 等を表示します。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュールとファイルの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み、Settings クラス
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 & 保存）
    - news_collector.py      — RSS ニュース収集・前処理・DB 保存
    - schema.py              — DuckDB スキーマ定義 / init_schema()
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - pipeline.py            — 差分 ETL / パイプライン
    - quality.py             — （品質チェックモジュール: このリストに準ずる想定）
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（正規化・ユニバースフィルタ）
    - signal_generator.py    — final_score 計算と signals 生成
  - backtest/
    - __init__.py
    - engine.py              — run_backtest メインロジック
    - simulator.py           — PortfolioSimulator / 約定モデル
    - metrics.py             — バックテスト指標計算
    - run.py                 — CLI ランナー
    - clock.py               — SimulatedClock（将来拡張用）
  - execution/               — 発注層（拡張ポイント）
    - __init__.py
  - monitoring/              — 監視 / アラート（拡張ポイント）
    - __init__.py

（注）実際のリポジトリにはさらに細分化されたモジュールやユーティリティが含まれる想定です。

---

## 設計上の注意事項 / 参考

- 自動で .env を読み込む機構が config.py にあり、読み込み優先順位は OS 環境変数 > .env.local > .env です。自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- DuckDB のスキーマは init_schema() により冪等的に作成されます。既存データを保ったままスキーマ更新したい場合は注意して実行してください。
- API のレート制御・再試行・トークン更新は jquants_client に実装されています。実運用では J-Quants のレート制限や認証要件に従ってください。
- ニュース収集では SSRF、XML Bomb、レスポンスサイズ等への対策が組み込まれています。
- バックテストは本番テーブル（signals / positions 等）を汚さないよう、内部でインメモリ DB を構築して実行します。

---

## ライセンス / 貢献

- ライセンス情報はリポジトリに含めてください（このスニペットには含まれていません）。  
- バグ報告・機能提案・プルリクエスト歓迎です。コードスタイルやテスト方針は CONTRIBUTING.md を参照してください（存在する場合）。

---

README は以上です。必要があれば以下の追加情報を作成します：

- 詳細な .env.example（各キーの説明）
- ETL / Scheduler の実運用手順（cron / Airflow 例）
- 単体テストの実行方法や CI 設定サンプル
- API の利用例スクリプト（ニュース収集、J-Quants フルバックフィル等）

どれを追加しましょうか？