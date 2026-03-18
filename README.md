# KabuSys

日本株向けの自動売買・データプラットフォーム用モジュール群です。  
データ取得（J-Quants）、DuckDB ベースのスキーマ設計、ETL パイプライン、ニュース収集、ファクター計算（リサーチ用）、品質チェック、監査ログなどの機能を備えています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株のデータ取得から特徴量生成、品質管理、監査ログまでをカバーするモジュール群です。設計方針としては以下を重視しています。

- DuckDB を中心としたシンプルかつ冪等なデータ保存
- J-Quants API を利用した差分取得（レート制限・リトライ・トークン自動更新対応）
- ETL の品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と銘柄紐付け
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）と IC 計算
- 監査ログ用スキーマ（シグナル → 発注 → 約定 のトレース）

注意: このリポジトリ内の多くのモジュールは「データ処理 / リサーチ」領域を扱い、本番注文発行（ブローカー接続）に直接アクセスするコードは含まれません。運用・実際の発注はリスク管理や環境に応じて別途実装してください。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制限、リトライ、トークン自動更新、ページネーション）
  - news_collector: RSS 収集、前処理、DuckDB へ冪等保存、銘柄抽出・紐付け
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分更新・バックフィル・品質チェック）
  - calendar_management: JPX カレンダーの管理・営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用テーブル定義と初期化
  - stats / features: 統計ユーティリティ（Z スコア正規化 等）
- research/
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
  - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算
- config: 環境変数/設定読み込み（.env 自動読み込み、必須キー検査）
- strategy / execution / monitoring: パッケージ階層を用意（実装は配置想定）

---

## 前提 / 必要環境

- Python 3.10+
  - 型注釈（PEP 604）や一部書式に合わせて 3.10 以上を推奨します。
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS フィード）

インストール例（開発環境）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# パッケージをローカル開発モードでインストールする場合
pip install -e .
```

（パッケージ配布用の setup/pyproject は別途用意してください）

---

## 環境変数 / .env の設定

プロジェクトルートの `.env` / `.env.local` を自動でロードします（環境変数が優先）。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数（config.Settings から）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード（将来的な利用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID

その他（任意/デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — 実行環境（デフォルト: development）
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視等で使う SQLite パス（デフォルト: data/monitoring.db）

例 `.env`:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンし仮想環境を作成

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発時
pip install -e .
```

2. 環境変数を設定（.env ファイル作成）

3. DuckDB スキーマ初期化（Python REPL またはスクリプト）

```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

（監査ログ用スキーマを追加する場合）

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

---

## 基本的な使い方（コード例）

- 日次 ETL を実行する

```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# 初回は init_schema を使うのが安全
conn = init_schema("data/kabusys.duckdb")

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブを実行する

```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"6501","7203","6758"}  # 既知銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- 研究用ファクター計算・IC 計算

```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
t = date(2024, 1, 31)

mom = calc_momentum(conn, t)           # モメンタムファクター
fwd = calc_forward_returns(conn, t)    # 将来リターン（fwd_1d 等）
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
summary = factor_summary(mom, ["mom_1m", "mom_3m", "ma200_dev"])
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- J-Quants データ取得（クライアント直接利用）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
token = get_id_token()  # settings.jquants_refresh_token を利用して idToken を取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

---

## 注意事項・運用メモ

- J-Quants API はレート制限（120 req/min）に従うため、jquants_client は内部でスロットリングを行います。
- jquants_client は 401 受信時に refresh token から id token を自動で更新してリトライします。
- news_collector は RSS の SSRF 対策、受信サイズ制限、gzip 解凍後のバリデーション等を行います。
- DuckDB の INSERT は多くの関数で ON CONFLICT を用いて冪等的に保存します。
- テスト時は自動 .env ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 実際に発注を行うモジュール（execution/strategy）は本リポジトリ上での実装を想定した骨組みがあるものの、ブローカー接続の実装・設定は慎重に行ってください。KABUSYS_ENV に応じて paper_trading/live を切り替えられる設計になっています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数 / 設定管理（.env 自動ロード）
    - data/
      - __init__.py
      - jquants_client.py              — J-Quants API クライアント（取得・保存）
      - news_collector.py              — RSS 収集・前処理・DB保存・銘柄抽出
      - schema.py                      — DuckDB スキーマ定義 / init_schema / get_connection
      - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py         — JPX カレンダー管理・営業日ユーティリティ
      - quality.py                     — データ品質チェック
      - etl.py                         — ETL 公開インターフェース（ETLResult 再エクスポート）
      - audit.py                       — 監査ログスキーマ（signal/events/order_requests/executions）
      - stats.py                       — 統計ユーティリティ（zscore_normalize）
      - features.py                    — features の公開インターフェース
    - research/
      - __init__.py
      - feature_exploration.py         — 将来リターン、IC、rank、factor_summary
      - factor_research.py             — momentum/value/volatility の計算
    - strategy/                         — 戦略層（エントリポイントを想定）
      - __init__.py
    - execution/                        — 発注 / ブローカー連携（構成用）
      - __init__.py
    - monitoring/                       — 監視用モジュール（未実装のプレースホルダ）
      - __init__.py

---

## 開発・テストに関する補足

- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効にすることができます。
- DuckDB を使ったユニットテストは ":memory:" を渡してインメモリ DB を利用すると高速です。
- news_collector のネットワーク呼び出しはモックしやすい設計（_urlopen の置換等）になっています。
- jquants_client のネットワーク処理は urllib を使っているため、テスト時は HTTP サーバのスタブや urllib のモンキーパッチで制御してください。

---

この README は本コードベースの概要と利用方法の最小限のガイドです。詳細な設計（DataPlatform.md / StrategyModel.md 等）や追加の運用手順がある場合は、別途ドキュメントを参照してください。必要であれば README に追記する内容（CI の設定例、サンプルワークフロー、追加の環境変数一覧など）を教えてください。