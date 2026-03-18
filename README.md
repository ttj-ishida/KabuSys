# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）の README です。  
このリポジトリはデータ収集（J-Quants）→ ETL → 特徴量生成 → 研究（ファクター評価）→ 発注／監査までを想定したモジュール群を提供します。

---

目次
- プロジェクト概要
- 主な機能一覧
- システム要件
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（.env）
- ディレクトリ構成（主要ファイル）
- よくある操作例

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けのユーティリティ群です。主に以下を目的とします。

- J-Quants API など外部データソースからのデータ収集（株価日足 / 財務 / マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義・永続化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース（RSS）収集と記事→銘柄紐付け
- ファクター計算・探索（モメンタム、ボラティリティ、バリュー、IC 等）
- 発注／監査（テーブル定義とトレーサビリティ）を支援するユーティリティ

設計方針として、可能な限り副作用を少なくし DuckDB や標準ライブラリのみで安全に動くことを目指しています（外部依存は最小限）。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API との通信、ページネーション／リトライ／レートリミット対応、DuckDB への保存（冪等）
  - schema: DuckDB のスキーマ定義と初期化関数
  - pipeline: 日次 ETL フロー（カレンダー → 株価 → 財務 → 品質チェック）の実行
  - news_collector: RSS 取得 → 前処理 → raw_news 保存 → 銘柄抽出
  - quality: データ品質チェック（欠損、スパイク、重複、日付整合）
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - audit: 発注〜約定の監査ログテーブル定義・初期化
  - stats: Zスコア正規化等の統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value の計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- config: .env 自動ロード、Settings オブジェクト（環境変数管理）
- execution / strategy / monitoring: 発注・戦略・監視関連の名前空間（拡張ポイント）

---

## システム要件

- Python 3.10 以上（型アノテーションに | を使用）
- 必須パッケージ（最低限）
  - duckdb
  - defusedxml
- （任意）J-Quants API を使う場合はインターネット接続と J-Quants のリフレッシュトークンが必要

インストール例（仮想環境を推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージを開発モードでインストールする場合（setup.py/pyproject.toml がある前提）
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作る（推奨）
3. 依存ライブラリをインストール（上記参照）
4. 環境変数を設定（.env ファイルをプロジェクトルートに置くと自動ロードされます — 詳細は後述）
5. DuckDB スキーマを初期化

例: DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してテーブルを作る
conn.close()
```

監査ログ専用 DB を初期化する例:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
audit_conn.close()
```

---

## 簡単な使い方（コード例）

※ 下記は Python スクリプト / REPL での利用例です。

- 日次 ETL を実行する（J-Quants トークンは settings から取得）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl
import datetime

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=datetime.date.today())
print(result.to_dict())
conn.close()
```

- ニュース収集を行う（既に DuckDB 接続を初期化しておく）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
conn = init_schema("data/kabusys.duckdb")
# known_codes: 抽出時に有効とみなす銘柄コードセット（例えば取引銘柄）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
conn.close()
```

- 研究用・ファクター計算
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
from kabusys.data.schema import get_connection
import datetime
conn = get_connection("data/kabusys.duckdb")
d = datetime.date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m","mom_3m","ma200_dev"])
conn.close()
```

- J-Quants から直接データを取得して保存（高度な用途）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection
from kabusys.config import settings
from datetime import date

conn = get_connection("data/kabusys.duckdb")
recs = fetch_daily_quotes()  # settings.jquants_refresh_token を内部で使用
count = save_daily_quotes(conn, recs)
conn.close()
```

---

## 環境変数（.env）

config.Settings によって以下の環境変数が参照されます。プロジェクトルートに .env / .env.local があれば自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（Settings._require によって未設定は例外）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション等の API パスワード（発注連携を使う場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — Slack 通知チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

注意:
- .env のパースはかなり厳密に実装されています。クォート、エスケープ、コメントなどの処理は config モジュール準拠で扱ってください。

---

## ディレクトリ構成（主要ファイル）

リポジトリは src 配下にパッケージ `kabusys` を持ちます。主要ファイルは以下の通り（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  ← 環境変数管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py  ← J-Quants API クライアント（fetch/save）
    - news_collector.py  ← RSS 収集・解析・DB 保存
    - schema.py          ← DuckDB スキーマ定義・init_schema
    - pipeline.py        ← ETL パイプライン（run_daily_etl）
    - quality.py         ← データ品質チェック
    - calendar_management.py ← カレンダー管理／更新ジョブ
    - audit.py           ← 監査ログスキーマ（発注〜約定トレーサビリティ）
    - stats.py           ← zscore_normalize 等
    - features.py        ← features の公開インターフェース
    - etl.py             ← ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py ← Momentum/Volatility/Value 等の計算
    - feature_exploration.py ← 将来リターン・IC・統計サマリー
  - strategy/           ← 戦略関連（拡張ポイント）
  - execution/          ← 発注実装の拡張ポイント
  - monitoring/         ← 監視関連（拡張ポイント）

データベース上の主なテーブル（抜粋）:
- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signal_queue, orders, trades, positions, portfolio_performance
- signal_events, order_requests, executions （監査ログ）

---

## よくある操作例・ヒント

- DuckDB の初期化は一度で良い（既にテーブルがあればスキップされるため冪等）。
- ETL は日次バッチで run_daily_etl を呼ぶのが想定。内部でカレンダーを先に更新して営業日を調整します。
- ニュース収集は外部 RSS を取得するためネットワーク要件と SSRF 対策が組み込まれています。大量取得時はタイムアウト・レスポンスサイズ制限に注意。
- J-Quants API はレート制限（120 req/min）を順守する実装になっていますが、大規模バッチでは API 側の制約に注意してください。
- 品質チェック（quality.run_all_checks）は ETL 後に実行して問題を検出し、重大な問題（error）があるかどうかを判断できます（ETLResult.has_quality_errors）。
- Settings は .env を自動読み込みしますが、テストや CI で自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この README はコード内のドキュメント文字列（docstring）と設定管理ロジックを元に作成しました。実運用時は .env.example の整備、CI ジョブ、実際の発注ロジック（execution レイヤ）の実装・テスト・バックテストを行ってください。質問や追加したいドキュメント項目があればお知らせください。