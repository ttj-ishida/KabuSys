# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB をデータ格納層に用い、データ収集（J-Quants）、ETL、ファクター計算、シグナル生成、バックテスト、ニュース収集などの主要コンポーネントを提供します。

この README ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

主な目的
- J-Quants API などから日本株データ（OHLCV、財務、マーケットカレンダー）を取得して DuckDB に保存
- 研究（research）で作成したファクターを取り込み、特徴量エンジニアリングを行い features テーブルを作成
- 正規化済み特徴量と AI スコアを統合して売買シグナルを生成
- シグナルに基づくバックテストシミュレータを提供（スリッページ・手数料モデルを考慮）
- RSS ベースのニュース収集と銘柄紐付け機能

設計上のポイント
- ルックアヘッドバイアス防止（target_date 時点のデータのみを参照）
- DuckDB による軽量かつ高速な分析向けストレージ
- ETL と保存処理は冪等（ON CONFLICT / トランザクション）で実装
- ネットワークや外部 API 呼び出しに対するリトライ・レート制限の実装

---

## 機能一覧

- data/
  - J-Quants クライアント（ページネーション、トークンリフレッシュ、レート制限、保存関数）
  - RSS ニュース収集（SSRF 対策、gzip 制限、トラッキングパラメータ除去、記事ID生成）
  - DuckDB スキーマ定義・初期化（init_schema）
  - 統計ユーティリティ（Z スコア正規化等）
  - ETL パイプライン補助（差分取得、バックフィル、品質チェック呼び出し）
- research/
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリー）
- strategy/
  - 特徴量エンジニアリング（features テーブル作成、フィルタ、正規化、クリップ）
  - シグナル生成（final_score 計算、BUY/SELL 判定、Bear レジーム抑制）
- backtest/
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - バックテストエンジン（データコピー→日次ループ→約定→評価）
  - メトリクス計算（CAGR, Sharpe, MaxDD, Win Rate, Payoff Ratio）
  - CLI 実行用エントリポイント（python -m kabusys.backtest.run）
- execution / monitoring（発注・監視用プレースホルダ層）

---

## 要件

- Python 3.10 以上（型アノテーションで `|` を使用）
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリで多くの処理を実装しています（urllib 等）

例（pip インストール）:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロダクションでは他の依存（Slack API 等）を追加する可能性があります。

---

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo-root>
```

2. 開発用にローカルインストール（省略可）
```bash
python -m pip install -e .
```

3. 必要パッケージをインストール
```bash
python -m pip install duckdb defusedxml
```

4. 環境変数 / .env
- プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（config.py の自動ロード機能）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

その他（任意）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

サンプル .env（プロジェクトルート）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

5. DuckDB スキーマ初期化
Python REPL やスクリプトで以下を実行します:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```
またはデフォルト環境変数を使う場合は DUCKDB_PATH を参照して自前で指定してください。

---

## 使い方（代表的な例）

- バックテスト（CLI）
  このプロジェクトにはバックテスト用 CLI が用意されています。事前に DuckDB に必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を用意してください。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 \
  --slippage 0.001 \
  --commission 0.00055 \
  --max-position-pct 0.20 \
  --db data/kabusys.duckdb
```

- Python API からバックテストを呼ぶ
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
result = run_backtest(
    conn=conn,
    start_date=date(2023,1,1),
    end_date=date(2023,12,31),
    initial_cash=10_000_000,
)
conn.close()

print(result.metrics)
```

- 特徴量ビルド（feature engineering）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024,1,31))
print(f"features upserted: {n}")
conn.close()
```

- シグナル生成
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals

conn = duckdb.connect("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date(2024,1,31))
print(f"signals written: {count}")
conn.close()
```

- ETL（株価差分取得）例（J-Quants トークンが環境にある前提）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# target_date は通常は当日
result = run_prices_etl(conn, target_date=date.today())
print(result.to_dict())
conn.close()
```

- ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄リスト (例: {"7203", "6758", ...}) を渡すと紐付けを行う
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(res)
conn.close()
```

---

## 設計上の注意 / 動作前提

- DuckDB のスキーマは init_schema() で作成してください。既存 DB に対しては init_schema を最初に一度だけ実行することが推奨されます。
- J-Quants API はレート制限（120 req/min）があるため、ETL 実行時は適切に待ち時間が入り安全に収集されます。
- 自動で .env をロードする仕組みはプロジェクトルート（.git または pyproject.toml）を基準にしています。テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- 多くの関数は DuckDB のテーブル存在を前提としており、テーブル未作成の場合は動作しない箇所があります（init_schema で初期化してください）。
- 本ライブラリは取引実行 API（kabuステーション等）への発注ロジックと独立して設計されており、シグナル生成→発注のフローは実運用に合わせて execution 層を実装する必要があります。

---

## ディレクトリ構成（主要ファイル）

以下は主要モジュールの一覧（src/kabusys 以下の抜粋）。

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py              — J-Quants API クライアント + 保存関数
      - news_collector.py              — RSS ニュース収集・保存
      - schema.py                      — DuckDB スキーマ定義 / init_schema
      - stats.py                       — 統計ユーティリティ（zscore_normalize 等）
      - pipeline.py                    — ETL パイプラインヘルパー
    - research/
      - __init__.py
      - factor_research.py             — momentum / volatility / value 計算
      - feature_exploration.py         — 将来リターン・IC・summary
    - strategy/
      - __init__.py
      - feature_engineering.py         — features テーブル構築
      - signal_generator.py            — final_score 計算と signals 書き込み
    - backtest/
      - __init__.py
      - engine.py                      — run_backtest（エンジン）
      - simulator.py                   — PortfolioSimulator, 約定処理
      - metrics.py                     — バックテスト評価指標
      - clock.py                       — SimulatedClock（将来拡張用）
      - run.py                         — CLI エントリポイント
    - execution/                        — 発注層（パッケージ化済みだが内容は実装次第）
    - monitoring/                       — 監視系（プレースホルダ）

各ファイルは README のほか、ソーストップの docstring や関数 docstring に実装方針・仕様が詳述されています。実装や API の詳細はそれぞれのモジュールの docstring を参照してください。

---

## 追加メモ / 開発者向け

- 単体テストや CI のセットアップはリポジトリに含まれていないため、必要に応じて pytest などを追加してください。
- 外部システムと連携する部分（J-Quants / kabuステーション / Slack）には実ネットワークアクセスが必要です。ローカルテストではモックを利用してください（たとえば news_collector._urlopen を差し替えてテスト可能）。
- スキーマはバージョン管理の対象にして、スキーマ変更時はマイグレーション戦略を検討してください（DuckDB の制約に注意）。

---

もし README に追加したい内容（例: CLI の詳細、環境変数 .env.example を含むテンプレート、デプロイ手順、運用チェックリスト等）があれば教えてください。必要に応じて追記します。