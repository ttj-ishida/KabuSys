# KabuSys

日本株向けの自動売買・研究プラットフォーム（KabuSys）のコードベース概要と利用手順をまとめた README です。  
このリポジトリはデータ取得（J-Quants）、ETL／データ品質管理、ファクター計算、シグナル生成、バックテスト、ニュース収集、DuckDB スキーマ管理などを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けライブラリで、主に以下を提供します。

- J-Quants API から市場データ・財務データ・市場カレンダーを取得・保存
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB スキーマ定義とデータ永続化（Raw / Processed / Feature / Execution 層）
- 研究用のファクター計算（Momentum / Volatility / Value 等）と特徴量エンジニアリング
- 正規化された特徴量と AI スコアを統合して売買シグナルを生成
- シグナルを使ったメモリ内ポートフォリオシミュレーション（バックテスト）
- バックテストの評価指標計算（CAGR、Sharpe、Max Drawdown 等）
- ETL パイプライン（差分更新、バックフィル、品質チェック）

設計上のポイント：
- ルックアヘッドバイアスを避けるため、target_date 時点までのデータのみを用いる設計
- DuckDB を中心としたローカル DB 管理（":memory:" でのバックテストも可能）
- 冪等性（INSERT ... ON CONFLICT / トランザクション）を重視

---

## 機能一覧（主要）

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・レート制限・リトライ・トークンリフレッシュ対応）
  - news_collector: RSS 取得・記事正規化・raw_news / news_symbols 保存
  - schema: DuckDB スキーマ定義と init_schema()
  - stats: z-score 正規化などの統計ユーティリティ
  - pipeline: ETL（差分取得・保存・品質チェック）、run_prices_etl など
- research/
  - factor_research: momentum / volatility / value ファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- strategy/
  - feature_engineering.build_features: raw ファクターを正規化して features テーブルへ保存
  - signal_generator.generate_signals: features と ai_scores を使って BUY/SELL シグナルを生成
- backtest/
  - engine.run_backtest: ローカルでのバックテスト実行ループ
  - simulator.PortfolioSimulator: 約定ロジック（スリッページ・手数料モデル）
  - metrics.calc_metrics: バックテスト評価指標
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config:
  - 環境変数読み込みと Settings クラス（自動 .env ロード、必須キー検証）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型注釈に PEP 604（| 型）等を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- （任意）開発用: pytest など

インストール例（venv を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install "duckdb" "defusedxml"
# またはプロジェクトの requirements.txt があればそれを利用
```

---

## 環境変数 (.env)／設定

自動で .env（プロジェクトルート）および .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（Settings クラスより）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — モニタリング用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

例: .env.example
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

2. .env を作成（プロジェクトルート）
   - 上記の必須変数を設定してください。

3. DuckDB スキーマを初期化
   - デフォルトパスを使う場合（settings.duckdb_path のデフォルトは data/kabusys.duckdb）:
     ```python
     python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
     ```
   - 別パスの場合は引数にパスを指定してください。":memory:" を使うとインメモリ DB を作成します。

4. （任意）J-Quants データを ETL して prices_daily などを埋める
   - python REPL/スクリプトから pipeline.run_prices_etl 等を呼び出して差分取得・保存を行います（下記 使い方参照）。

---

## 使い方（主要ケース）

以下は代表的なユースケースとサンプル呼び出しです。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

2) J-Quants から株価差分 ETL（pipeline.run_prices_etl）
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
target = date.today()
fetched, saved = run_prices_etl(conn, target_date=target)
print("prices fetched:", fetched, "saved:", saved)
conn.close()
```

3) ニュース収集ジョブを実行（RSS）:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 抽出用に有効な銘柄コードセットを渡す
results = run_news_collection(conn, known_codes=known_codes)
print(results)
conn.close()
```

4) 特徴量作成（features テーブルへ保存）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features

conn = init_schema("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 31))
print("features upserted:", count)
conn.close()
```

5) シグナル生成（signals テーブルへ保存）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals

conn = init_schema("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date(2024, 1, 31))
print("signals written:", num)
conn.close()
```

6) バックテスト（CLI）
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```
- 上記は DB に prices_daily, features, ai_scores, market_regime, market_calendar が予め存在していることが前提です。
- Python API からは `kabusys.backtest.engine.run_backtest(conn, start_date, end_date, ...)` を呼べます。

7) バックテスト API の例（Python）
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

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 収集、raw_news / news_symbols 保存
    - schema.py — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - pipeline.py — ETL パイプライン（差分取得 / backfill / 品質チェック）
  - research/
    - __init__.py
    - factor_research.py — momentum / volatility / value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py — ファクター正規化 → features テーブル
    - signal_generator.py — final_score 計算 → signals テーブル
  - backtest/
    - __init__.py
    - engine.py — run_backtest（全体ループ、バックテスト用接続作成）
    - simulator.py — PortfolioSimulator（擬似約定）
    - metrics.py — バックテスト評価指標計算
    - run.py — CLI エントリポイント
    - clock.py — 将来的な模擬時計
  - execution/ — 発注関連（現在はパッケージエクスポートのみ）
  - monitoring/ — 監視用 DB/処理（別途実装想定）

---

## 注意点 / 実運用上のヒント

- Settings はいくつかの値を必須としているため、.env に必要なキーを用意してから動かしてください。
- J-Quants のレート制限（120 req/min）を守る実装になっていますが、多量データの取得は時間がかかります。バックフィル時は分割して実行することを検討してください。
- ニュース RSS 収集は外部 URL にアクセスするため SSRF 対策やタイムアウトを必ず設定しています。プロダクションでの実行時にはネットワークルールを適切に設定してください。
- DuckDB のファイルは単一ファイルで管理されます。バックアップ、アクセス制御、排他管理（複数プロセスでの同時書込み）を考慮してください。
- generate_signals / build_features は DB のスキーマ（特定テーブル）を前提に動作します。事前に init_schema と必要なデータ投入を行ってください。

---

## 貢献 / 開発

- コードの拡張やバグ修正の際はユニットテストを追加してください（現在のリポジトリにテストフレームワークが含まれていない場合は pytest などを導入してください）。
- 大きなデータ操作は小さなバッチに分け、ログとモニタリングを充実させてください。

---

README の内容やサンプルについて、プロジェクト固有の実行手順（CI、デプロイ方法、追加の外部サービス連携など）を追記したい場合は、その要件を教えてください。必要に応じて .env.example を自動生成するテンプレートや、よく使う CLI 実行スクリプトも作成できます。