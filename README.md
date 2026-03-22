# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
データ収集（J-Quants）、ETL、ファクター計算、特徴量エンジニアリング、シグナル生成、バックテスト、ニュース収集など一連の処理を含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の量的投資ワークフローを想定した小規模なフレームワークです。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・自動トークンリフレッシュ対応）
- DuckDB を用いたデータスキーマ管理と冪等的な保存
- 研究用ファクター計算（momentum / volatility / value 等）
- 特徴量正規化（Zスコア）と features テーブル構築
- シグナル生成（final_score に基づく BUY / SELL 判定）
- バックテストエンジン（シミュレータ、メトリクス算出）
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策・XML 防御・メモリ上限）

設計上のポイント:
- ルックアヘッドバイアス防止（target_date 時点のデータのみを使用）
- DB 操作は冪等（ON CONFLICT / トランザクション）を意識
- 本番発注層とは分離（strategy 層は execution 層に依存しない）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・レート制限対応）
  - schema: DuckDB スキーマ定義・初期化（init_schema）
  - pipeline: ETL ジョブ（差分取得・保存・品質チェック）
  - news_collector: RSS 取得・正規化・DB 保存・銘柄抽出
  - stats: Zスコア正規化など統計ユーティリティ
- research/
  - factor_research: momentum/volatility/value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリー
- strategy/
  - feature_engineering.build_features(conn, target_date): features テーブル構築
  - signal_generator.generate_signals(conn, target_date, ...): signals テーブルに BUY/SELL を作成
- backtest/
  - engine.run_backtest(...): 日次ループ方式のバックテスト実行
  - simulator.PortfolioSimulator: 擬似約定・手数料・スリッページ・時価評価
  - metrics.calc_metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD 等）
  - run.py: CLI からのバックテスト実行エントリポイント
- config:
  - 環境変数管理（.env 自動ロード、必須変数チェック）

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型記法や | 型ヒントに依存）
- DuckDB を使用（pip パッケージ: duckdb）
- RSS XML の安全パースに defusedxml を使用

例: 仮想環境作成と必要パッケージのインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
```

（プロジェクト配布に requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。）

環境変数:
- プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（config.py が自動ロード）。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（config.Settings が要求するもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN: Slack 通知（必要に応じて）
- SLACK_CHANNEL_ID: Slack チャンネルID
（その他）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視DBパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: one of development/paper_trading/live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例（.env のサンプル）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

DB スキーマ初期化:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
conn.close()
```

---

## 使い方

以下は代表的な操作の例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# (処理...)
conn.close()
```

2) J-Quants からデータ取得して保存（簡易例）
```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=...)
saved = jq.save_daily_quotes(conn, records)
conn.close()
```

3) ETL（パイプライン）: run_prices_etl など（pipeline モジュールを参照）
```python
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# target_date は通常当日の日付
fetched_count, saved_count = run_prices_etl(conn, target_date)
conn.close()
```

4) 特徴量構築
```python
import duckdb
from datetime import date
from kabusys.strategy import build_features

conn = duckdb.connect("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 15))
conn.close()
```

5) シグナル生成
```python
from kabusys.strategy import generate_signals
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date(2024,1,15), threshold=0.6)
conn.close()
```

6) ニュース収集（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
# results は {source_name: saved_count}
conn.close()
```

7) バックテスト（CLI）
プロジェクトルートから:
```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```

またはプログラムから:
```python
from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2023,1,4), end_date=date(2023,12,29))
# res.history, res.trades, res.metrics を使用
conn.close()
```

ログ出力は `LOG_LEVEL` 璧等により制御してください。

---

## 注意事項 / 運用メモ

- J-Quants API のレート制限（120 req/min）に注意。jquants_client は内部でスロットリングを行いますが、並列実行時には十分な設計を行ってください。
- DuckDB への書き込みは冪等性（ON CONFLICT）を考慮しています。ETL は差分取得を行いますが、backfill 設定により過去数日再取得して API の後出し修正を吸収できます。
- news_collector は SSRF 対策・XML 攻撃対策を実装していますが、外部 RSS の扱いは慎重に運用してください。
- 本リポジトリの戦略ロジック（重みや閾値）はサンプル実装です。実運用前に十分な検証を実施してください。
- positions / orders など実際の発注に係るテーブルの扱いは、kabuステーション等との連携実装に依存します。現状のコードは発注層と分離されており、実取引に接続する際は追加実装が必要です。

---

## ディレクトリ構成

以下はパッケージ内の主なファイルとディレクトリ（src/kabusys 以下）の概要です。

- kabusys/
  - __init__.py
  - config.py                  -- 環境変数 & 設定管理
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント & 保存関数
    - news_collector.py        -- RSS 収集・前処理・DB 保存
    - schema.py                -- DuckDB スキーマ定義・init_schema
    - stats.py                 -- zscore_normalize 等
    - pipeline.py              -- ETL パイプライン（差分取得等）
  - research/
    - __init__.py
    - factor_research.py       -- momentum / volatility / value の計算
    - feature_exploration.py   -- forward returns, IC, factor summary
  - strategy/
    - __init__.py
    - feature_engineering.py   -- build_features（features テーブル構築）
    - signal_generator.py      -- generate_signals（signals テーブル作成）
  - backtest/
    - __init__.py
    - engine.py                -- run_backtest（バックテスト全体フロー）
    - simulator.py             -- PortfolioSimulator（擬似約定）
    - metrics.py               -- バックテスト評価指標計算
    - clock.py                 -- SimulatedClock（将来拡張用）
    - run.py                   -- CLI エントリポイント
  - execution/                 -- 発注系の将来実装用（現在は空）
  - monitoring/                -- 監視系の将来実装用（現在は空）

（実際のファイル群は README 作成時点のソースリストに準拠）

---

## 開発 / 貢献

バグ報告や Pull Request は歓迎します。設計方針としては以下を重視してください。

- ルックアヘッドバイアスやデータリークの回避
- DB 操作は冪等性・トランザクションを保持
- 依存は最小限（できるだけ標準ライブラリ + 必須パッケージ）
- テスト可能性（外部 API 呼び出し箇所はモック可能に）

---

以上が KabuSys の概要と基本的な使い方です。具体的な利用シナリオや拡張（kabu API 統合、Slack 通知、運用ジョブ化等）が必要であれば、次のステップに合わせた補足ドキュメントを作成します。