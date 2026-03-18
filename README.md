# KabuSys

日本株自動売買システムのライブラリ群（モジュール群）です。  
データ取得（J-Quants）、ETL、データ品質チェック、特徴量計算、ニュース収集、監査ログ、マーケットカレンダー管理、研究用ユーティリティなどを含みます。

---

## プロジェクト概要

KabuSys は日本株の量的運用基盤を想定したコンポーネント群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得（レートリミット・リトライ・トークン自動更新対応）
- DuckDB を用いた Raw / Processed / Feature / Execution 層のデータ管理
- ETL（差分取得・保存）パイプラインと品質チェック
- RSS ベースのニュース収集と銘柄紐付け
- 戦略研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）と IC/統計サマリー
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）

設計方針として、DuckDB を中心に冪等性（ON CONFLICT）、Look-ahead バイアス回避（fetched_at の記録）、外部 API への影響を考慮した安全設計（SSRF対策、XML防御、レスポンスサイズ制限 等）が取り入れられています。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants からのデータ取得（株価日足・財務・マーケットカレンダー）
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（save_*）

- data/schema.py, data/audit.py
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(), init_audit_schema(), init_audit_db()

- data/pipeline.py
  - 差分更新型 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - ETL 実行結果を表す ETLResult クラス

- data/quality.py
  - 欠損・重複・スパイク・日付不整合などの品質チェック（run_all_checks）

- data/news_collector.py
  - RSS フィード取得、正規化、記事ID生成（SHA-256 の先頭32文字）、raw_news への冪等保存
  - SSRF・gzip・XML 脆弱性対策、銘柄コード抽出と news_symbols 紐付け

- data/calendar_management.py
  - market_calendar の差分更新ジョブ、営業日判定、next/prev/get_trading_days、SQ日判定等

- research/*
  - factor_research.py：モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py：将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - data.stats.zscore_normalize の再エクスポートを含む

- execution, strategy, monitoring モジュールのプレースホルダ（パッケージ化済み）

---

## セットアップ手順

前提
- Python 3.9+（型ヒントに union | 型 等を使用しているため）
- pip, virtualenv 等

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   ※リポジトリに requirements.txt がない場合、主要な依存は以下です（実際のプロジェクトで追加の依存があるか確認してください）。
   ```
   pip install duckdb defusedxml
   ```
   （HTTP クライアント等が標準ライブラリで実装されているため最小依存に留めています）

4. 環境変数の準備  
   プロジェクトルートに `.env`（あるいは `.env.local`）を置くことで自動的に読み込まれます（ただし、テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します）。

   必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知チャネル ID

   その他（デフォルトあり）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabuAPI base URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング）パス（デフォルト: data/monitoring.db）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUS_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は Python スクリプト／REPL での基本的な利用例です。パスや変数は環境に合わせて調整してください。

- DuckDB スキーマ初期化（最初の一回）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
# 以降 conn を再利用して ETL・保存等を行う
```

- 監査スキーマの初期化（独立して監査 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

- 日次 ETL の実行（市場カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブ（既知銘柄コードを与えて紐付けまで行う）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

- J-Quants API から日足を直接取得
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
```

- 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research import calc_momentum
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
factors = calc_momentum(conn, target_date=date(2025,3,1))
# factors は [{"date": ..., "code": ..., "mom_1m": ..., ...}, ...]
```

- ファクター評価（将来リターン・IC 計算）
```python
from kabusys.research import calc_forward_returns, calc_ic
# forward_returns = calc_forward_returns(conn, target_date, horizons=[1,5,21])
# calc_ic(factor_records, forward_records, factor_col='mom_1m', return_col='fwd_1d')
```

---

## 注意点 / Tips

- 自動で .env / .env.local を読み込みます（プロジェクトルート判定は .git または pyproject.toml を基準）。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にします（テスト時の差し替えに便利）。
- J-Quants のレート制限（120 req/min）を守るため内部でスロットリング処理があります。大量取得時はこの仕様に従ってください。
- DuckDB の INSERT は冪等（ON CONFLICT）で設計されていますが、外部から直接変更が入るケース等を考慮し品質チェック（data.quality.run_all_checks）を実行することを推奨します。
- news_collector は外部 RSS を扱うため、SSRF 対策や XML パーサ保護（defusedxml）を組み込んでいます。外部 URL の取扱いは慎重に。
- KABUSYS_ENV の有効値は development / paper_trading / live。log レベルは標準的な値（DEBUG 等）を使用します。

---

## ディレクトリ構成（概要）

以下は主要ファイル／モジュールの一覧と簡単な説明です（src/kabusys 以下）。

- __init__.py
  - パッケージの公開 API を定義（data, strategy, execution, monitoring）

- config.py
  - 環境変数読み込み（.env 自動ロード）と Settings クラス（設定項目）

- data/
  - __init__.py
  - jquants_client.py : J-Quants API クライアント（取得 + DuckDB 保存）
  - news_collector.py : RSS ニュース収集・保存・銘柄抽出
  - schema.py         : DuckDB スキーマ定義・初期化関数
  - stats.py          : z-score 正規化など統計ユーティリティ
  - pipeline.py       : ETL パイプライン（run_daily_etl 等）
  - features.py       : features 用公開インターフェース（zscore 再エクスポート）
  - calendar_management.py : market_calendar 管理・判定ユーティリティ
  - audit.py          : 監査ログ（signal_events / order_requests / executions）DDL と初期化
  - quality.py        : データ品質チェック

- research/
  - __init__.py
  - feature_exploration.py : 将来リターン・IC・統計サマリー等
  - factor_research.py     : Momentum / Volatility / Value 等のファクター計算

- strategy/ (空の __init__ プレースホルダ)
- execution/ (空の __init__ プレースホルダ)
- monitoring/ (空の __init__ プレースホルダ)

---

## 追加情報

- ロギングは標準 logging を使用します。環境変数 LOG_LEVEL で出力レベルを調整してください。
- DuckDB パスや監査 DB パスは環境変数で設定可能です（settings.duckdb_path 等）。
- 実運用で発注（kabu API）を行う場合は十分なテスト・リスク管理（paper_trading モード等）を実施してください。

---

問題や追加で README に載せたい内容（例: サンプル .env.example、requirements.txt、運用手順）等があれば教えてください。必要に応じて README を拡張します。