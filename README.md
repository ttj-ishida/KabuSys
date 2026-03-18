# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ群です。  
データ収集（J-Quants）、DuckDBベースのデータスキーマ、ETLパイプライン、ニュース収集、ファクター計算・リサーチユーティリティ、監査ログなどを含みます。

- パッケージ名: kabusys
- バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## 概要

KabuSys は日本株の自動売買に必要なデータ基盤・研究・実行周りの共通ロジックを提供するライブラリです。主に以下のレイヤーを備えます。

- Data layer: J-Quants API クライアント、RSSニュース収集、DuckDBスキーマ定義、ETLパイプライン、データ品質チェック
- Research layer: ファクター計算（Momentum / Value / Volatility 等）、将来リターン計算、IC計算、統計ユーティリティ
- Execution / Audit: 発注・約定・監査ログのスキーマ設計（DuckDB）
- 設定管理: .env / 環境変数読み込み（自動ロード対応）

設計上の特徴:
- DuckDB をデータベースに利用（ファイル / :memory: に対応）
- J-Quants API のレート制御、再試行、トークン自動リフレッシュを実装
- RSS ニュース収集における SSRF / XML ボム対策、トラッキングパラメータ除去、記事IDの冪等化
- ETL は差分更新・バックフィル・品質チェックを備える

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
  - 必須キーの取得（ValueError を送出）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- J-Quants データ取得（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ、JPXカレンダーの取得（ページネーション対応）
  - レートリミット（120 req/min）・リトライ・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）

- ETL / パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日を基に自動算出）
  - run_daily_etl によるカレンダー取得→株価取得→財務取得→品質チェックの一連処理
  - ETLResult で集約された実行結果を返す

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit レイヤーのテーブル定義と初期化
  - init_schema, get_connection を提供

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、テキスト前処理、記事ID生成、raw_news への冪等保存
  - 銘柄コード抽出（4桁数字マッチ）と news_symbols への紐付け
  - SSRF・XML 脅威対策・レスポンスサイズ制限

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue を返して呼び出し側で判断可能

- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value 等のファクター計算
  - calc_forward_returns（将来リターン）、calc_ic（スピアマンρ）、factor_summary、rank、zscore_normalize

- 統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（クロスセクションの Z スコア正規化）

---

## セットアップ手順

前提: Python 3.10+（typing の `X | None` 等を使用しているため）

1. リポジトリをクローン／ワークスペースに配置

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - その他プロジェクト固有の依存があれば requirements を参照してインストールしてください。

4. 環境変数 / .env
   プロジェクトルートに .env（および .env.local）を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば読み込みを無効化できます）。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot Token（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development|paper_trading|live), デフォルト development
   - LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（サンプル）

基本的な DB 初期化と日次 ETL の実行例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DuckDB を初期化（ファイルがなければ作成）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn)

print(result.to_dict())
```

ニュース収集の実行例:

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# DEFAULT_RSS_SOURCES を使うか、自前の dict を渡す
res = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
print(res)  # ソースごとの新規保存件数を返す
```

リサーチ・ファクター計算の例:

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)

# モメンタムを計算
mom = calc_momentum(conn, target)

# 将来リターンを計算
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# IC（Spearman ρ）を計算（例: mom_1m と fwd_1d）
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
print("IC:", ic)

# Z スコア正規化
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

監査ログスキーマの初期化:

```python
from kabusys.data.audit import init_audit_db

# 監査ログ用 DB を別ファイルに分けたい場合
audit_conn = init_audit_db("data/audit.duckdb")
```

設定値の参照:

```python
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
is_live = settings.is_live
```

自動環境読み込みを無効化したい（テスト時など）:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから Python を起動します。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なモジュールと簡易説明を示します（src/kabusys 以下）:

- __init__.py
  - パッケージのエントリ。__version__ = "0.1.0"

- config.py
  - 環境変数 / .env 自動読み込み、Settings クラス（jquants / kabu / Slack / DB パス等）

- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント、取得関数と DuckDB 保存ユーティリティ
  - news_collector.py: RSS フィードの取得・前処理・保存、銘柄抽出
  - schema.py: DuckDB スキーマ定義と init_schema / get_connection
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - features.py: features インターフェース（zscore_normalize 再エクスポート）
  - calendar_management.py: market_calendar 管理・営業日ロジック
  - audit.py: 監査ログ用スキーマ初期化（order_requests / executions / signal_events）
  - etl.py: 公開型 ETLResult 再エクスポート
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）

- research/
  - __init__.py: 主要リサーチ関数の再エクスポート
  - feature_exploration.py: 将来リターン計算、IC、factor_summary、rank
  - factor_research.py: calc_momentum / calc_value / calc_volatility

- strategy/
  - __init__.py（将来的な戦略モデルやシグナル生成を想定）

- execution/
  - __init__.py（発注ロジック、kabuステーション連携を想定）

- monitoring/
  - __init__.py（監視・メトリクス用、現状空）

---

## 注意事項 / 運用上のポイント

- 環境変数の必須項目が欠如すると Settings プロパティで ValueError が出ます（明示的なエラーとして早期に検出）。
- J-Quants API へのリクエストはレート制御とリトライを行いますが、運用時は適切な API キー管理とログ監視を行ってください。
- DuckDB の ON CONFLICT を利用して冪等性を担保していますが、ETL の外部からの直接挿入などでデータ不整合が発生する可能性があるため、品質チェック（data.quality.run_all_checks）の定期実行を推奨します。
- news_collector は外部 URL を扱うため、SSR F・XML 攻撃対策を実装しています。テスト時に HTTP モックを使って安全に振る舞いを検証してください。
- 本ライブラリは「研究（Research）とデータ基盤」を主目的とし、実際に証券会社へ発注するコードは別モジュール（execution）で接続実装する想定です。実運用での資金管理やリスク管理は別途厳密な検証が必要です。

---

## ライセンス / コントリビューション

（ここにプロジェクト固有のライセンスや貢献方法を記載してください。README のテンプレートでは省略しています。）

---

必要であれば、README に動的な使い方（CLI、cron ジョブ例、Dockerfile、CI 設定、テスト方法）を追加できます。どの部分を詳細に載せたいか教えてください。