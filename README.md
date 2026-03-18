# KabuSys

日本株向け自動売買・データプラットフォーム（KabuSys）のリポジトリ内ドキュメントです。  
この README はコードベースの主要概念、セットアップ手順、簡単な使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買・データ基盤ライブラリです。  
主な目的は以下：

- J-Quants API からの市場データ（株価・財務・マーケットカレンダー等）取得と DuckDB への蓄積
- RSS ニュース収集と記事の前処理・銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 特徴量（モメンタム、ボラティリティ、バリュー等）の計算（Research 用）
- ETL パイプライン（差分更新・バックフィル対応）
- 発注・監視・監査ログのスキーマ整備（発注実装は別途拡張）

設計方針として、DuckDB を中心に SQL と Python を組み合わせ、外部ライブラリ依存は最小限に抑えています（ただし DuckDB / defusedxml 等は使用しています）。  
本コードベースでは、本番発注 API に直接アクセスする箇所は原則無く、データ処理・研究・監査のための基盤を提供します。

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み、必須値チェック）
- J-Quants API クライアント
  - 日足（OHLCV）・財務・マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）とリトライ・トークン自動リフレッシュを実装
  - DuckDB への冪等保存（ON CONFLICT で更新）
- ニュース収集モジュール（RSS）
  - URL 正規化・トラッキングパラメータ除去・SSRF 対策・gzip サイズ上限
  - 記事ID は正規化 URL の SHA-256 先頭 32 文字
  - raw_news, news_symbols への冪等保存
- DuckDB スキーマ定義 / 初期化（raw / processed / feature / execution / audit 層）
- ETL パイプライン（差分更新、バックフィル、カレンダー先読み）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- Research ツール
  - 将来リターン計算、IC（スピアマン）計算、ファクターサマリー
  - Momentum / Volatility / Value などのファクター計算
  - Z スコア正規化ユーティリティ
- 監査ログ用スキーマ（signal -> order_request -> execution のトレース設計）

---

## 前提 / 必要環境

- Python 3.10+
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全対策）
- その他標準ライブラリ（urllib, datetime, logging 等）

（プロジェクトのパッケージ管理（pyproject.toml / requirements.txt）に従ってインストールしてください。以下は基本的な例です）

---

## セットアップ手順（簡易）

1. リポジトリをクローンして移動

```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境を作成・有効化（例: venv）

```bash
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows (PowerShell や CMD)
```

3. 必要パッケージをインストール（最小セット）

```bash
pip install duckdb defusedxml
# 追加でテストや開発用パッケージがあればインストール
```

4. 環境変数の設定

ルートに `.env`（および任意で `.env.local`）を置くと自動で読み込まれます。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

必要な環境変数（例）:
- JQUANTS_REFRESH_TOKEN  # J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      # kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN        # Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       # 通知先 Slack チャンネルID（必須）
- DUCKDB_PATH (任意, default: data/kabusys.duckdb)
- SQLITE_PATH (任意, default: data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live)（任意, default: development）
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（任意）

例 `.env`（テンプレート）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB スキーマ初期化

Python REPL やスクリプトから schema.init_schema を呼んで DB を初期化します。

```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# conn は duckdb の接続オブジェクト
```

---

## 使い方（主要ユースケースの例）

ここでは代表的な使い方を示します。実行は Python スクリプトまたは REPL で行ってください。

- ETL（日次パイプライン）の実行

```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

# DB 初期化（未初期化なら）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL（デフォルトは今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- J-Quants から日足を取得して保存（個別実行）

```python
from kabusys.data import jquants_client as jq
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

- RSS ニュース収集ジョブ（全ソース）

```python
from kabusys.data import news_collector as nc
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")

# known_codes: 銘柄コードの集合（任意）
known_codes = {"7203", "6758", "6501"}

results = nc.run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- Research（特徴量計算 / IC 計算）

```python
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.research import calc_forward_returns, calc_ic, factor_summary
from kabusys.data import stats as data_stats
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# 将来リターンを計算
fwd = calc_forward_returns(conn, target)

# 例: mom_1m と fwd_1d の IC
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

# Z スコア正規化
normalized = data_stats.zscore_normalize(mom, ["mom_1m", "ma200_dev"])
```

- データ品質チェック（ETL 後に呼び出し）

```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=target, reference_date=target)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 注意点 / 運用上のポイント

- 環境変数は `.env` / `.env.local` から自動ロードされます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定してください。
- J-Quants API クライアントは内部でレートリミット（120 req/min）とリトライを管理します。大量の並列リクエストは避けてください。
- DuckDB の INSERT は多くの場所で ON CONFLICT を利用して冪等性を担保しています。
- RSS フィードの取得では SSRF 対策（スキーム検証・プライベートIPブロック・リダイレクト検査）やサイズ上限チェックを実施しています。
- 本リポジトリはデータ収集・研究基盤を提供します。実際の発注処理を行う場合は、発注・ブローカー API 部分の追加実装と、十分なテスト・リスク管理が必要です。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要ファイルと役割の一覧です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py
      - RSS 収集、記事前処理、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（run_daily_etl 他）
    - features.py
      - features 用インターフェース（zscore の再エクスポート）
    - calendar_management.py
      - market_calendar の管理、営業日判定（next/prev/is_trading_day 等）
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の DDL 初期化
    - etl.py
      - ETL オブジェクトの公開（ETLResult の再エクスポート）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - research/
    - __init__.py
      - 主要関数をエクスポート（calc_momentum 等）
    - feature_exploration.py
      - forward return / IC / summary / rank
    - factor_research.py
      - momentum / volatility / value の計算
  - strategy/
    - __init__.py
    - （戦略モデル実装用のプレースホルダ）
  - execution/
    - __init__.py
    - （発注実装用のプレースホルダ）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連のプレースホルダ）

---

## テスト・開発時のヒント

- 自動環境読み込みを無効化してテスト用設定を注入する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB のインメモリ DB を利用して単体テストを行う:
  - schema.init_schema(":memory:")
- ネットワーク外部依存（J-Quants / RSS）をモックしてテストする。特に jquants_client._request や news_collector._urlopen を差し替えると容易になります。

---

もし README に追加してほしい具体的な内容（CI, デプロイ手順、サンプル設定ファイル、拡張方法のガイドなど）があれば教えてください。必要に応じて追記します。