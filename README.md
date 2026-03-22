# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用コンポーネント群です。データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、バックテスト、ニュース収集・紐付け、ポートフォリオシミュレーションなど、戦略開発と運用に必要な機能をモジュール化して提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（各処理は target_date 時点のデータのみ参照）
- DuckDB によるローカル DB（raw / processed / feature / execution 層）
- 冪等性を重視（DB への INSERT は ON CONFLICT / トランザクションで安全に）
- 外部依存は最小限（標準ライブラリ中心、必要に応じて duckdb, defusedxml 等）

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ユースケース例）
- 環境変数
- ディレクトリ構成
- 参考（実行例・注意点）

---

## プロジェクト概要

このリポジトリは戦略開発からバックテスト、データパイプラインまでを包含した日本株自動売買システムのコアライブラリ群です。モジュールは目的別に分かれており、研究環境（research）で作成した生ファクターを正規化して features に格納し、そこからシグナルを生成、発注/シミュレーション（バックテスト）を行います。J-Quants API を介した価格・財務データ取得および RSS ベースのニュース収集機能も含みます。

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（ページネーション対応、トークン自動更新、リトライ/レート制御）
  - raw_prices / raw_financials / market_calendar の保存関数
  - DuckDB スキーマ初期化（init_schema）

- ETL パイプライン
  - 差分更新ロジック（最終取得日からの再取得 / backfill）
  - 品質チェック（quality モジュールと連携する設計）

- ニュース収集
  - RSS フィード取得（SSRF / private-host 検査、gzip 解凍、XML の安全パース）
  - 記事ID の冪等生成（正規化 URL の SHA-256 先頭 32 文字）
  - raw_news / news_symbols への保存

- 研究用・特徴量計算
  - ファクター計算（Momentum, Volatility, Value 等）
  - クロスセクション Z スコア正規化

- 特徴量エンジニアリング（strategy.feature_engineering）
  - raw ファクターの合成、ユニバースフィルタ、Z スコアクリッピング、features テーブルへの UPSERT

- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出
  - Bear レジーム判定（ai_scores の regime_score 集計）
  - BUY / SELL シグナルの生成と signals テーブルへの書き込み

- バックテスト（backtest）
  - 日次ループの engine（run_backtest）
  - PortfolioSimulator（擬似約定、スリッページ・手数料モデル）
  - メトリクス計算（CAGR, Sharpe, MaxDD, WinRate, PayoffRatio）
  - CLI エントリポイント: python -m kabusys.backtest.run

- ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - 研究支援（IC 計算、将来リターン計算、factor summary）

---

## セットアップ手順

1. Python 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 最低限の依存パッケージをインストール
   - 本プロジェクトで明示的に利用しているパッケージ:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```

   （このリポジトリに requirements.txt / pyproject.toml があればそちらを利用してください。ローカル環境依存の追加パッケージは適宜インストールしてください。）

3. パッケージとして開発インストール（任意）
   ```
   pip install -e .
   ```

4. DuckDB スキーマの初期化
   Python コンソールまたはスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # data/ 以下は自動作成されます
   conn.close()
   ```

5. 環境変数（後述）を設定
   - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 環境変数

Settings（kabusys.config.Settings）は以下の環境変数を参照します。必須のものは未設定だと ValueError を投げます。

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants API のリフレッシュトークン（fetch / save 系を使う場合必須）
- KABU_API_PASSWORD
  - kabu ステーション API を利用する場合のパスワード
- SLACK_BOT_TOKEN
  - Slack 通知用（未使用の箇所がある場合でも設定が期待されます）
- SLACK_CHANNEL_ID
  - Slack 通知先チャンネル ID

任意 / デフォルト値あり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

.env 例（プロジェクトルートの .env に配置）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# optional
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

自動ロードの挙動:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を特定して .env, .env.local を順に読み込みます。
- 自動ロードを無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 使い方

