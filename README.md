# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
データ取得（J-Quants）、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、データ品質チェック、特徴量計算、監査ログなど、戦略実装から運用までを想定したツール群を含みます。

主に研究用途（feature exploration / factor research）とデータパイプライン（ETL・カレンダー管理・ニュース収集）に重点を置いて実装されています。発注関連や実運用のブリッジも想定した構成ですが、Research モジュールは本番口座や発注 API にはアクセスしない設計です。

---

## 主な機能一覧

- 環境設定の自動ロード（.env / .env.local / OS 環境変数）
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レートリミット遵守（120 req/min）、リトライ、トークン自動リフレッシュ
- DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS → 正規化 → DuckDB 保存、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day、夜間更新ジョブ）
- 監査ログ（signal / order_request / execution のトレーサビリティ）
- 研究向けファクター計算
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Spearman rank）評価、ファクター統計サマリー
- 汎用統計ユーティリティ（Z-score 正規化 等）

---

## 必要環境 / 依存パッケージ

最低限必要な Python ランタイムやライブラリ（抜粋）:

- Python 3.9+
- duckdb
- defusedxml

（標準ライブラリのみで実装されている箇所も多いですが、DuckDB 接続や XML 安全パーサのため上記依存があります。）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを editable にインストールする場合（プロジェクトルートで）
pip install -e .
```

---

## 環境変数（.env）

config.Settings が必要とする主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意（デフォルトがある / 推奨設定）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化する（テスト用）
- KABUS_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

プロジェクトルートに `.env` / `.env.local` を置くと、自動的にロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化可能）。

簡易 `.env.example`（README 用サンプル）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローンし、プロジェクトルートに移動。
2. Python 仮想環境を作成・有効化。
3. 依存ライブラリをインストール（duckdb, defusedxml 等）。
4. `.env` を作成して必要な環境変数を設定。
5. DuckDB スキーマを初期化（下記参照）。

例:
```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 必要に応じてパッケージをインストール
pip install -e .
# .env を作成（上記参照）
```

データベース初期化（Python から）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# 監査ログ用 DB を別途初期化する場合
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要なユースケース）

以下は代表的な操作例です。実運用やジョブ化は用途に応じてスクリプト化してください。

1) 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")
# ETL 実行（今日を対象）
result = run_daily_etl(conn)
print(result.to_dict())
```

2) ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効コードのセット（例: {'7203','6758', ...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
print(res)
```

3) ファクター / 研究用ユーティリティの利用例
```python
from datetime import date
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
t = date(2024, 1, 31)
momentum_records = calc_momentum(conn, t)
forward_records = calc_forward_returns(conn, t, horizons=[1,5,21])
# 例: mom_1m と fwd_1d の IC を計算
ic = calc_ic(momentum_records, forward_records, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

4) マーケットカレンダー関係
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day
conn = get_connection("data/kabusys.duckdb")
d = date(2024, 1, 1)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- Research モジュールはデータ参照のみで実行口座や発注 API にはアクセスしません（安全に分析できます）。
- J-Quants クライアントは rate limit を守り、トークン自動更新やリトライ処理を実装しています。

---

## ディレクトリ構成

主要なファイル／モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得・保存関数）
    - news_collector.py         — RSS 収集・前処理・DB 保存
    - schema.py                 — DuckDB スキーマ定義 & init_schema / get_connection
    - stats.py                  — 統計ユーティリティ（zscore_normalize）
    - pipeline.py               — ETL パイプライン（差分取得・品質チェック）
    - etl.py                    — ETLResult の公開インターフェース
    - quality.py                — データ品質チェック
    - calendar_management.py    — マーケットカレンダー管理 / 更新ジョブ
    - audit.py                  — 監査ログ（signal / order_request / executions）
    - features.py               — 特徴量ユーティリティ（再エクスポート）
  - research/
    - __init__.py               — 研究用関数の公開
    - feature_exploration.py    — 将来リターン / IC / サマリー等
    - factor_research.py        — momentum / volatility / value 等の計算
  - strategy/                   — 戦略関連（空パッケージ：拡張ポイント）
  - execution/                  — 発注/ブローカー連携（空パッケージ：拡張ポイント）
  - monitoring/                 — 監視 / メトリクス（空パッケージ：拡張ポイント）

プロジェクトルートに以下を配置する想定:
- pyproject.toml / setup.cfg / requirements.txt（パッケージ管理）
- .env / .env.local（環境変数）
- data/ (デフォルトの DB ファイル保存先)

---

## 実運用上の注意・設計上のポイント

- J-Quants API: レート制限・リトライ・トークンリフレッシュの考慮あり。ID トークンはモジュールレベルでキャッシュされます。
- DuckDB: スキーマは冪等に作成され、ON CONFLICT や INSERT ... RETURNING を多用してデータ整合性を保ちます。
- ニュース収集: SSRF 対策や受信サイズ上限（10MB）、XML パース時の安全対策（defusedxml）を実装しています。
- 品質チェック: Fail-Fast ではなく、各チェックは全件を調べて問題リストを返す設計。呼び出し元でエラー重大度に応じた処理を行ってください。
- 監査ログ: order_request_id を冪等キーとして扱い、トレース性を確保。タイムゾーンは UTC 想定。

---

## 拡張ポイント / 今後の作業

- strategy / execution / monitoring ディレクトリは拡張ポイント：ここに取引戦略、証券会社 API 連携、稼働監視コードを実装できます。
- 特徴量・AI スコアの拡張：features / ai_scores テーブルへの投入パイプラインの追加。
- Slack 通知やアラート連携（config に Slack トークンがあるため、ジョブ結果の通知に利用可能）。

---

不明点や特定の使い方（例: 監査スキーマの詳細、ETL のジョブ化、Kabu ステーション連携実装例など）について詳しいコード例が必要であれば、用途に合わせたサンプルを作成します。どの部分を詳しく知りたいか教えてください。