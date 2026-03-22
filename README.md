# KabuSys

日本株向けの自動売買・データパイプライン・バックテスト基盤ライブラリです。  
DuckDB をデータストアに使い、J-Quants など外部データソースからの取得・品質管理・特徴量生成・シグナル生成・バックテストまでを一貫して扱えるよう設計されています。

主な設計方針
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを利用）
- DuckDB 上での冪等的なデータ保存（ON CONFLICT / トランザクション）
- テスト容易性を考慮した id_token 注入や自動 env ロードの無効化オプション
- 外部依存を最小限に（標準ライブラリ + 必要最小限の外部パッケージ）

---

## 機能一覧
- データ収集・保存
  - J-Quants からの日次株価、財務データ、マーケットカレンダー取得
  - RSS からのニュース収集（前処理・SSRF 対策・トラッキングパラメータ除去）
  - DuckDB への冪等保存（raw / processed / feature / execution 層のスキーマ）
- データ品質チェック（quality モジュールと連携する設計）
- 研究用ファクター計算（momentum / volatility / value など）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブルへの UPSERT）
- シグナル生成（features と ai_scores を統合して BUY/SELL を生成）
- 発注・ポートフォリオシミュレータ（バックテスト用、スリッページ・手数料モデル含む）
- バックテストエンジン（DB コピー → 日次ループ → 評価指標算出）
- CLI エントリポイント（バックテスト実行用）

---

## 前提条件
- Python 3.10 以上（typing の新しい構文を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- 環境変数管理に .env（プロジェクトルートの .env / .env.local を自動読み込み。無効化可）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# プロジェクトを開発用にインストールする場合:
# pip install -e .
```

---

## 環境変数
このパッケージは環境変数から設定を読み込みます（`.env` / `.env.local` をプロジェクトルートから自動読み込み）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数
- J-Quants / API
  - JQUANTS_REFRESH_TOKEN — 必須（J-Quants のリフレッシュトークン）
- kabu ステーション API（発注等）
  - KABU_API_PASSWORD — 必須
  - KABU_API_BASE_URL — 省略可（デフォルト: http://localhost:18080/kabusapi）
- Slack（通知など）
  - SLACK_BOT_TOKEN — 必須
  - SLACK_CHANNEL_ID — 必須
- DB / パス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
- 実行環境
  - KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

不足時は `kabusys.config.settings` のプロパティ呼び出しで例外が出ます（必須項目は _require により ValueError）。

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url> kabusys
cd kabusys
```

2. Python 仮想環境作成・パッケージインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 追加の依存があればここでインストール
```

3. 環境変数設定
- プロジェクトルートに `.env` を作成（`.env.example` を参考に）
- もしくは OS の環境変数で設定

4. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
init_schema("data/kabusys.duckdb")
```
もしくは Python スクリプト/REPL で実行。`:memory:` を指定するとインメモリ DB を使えます（テスト用）。

---

## 使い方（代表的なワークフロー）

以下は代表的な利用例です。実運用ではスケジューラやジョブランナー（cron / Airflow 等）からこれらを呼ぶことを想定しています。

1. データ取得（ETL）の実行（株価差分取得の例）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
target = date.today()
fetched, saved = run_prices_etl(conn, target_date=target)
conn.close()
print("fetched:", fetched, "saved:", saved)
```
（pipeline モジュールには市場カレンダー・財務データなどの ETL 関数も用意されています）

2. ニュース収集と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は有効銘柄コードの set（抽出に使用）
res = run_news_collection(conn, sources=None, known_codes=set(["7203", "6758"]))
print(res)  # {source_name: saved_count, ...}
```

3. 特徴量（features）構築
```python
from datetime import date
from kabusys.strategy import build_features
# conn は DuckDB 接続
count = build_features(conn, target_date=date(2024,1,31))
print("features upserted:", count)
```

4. シグナル生成
```python
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, target_date=date(2024,1,31))
print("signals written:", n)
```

5. バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000
```

6. バックテスト（プログラム呼び出し）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
print(result.metrics)
conn.close()
```

---

## 主要 API（短い参照）
- kabusys.data.schema
  - init_schema(db_path) — スキーマ作成 / 接続を返す
  - get_connection(db_path) — 既存 DB への接続
- kabusys.data.jquants_client
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - get_id_token()
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection
- kabusys.data.pipeline
  - run_prices_etl / get_last_price_date / run_other_etl...
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定読み込み（.env 自動ロード機能）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（レート制限・リトライ・トークン管理）
    - news_collector.py — RSS 収集、前処理、DB 保存
    - schema.py — DuckDB スキーマ定義と init_schema
    - stats.py — z-score 正規化などの統計ユーティリティ
    - pipeline.py — ETL パイプライン（差分更新・保存・品質チェック連携）
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — forward returns / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — features 作成（正規化・ユニバースフィルタ）
    - signal_generator.py — final_score 計算と BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py — バックテストエンジン（DB コピー→日次ループ）
    - simulator.py — PortfolioSimulator（擬似約定・履歴）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント
    - clock.py — 将来拡張用の模擬時計
  - execution/ — 発注・実行関連（将来的な実装想定）
  - monitoring/ — 監視・メトリクス（SQLite 連携など、将来的な実装想定）
  - backtest/*, research/* などはドメイン別に分割

---

## 開発上の注意 / トラブルシューティング
- .env の自動読み込みはプロジェクトルート (.git または pyproject.toml を基準) を検出して行います。テストなどで無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかのみ有効です。誤った値は ValueError を発生させます。
- DuckDB のテーブル定義は厳格（CHECK 制約や NOT NULL 等）です。既存データを取り込むときは型・NULL に注意してください。
- J-Quants API のトークン周りは自動リフレッシュを行いますが、初期の refresh token は環境変数で必ず設定してください。
- RSS 収集は SSRF 対策や受信サイズ上限を設けています。外部 URL の取り扱いには注意してください。

---

README は以上です。動かし方や追加のユースケース（運用ワークフロー、ジョブスケジューリング、監視・通知の実装例）が必要であれば、用途に合わせてサンプル手順や運用設計を追記します。