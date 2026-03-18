# KabuSys

日本株向けの自動売買プラットフォームのライブラリ（KabuSys）。データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログなど、戦略の研究〜本番運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群から構成されています。

- データ取得（J-Quants API）と保存（DuckDB）
- 市場カレンダー管理
- ETL（差分取得・バックフィル・品質チェック）
- ニュース（RSS）収集と記事→銘柄紐付け
- ファクター／特徴量計算（モメンタム、バリュー、ボラティリティ等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 研究用ユーティリティ（IC 計算、Zスコア正規化 等）

設計方針として、DuckDB を中核にして冪等な保存（ON CONFLICT）や Look-ahead bias の防止、API レート制御、ETL の堅牢性を重視しています。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API から日足・財務・カレンダーをページネーション対応で取得
  - レートリミット、リトライ、401 トークン自動リフレッシュを実装
  - DuckDB への冪等保存（save_* 関数）
- data/pipeline
  - 日次 ETL パイプライン（run_daily_etl）
  - 差分取得 / バックフィル / 品質チェックの統合
- data/schema, data/audit
  - DuckDB 用スキーマ定義と初期化（init_schema / init_audit_db）
  - 監査ログテーブル（signal_events / order_requests / executions）
- data/news_collector
  - RSS フィード取得、前処理、ID生成、DuckDB への冪等保存
  - SSRF 対策／gzip・サイズ制限・XML パース安全化（defusedxml）
  - 記事から銘柄コード抽出、news_symbols への紐付け
- data/quality
  - 欠損、重複、スパイク、日付不整合などの品質チェック
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- data/stats
  - Zスコア正規化ユーティリティ（zscore_normalize）

---

## 要求環境 / 依存

- Python 3.10 以上（typing の `X | Y` 構文を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# 開発時はパッケージをローカルインストールしておくと便利
# python -m pip install -e .
```

（実際の requirements.txt / pyproject.toml がある場合はそちらに従って下さい）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動で読み込まれます（自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。自動検出は .git または pyproject.toml を基準に行います。

主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

不足していると起動時にエラーとなる環境変数は Settings クラス経由で参照されます（例: settings.jquants_refresh_token）。

---

## セットアップ手順

1. リポジトリをクローン
   - （省略）

2. 仮想環境作成と依存インストール

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb defusedxml
# 任意: 開発パッケージを編集可能インストール
# python -m pip install -e .
```

3. 環境変数を用意
   - プロジェクトルートに .env を作成（.env.example を参照する想定）
   - 必須項目（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 自動ロードが不要な場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化

```python
from kabusys.data import schema
from kabusys.config import settings

# ファイルパスを明示して初期化する例
conn = schema.init_schema(settings.duckdb_path)
```

監査ログ用 DB を別途初期化する場合:

```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要ユースケース）

- 日次 ETL を実行（J-Quants から差分取得して DuckDB に保存し、品質チェックまで行う）

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data import schema, pipeline

# スキーマ初期化（既に済んでいれば不要）
conn = schema.init_schema(settings.duckdb_path)

# ETL 実行（指定日、省略時は今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集を実行（RSS 取得→raw_news 保存→既知銘柄で紐付け）

```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
# sources を指定可能、known_codes は銘柄コードセット（例: {'7203','6758',...}）
res = news_collector.run_news_collection(conn, known_codes={'7203','6758'})
print(res)
```

- ファクター（モメンタム等）計算

```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
records = calc_momentum(conn, target_date=date(2025, 1, 31))
# records は各銘柄ごとの dict リスト
```

- 将来リターン／IC 計算（研究用）

```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2025,1,31), horizons=[1,5,21])
# factor_records は calc_momentum 等の結果
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- J-Quants から直接データ取得（テストやデバッグ用）

```python
from kabusys.data import jquants_client as jq

# id_token を明示的に渡すことも可能（省略時は Settings のトークンを使って自動取得）
daily = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
```

---

## 開発者向け: 主要モジュール説明 / API のハイライト

- kabusys.config
  - Settings クラス: settings.jquants_refresh_token, settings.duckdb_path, settings.env などを提供
  - .env 自動読み込みロジック、KABUSYS_DISABLE_AUTO_ENV_LOAD

- kabusys.data.schema
  - init_schema(db_path): DuckDB の全テーブルを作成（冪等）
  - get_connection(db_path): 既存 DB 接続を返す

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

- kabusys.data.pipeline
  - run_daily_etl(conn, ...): ETL の統合エントリポイント

- kabusys.data.news_collector
  - fetch_rss(url, source): RSS 取得して記事リストを返す
  - save_raw_news(conn, articles): raw_news に保存（INSERT ... RETURNING）
  - run_news_collection(conn, sources, known_codes)

- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
  - data.stats.zscore_normalize を再エクスポート

- kabusys.data.quality
  - run_all_checks(conn, target_date, ...): 品質チェックを実行し QualityIssue リストを返す

---

## ディレクトリ構成

リポジトリ内の主要なファイル・ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/          (発注実装用モジュール群、現状ベース構成)
    - strategy/           (戦略実装用のパッケージ)
    - monitoring/         (監視・アラート関連)
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - features.py
      - stats.py
      - calendar_management.py
      - etl.py
      - quality.py
      - audit.py
    - research/
      - __init__.py
      - feature_exploration.py
      - factor_research.py

各モジュールはドキュメント文字列（docstring）で設計方針や返り値・副作用が丁寧に説明されています。まずは data/schema.init_schema() と pipeline.run_daily_etl() を動かして、ETL の一連処理と DB スキーマ動作を確認することをおすすめします。

---

## 注意事項 / 運用上のヒント

- J-Quants API のレートリミット（120 req/min）に従うよう RateLimiter を実装済みですが、外部のネットワークや API 側の制限があるため運用時はログを監視してください。
- DuckDB のファイルはバックアップを定期的に行ってください。監査ログを別 DB に分離して運用することも可能です（data.audit.init_audit_db）。
- 本コードベースは「実行・発注」部分と「研究・特徴量」部分を分離しているため、paper_trading / live など環境設定を切り替えてテスト→本番展開がしやすくなっています。settings.env を活用してください。
- RSS 収集部分は外部ネットワークを扱うため、SSRF 対策やサイズ制限を実装しています。ソース変更時は安全性を意識して下さい。

---

必要であれば、README に含めるコマンドラインの実行例や .env.example のテンプレート、CI やデプロイ手順（systemd/timers での定期 ETL 実行など）も追加できます。どの情報を優先して追記するか指示をください。