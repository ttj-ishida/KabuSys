# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
価格・財務・ニュースの収集、ファクター計算、シグナル生成、バックテスト、簡易発注層のサポートを含むモジュール群を提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「DuckDB中心のローカルデータ管理」「外部 API 呼び出しの安全化（SSRF対策等）」です。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（レート制限、リトライ、トークン自動リフレッシュ）
  - RSS ベースのニュース収集（URL正規化、SSRF対策、記事ID生成）
  - DuckDB スキーマ定義／初期化（raw → processed → feature → execution の多層スキーマ）
  - ETL パイプライン（差分更新・バックフィル・品質チェック用フック）

- 研究・ファクター
  - Momentum / Volatility / Value のファクター計算（prices_daily / raw_financials から）
  - クロスセクション Z スコア正規化ユーティリティ
  - ファクター探索（将来リターン計算、IC 計算、統計サマリ）

- 戦略（Signal）
  - 特徴量作成（生ファクターの統合・フィルタ・正規化）
  - シグナル生成（final_score 計算、Bear レジームフィルタ、BUY/SELL 判定）
  - signals テーブルへの冪等な保存

- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル、約定ロジック）
  - 日次ループのバックテストエンジン（本番DBからインメモリへコピーして実行）
  - バックテスト評価指標（CAGR、Sharpe、MaxDD、勝率、Payoff ratio）

- ニュース→銘柄紐付け
  - 記事保存（重複回避）
  - テキスト中の4桁銘柄コード抽出と news_symbols への保存

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型記法などを使用）
- pip が使用可能

1. リポジトリをクローン（またはプロジェクト配布を配置）
2. 必要パッケージをインストール（最小）
   - duckdb
   - defusedxml
   - （その他のユースケースに応じて追加パッケージをインストール）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発時はパッケージを編集可能インストール
pip install -e .
```

3. 環境変数設定
プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

推奨的な .env（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマ初期化（ファイルベース DB）
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```
またはコマンドラインから Python スクリプトを実行して行えます。

---

## 使い方

以下は代表的な利用例です。詳細は各モジュールの docstring を参照してください。

- DB 初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- J-Quants からデータ取得と保存（プログラム的に）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, recs)
```

- ETL パイプライン（株価差分 ETL の一例）
```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
# run_prices_etl は (fetched, saved) を返します
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（例: exchange の上場銘柄）
results = run_news_collection(conn, known_codes=set(["7203","6758"]))
```

- 特徴量作成・シグナル生成
```python
from kabusys.strategy import build_features, generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
build_features(conn, target_date=date(2024,1,15))
generate_signals(conn, target_date=date(2024,1,15))
```

- バックテスト（CLI）
本パッケージはバックテスト用の CLI エントリポイントを提供しています。

例:
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

主要オプション:
- --start / --end : YYYY-MM-DD（必須）
- --db : DuckDB ファイルパス（必須）
- --cash / --slippage / --commission / --max-position-pct

- バックテストをプログラム的に呼ぶ
```python
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
```

---

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須) - J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) - kabuステーション API パスワード
- KABU_API_BASE_URL - kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) - Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) - Slack チャネル ID
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV - 実行環境（development | paper_trading | live）
- LOG_LEVEL - ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

注意:
- 自動環境読み込みは .env / .env.local をプロジェクトルートから読みます。テスト時などで無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル/モジュール）

src/kabusys/
- __init__.py
- config.py
  - 環境変数 / 設定の読み込みロジック
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得・保存関数）
  - news_collector.py         — RSS 取得・記事保存・銘柄抽出
  - schema.py                 — DuckDB スキーマ定義・初期化
  - stats.py                  — zscore_normalize 等の統計ユーティリティ
  - pipeline.py               — ETL パイプラインヘルパー
- research/
  - __init__.py
  - factor_research.py        — Momentum / Volatility / Value のファクター算出
  - feature_exploration.py    — forward returns / IC / summary
- strategy/
  - __init__.py
  - feature_engineering.py    — features テーブル生成（正規化・フィルタ）
  - signal_generator.py       — final_score 計算・BUY/SELL 判定
- backtest/
  - __init__.py
  - engine.py                 — バックテストの全体制御（run_backtest）
  - simulator.py              — PortfolioSimulator（約定・マークツーマーケット）
  - metrics.py                — バックテスト評価指標計算
  - run.py                    — CLI エントリポイント
  - clock.py                  — 将来拡張用の模擬時計
- execution/                   — 発注実装用プレースホルダ（空パッケージ）
- monitoring/                  — 監視・モニタリング用（将来的な実装）

---

## 開発・コントリビュート

- コードのドキュメントは各モジュールの docstring を参照してください。
- テストは現状パッケージ内に含まれていません。ユニットテスト追加、CI の導入を歓迎します。
- 安全性（SSRF、XMLパース、外部入力の検証）に配慮した実装方針を取っています。第三者 API トークンや実口座での利用時には十分に注意してください（特に live 環境）。

---

## ライセンス・注意事項

この README はコードベースの説明を目的としています。実際の運用（特に live 口座での自動売買）では十分な検証・監査を行ってください。金融商品取引・API 利用に関する法令や利用規約を遵守する責任は利用者にあります。

---

必要であれば、README に「API リファレンス」「.env.example」「よくある質問（FAQ）」などの追加節を作成します。どの情報を優先して追記しましょうか？