以下に代表的な利用シナリオ（コードスニペット／CLI）を示します。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

2) J-Quants から株価を取得して保存（簡易例）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
conn.close()
print("saved:", saved)
```

3) ETL (株価差分取得) の呼び出し例
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
conn.close()
print(f"fetched={fetched} saved={saved}")
```
（run_prices_etl の詳細引数や戻り値は pipeline モジュールの docstring を参照）

4) ニュース収集の実行例
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes に既知の銘柄コードセットを渡すと記事→銘柄紐付けを行います
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
conn.close()
print(results)
```

5) 特徴量生成（features テーブルへ書き込み）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import build_features
from datetime import date

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,31))
conn.close()
print("features upserted:", n)
```

6) シグナル生成（signals テーブルへ書き込み）
```python
from kabusys.data.schema import init_schema
from kabusys.strategy import generate_signals
from datetime import date

conn = init_schema("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,1,31))
conn.close()
print("signals written:", count)
```

7) バックテスト CLI
DuckDB に必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）が存在することが前提です。
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
出力にバックテストメトリクス（CAGR, Sharpe, Max Drawdown 等）が表示されます。

8) バックテストを Python から呼ぶ（プログラム的利用）
```python
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest
from datetime import date

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
conn.close()

print(res.metrics)
```

---

## ディレクトリ構成

主要なファイル／モジュールを抜粋して記載します（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数／設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / 認証 / レート制御 / 冪等保存）
    - news_collector.py
      - RSS フィード取得・解析・raw_news 保存・記事→銘柄紐付け
    - pipeline.py
      - ETL 差分更新 / run_prices_etl 等
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - features テーブル作成（正規化・ユニバースフィルタ等）
    - signal_generator.py
      - features + ai_scores 統合 → final_score → BUY/SELL シグナル生成
  - backtest/
    - __init__.py
    - engine.py
      - run_backtest（全体ループ、バックテスト用インメモリ DB 構築）
    - simulator.py
      - PortfolioSimulator（擬似約定、mark_to_market、TradeRecord）
    - metrics.py
      - バックテスト評価指標計算
    - run.py
      - CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py
      - 将来拡張用の模擬時計
  - execution/
    - (発注／実行ロジック用プレースホルダ)
  - monitoring/
    - (監視／通知用プレースホルダ)

---

## 注意点 / 実運用メモ

- DuckDB スキーマは init_schema() で作成されます。初回起動時はこれを必ず呼んでください。
- J-Quants の API レート制限・リトライや 401 トークンリフレッシュは jquants_client に実装されていますが、API 利用時は必ず設定（JQUANTS_REFRESH_TOKEN）を行ってください。
- ニュース収集では SSRF / private-host 検査、レスポンスサイズ制限、XML の安全パース等を実装済みです。ただし外部フィードの多様性によるパースエラーには個別対応が必要になることがあります。
- 自動で .env を読み込みますが、テストや一時的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- features / signals / positions などは日付単位の「置換（DELETE -> INSERT）」で処理されるため、同日の再実行が冪等になるよう設計されています。
- 実行ログは logging モジュールで制御します。LOG_LEVEL でログレベルを指定できます。

---

## 参考

- 主要エントリポイント
  - Backtest CLI: python -m kabusys.backtest.run
  - スキーマ初期化: kabusys.data.schema.init_schema
  - ETL 関数: kabusys.data.pipeline.run_prices_etl
  - ニュース収集: kabusys.data.news_collector.run_news_collection
  - 特徴量生成: kabusys.strategy.build_features
  - シグナル生成: kabusys.strategy.generate_signals
  - バックテスト（プログラム呼び出し）: kabusys.backtest.engine.run_backtest

必要があれば README を拡張して、具体的な .env.example、サンプルデータの用意手順、CI での DB 初期化スクリプト、あるいは運用時のジョブスケジュール例（cron / systemd / Airflow など）を追加できます。どの情報がさらに必要か教えてください。