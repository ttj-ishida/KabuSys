# KabuSys

日本株向けの自動売買システム用ライブラリ（モジュール群）。データ取得・ETL、特徴量作成、シグナル生成、ニュース収集、監査ログ・スキーマ管理など、戦略運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は J-Quants などの外部 API から市場データを取得して DuckDB に保存し、
研究 → 特徴量生成 → シグナル生成 → 発注（別途実装）へつなぐための基盤モジュール群です。

主な設計方針：
- DuckDB をデータプラットフォームに利用（ローカル / インメモリ双方対応）
- ETL / 保存処理は冪等（ON CONFLICT / トランザクション）を意識
- ルックアヘッドバイアス対策（計算は target_date 時点の情報のみを使用）
- 外部 API のレート制御、リトライ、トークン自動リフレッシュ等の頑健な実装
- ニュース収集は SSRF / XML Bomb / 大容量レスポンス対策を施した安全設計

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足 / 財務 / 市場カレンダー）
  - safe に DuckDB へ保存する save_* 関数群（冪等）
- ETL パイプライン
  - run_daily_etl: カレンダー、株価、財務の差分取得 + 品質チェック
  - 単体ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- DuckDB スキーマ管理
  - init_schema / get_connection によるスキーマ初期化と接続
  - Raw / Processed / Feature / Execution 層のテーブル定義
- 特徴量（ファクター）計算・正規化
  - research モジュール: calc_momentum / calc_volatility / calc_value 等
  - strategy.feature_engineering.build_features: ファクター統合・Zスコア正規化・features への UPSERT
- シグナル生成
  - strategy.signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL を生成・signals テーブルへ書き込み
- ニュース収集
  - RSS 取得・前処理・raw_news 保存・銘柄抽出・news_symbols 紐付け
- カレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（audit）
  - signal_events / order_requests / executions など、トレーサビリティを残すテーブル群
- 共通ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - 設定管理（環境変数の自動ロード・必須チェック）

---

## 前提 / 必要パッケージ

- Python 3.10+
- 必須ライブラリ（代表）:
  - duckdb
  - defusedxml
- 標準ライブラリを多用する設計のため、依存は最低限に抑えられています。

インストール例（仮に requirements.txt を用意する場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# もしパッケージ化されている場合
# pip install -e .
```

※ プロジェクト配布形態に応じて pyproject.toml / setup.cfg があれば `pip install -e .` を推奨します。

---

## 環境変数（設定）

自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD に依存しない探索）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要な環境変数（Settings 参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

例 `.env`（最小）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成 & 依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # その他必要パッケージがあれば追加
   ```

3. 環境変数を設定（.env をプロジェクトルートに作成）
   - README 上の「環境変数」節を参考に `.env` を作成

4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   # settings.duckdb_path は環境変数で上書き済み
   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（例）

以下は主要なユースケースのサンプルコード例です。

- 日次 ETL（市場カレンダー、株価、財務、品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 特徴量生成（features テーブルへの upsert）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
n = build_features(conn, target_date=date.today())
print(f"build_features: {n} 銘柄処理")
```

- シグナル生成（features と ai_scores を統合して signals へ）
```python
from datetime import date
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"generate_signals: total signals = {total}")
```

- ニュース収集（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄コードセット (例: {"7203","6758",...})。None を渡すと紐付け処理をスキップ。
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
saved = calendar_update_job(conn)
print(f"calendar_update_job: saved={saved}")
```

---

## よくある設定上の注意

- 自動環境読み込み:
  - パッケージ起点の親ディレクトリから `.git` または `pyproject.toml` を探索して `.env` を自動ロードします。テストや特殊ケースでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- 環境検証:
  - Settings は KABUSYS_ENV や LOG_LEVEL の妥当性チェックを行います。不正な値は ValueError を投げます。
- DuckDB パス:
  - デフォルトは `data/kabusys.duckdb`。init_schema は親ディレクトリを自動生成します。
- API トークンの自動リフレッシュ:
  - J-Quants client はリフレッシュトークンから id token を取得しキャッシュ・自動更新します。401 を検知して 1 回だけリフレッシュしリトライします。

---

## ディレクトリ構成（主要ファイル）

下記は src/kabusys 以下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py               — DuckDB スキーマ定義・初期化
    - jquants_client.py       — J-Quants API クライアント（fetch/save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - news_collector.py       — RSS 収集・解析・保存
    - calendar_management.py  — カレンダー管理 / ジョブ
    - audit.py                — 監査ログ用スキーマと初期化
    - features.py             — zscore_normalize 再エクスポート
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - (その他: quality モジュール想定)
  - research/
    - __init__.py
    - factor_research.py      — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py  — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py  — build_features（features テーブル作成）
    - signal_generator.py     — generate_signals（BUY/SELL 判定）
  - execution/                — 発注・約定・ブローカー連携層（placeholder）
  - monitoring/               — 監視・メトリクス用（placeholder）

※ 実装コメントやドキュメント（StrategyModel.md, DataPlatform.md 等）に従って設計されています（リポジトリに同梱されている想定）。

---

## 開発者向け情報 / テスト時のヒント

- 単体テスト・統合テストでは DuckDB のインメモリ DB（db_path=":memory:"）を使用すると簡便です。
- 環境変数の自動ロードを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を外部から設定してください。
- news_collector のネットワーク呼び出しは _urlopen をモックすればテストが容易です。
- J-Quants の API 呼び出しは id_token を引数で注入できるため、テスト用トークンやモックを渡して制御できます。

---

## ライセンス / 貢献

リポジトリルートにある LICENSE を参照してください。バグ報告や改善提案は Issues / Pull Requests で受け付けます。

---

README は必要に応じてプロジェクト特有のインストール手順（packaging、CI、requirements.txt）や運用ノウハウ（運用時の cron / scheduler、バックアップ方針、モニタリング宛先）を追加してください。