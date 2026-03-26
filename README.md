# KabuSys

日本株向けの自動売買システムのコアライブラリ（研究・データ収集・シグナル生成・バックテスト等）。  
本リポジトリはデータ取得（J-Quants）、ニュース収集、特徴量生成、シグナル生成、ポートフォリオ構築、バックテストシミュレータなどの主要コンポーネントを提供します。

主な設計方針：
- バックテストと本番ロジックの分離（ルックアヘッドバイアス回避）
- DuckDB を用いた分析データ格納
- 冪等性を意識した DB 書き込み（ON CONFLICT 等）
- 外部 API 呼び出しはレート制御・リトライ・認証刷新を実装

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価、財務、上場情報、マーケットカレンダー）
  - ニュース（RSS）収集、記事の前処理、銘柄抽出、DB 保存
- 研究 / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials ベース）
  - ファクターの統計解析（IC, 相関, サマリ）
- 特徴量エンジニアリング
  - 生ファクターの正規化（Z スコア）、ユニバースフィルタ、features テーブルへの UPSERT
- シグナル生成（strategy）
  - features + AI スコアを統合して final_score を算出
  - BUY / SELL シグナル生成（レジーム判定・ストップロス等のエグジット判定含む）
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分、リスクベースサイジング
  - セクター集中制限、レジーム乗数の適用
- バックテスト
  - インメモリ DuckDB にデータをコピーして安全にバックテスト実行
  - 約定モデル（スリッページ、手数料、部分約定、単元丸め）
  - メトリクス計算（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）
  - CLI エントリポイントあり
- 実行 / 監視周り（骨格）
  - execution / monitoring 用のパッケージ構成（発注先 API 連携は別途実装）

---

## 必要環境 / 依存

- Python 3.10 以上（typing における | 型表記などを使用）
- 必須ライブラリ（代表例）
  - duckdb
  - defusedxml
- 標準ライブラリ：urllib, datetime, logging, dataclasses 等

requirements.txt がある場合はそれを使用してください。無ければ最低限以下をインストールします：

```bash
python -m pip install "duckdb" "defusedxml"
```

ソースを editable インストールする場合：

```bash
python -m pip install -e .
```

（プロジェクトに setup / pyproject があれば適宜インストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 仮想環境作成・有効化
3. 依存ライブラリをインストール（上記参照）
4. DuckDB スキーマの初期化（スキーマ定義は `kabusys.data.schema.init_schema` を利用）
   - 例：Python REPL またはスクリプトで
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - ※ schema モジュールはスキーマ定義・テーブル作成を行います（本リポジトリに含まれる想定）

5. 環境変数を設定（.env ファイルをプロジェクトルートに置くと自動で読み込まれます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）

必須の環境変数（コード上で _require() により必須指定されているもの）：
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトあり）：
- KABUSYS_ENV (development / paper_trading / live) — デフォルト `development`
- LOG_LEVEL (DEBUG / INFO / ...) — デフォルト `INFO`
- DUCKDB_PATH（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH（デフォルト `data/monitoring.db`）

例 .env（プロジェクトルート）：

```
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（主要な操作例）

以下は代表的な利用方法の抜粋です。各モジュールはプログラムから直接呼び出せます。

- DuckDB 初期化（スキーマ作成）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- J-Quants から日足取得・保存
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=None, date_to=None)  # 引数を指定して絞る
save_daily_quotes(conn, records)
conn.close()
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes に銘柄コード集合を渡すと銘柄紐付けまで行う
result = run_news_collection(conn, known_codes={"7203", "6758"})
print(result)  # {source_name: saved_count, ...}
conn.close()
```

- 特徴量作成（features テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import build_features
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {n}")
conn.close()
```

- シグナル生成（signals テーブルへの書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
num = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {num}")
conn.close()
```

- バックテスト（CLI）
リポジトリに含まれる CLI エントリポイントを利用できます。

```bash
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --db data/kabusys.duckdb \
  --cash 10000000 \
  --allocation-method risk_based
```

- バックテスト（プログラムから）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest

conn = init_schema("data/kabusys.duckdb")
res = run_backtest(conn, start_date=date(2022,1,1), end_date=date(2022,12,31))
# res.history, res.trades, res.metrics にアクセス可能
conn.close()
```

注意：
- 多くの処理（feature / signal / backtest）は DuckDB 内の特定テーブルに依存します。事前に prices_daily, raw_financials, features, ai_scores, market_regime, market_calendar 等のデータを準備してください。
- バックテストでは元 DB を直接更新しないよう、エンジン側でインメモリ接続に必要なデータをコピーして実行します。

---

## ディレクトリ構成（主なファイル）

以下は主要なパッケージ構成（抜粋）です。実際のツリーはリポジトリに合わせてください。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数設定読み込み・管理
  - data/
    - jquants_client.py       — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py       — RSS ニュース収集・DB 保存・銘柄抽出
    - (schema.py)             — DB スキーマ初期化（別ファイル想定）
    - calendar_management.py  — 取引日取得等（参照あり）
    - stats.py                — 正規化ユーティリティ（参照あり）
  - research/
    - factor_research.py      — Momentum / Volatility / Value ファクター計算
    - feature_exploration.py  — IC, forward returns, summary 等
  - strategy/
    - feature_engineering.py  — features 作成・正規化
    - signal_generator.py     — final_score 計算と signals 生成
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数計算・制約処理
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py               — バックテスト全体ループ
    - simulator.py            — 約定・ポートフォリオ管理の擬似実行器
    - metrics.py              — バックテスト評価指標
    - run.py                  — CLI エントリポイント
    - clock.py                — 模擬時計（将来用途）
  - execution/                — 発注層（API 実装箇所：骨格）
  - monitoring/               — 監視・アラート（骨格）

---

## 開発・テストに関する補足

- .env の自動読み込みは `kabusys.config` 内で行われます。テストや CI などで自動読み込みを避けたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ネットワーク呼び出し部分（J-Quants / RSS）はレート制御・リトライ・SSRF対策などを実装しています。ユニットテストでは HTTP 層をモックしてください（コード内でもモック可能な設計になっています）。
- DuckDB のスキーマ初期化関数（`init_schema`）を用いてテスト用のメモリ DB (`":memory:"`) を作成できます。

---

## 参考・注意事項

- 本ライブラリは「研究→ETL→シグナル→発注→監視」というフローのコア部分を提供しますが、実際の発注（kabuステーション等）や Slack 通知などの統合は別途実装・設定が必要です。
- 本番運用時は設定値（特に API トークン、パスワード）の管理とアクセス制御に十分注意してください。
- バックテスト結果は過去データに対する評価であり、将来のパフォーマンスを保証するものではありません。レジーム判定・手数料・スリッページ等のパラメータは現実的な値で検証してください。

---

もし README に追加したい具体的なセクション（例：API の詳細仕様、DB スキーマ、より詳しい開発手順や CI 設定例など）があれば教えてください。必要に応じて追記します。