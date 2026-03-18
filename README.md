# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）のリポジトリです。  
このリポジトリはデータ取得・ETL、ファクター（特徴量）計算、ニュース収集、監査ログ、マーケットカレンダー管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ基盤向けに設計された Python モジュール群です。主な目的は以下です。

- J-Quants API 等からの市場データ・財務データの取得と DuckDB への保存（ETL）
- ニュース RSS の収集と記事 → 銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ファクター（モメンタム・ボラティリティ・バリュー等）の計算および IC / 統計サマリー
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）テーブル定義
- マーケットカレンダー管理（営業日判定、前後営業日検索）
- 発注／実行／ポジション管理のためのスキーマ（実行レイヤ）

設計方針として、DuckDB を中心にローカルで完結するデータレイヤを構築し、外部 API 呼び出しは明確に隔離、冪等性と品質チェックを重視しています。

---

## 機能一覧

主な機能（モジュール単位）:

- kabusys.config
  - .env / 環境変数から設定を自動読み込み
  - 必須設定を取得する Settings クラス
- kabusys.data.jquants_client
  - J-Quants API クライアント（ページネーション、レートリミット、リトライ、トークン自動リフレッシュ）
  - fetch/save 用関数（株価・財務・カレンダー）
- kabusys.data.schema / audit
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - スキーマ初期化関数（init_schema, init_audit_db 等）
- kabusys.data.pipeline
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果の ETLResult クラス（品質問題・エラーログ収集）
- kabusys.data.news_collector
  - RSS フィード取得、XML パース（defusedxml）、記事正規化、記事ID生成、DuckDB への冪等保存
  - SSRF 対策、受信サイズ制限、トラッキングパラメータ除去
- kabusys.data.quality
  - データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- kabusys.data.calendar_management
  - market_calendar を用いた営業日判定、次/前営業日の検索、カレンダー更新ジョブ
- kabusys.research.factor_research / feature_exploration
  - momentum / volatility / value 等のファクター計算
  - 将来リターン計算、IC（Spearman ρ）計算、ファクターサマリー
  - z-score 正規化ユーティリティ（data.stats から）
- kabusys.data.stats
  - 汎用統計ユーティリティ（zscore_normalize 等）

（execution, strategy, monitoring 用のパッケージの土台を含む構成）

---

## セットアップ手順

前提:
- Python 3.9+（typing の表記等に依存）
- duckdb（Python パッケージ）
- defusedxml

1. リポジトリをチェックアウト（任意）
2. 仮想環境の作成（推奨）
   - Unix/macOS
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell)
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
3. 必要パッケージのインストール
   ```
   pip install duckdb defusedxml
   ```
   （将来的に requirements.txt / pyproject.toml があればそちらを使用）

4. 開発インストール（ソースをパッケージとして使う場合）
   ```
   pip install -e .
   ```
   （プロジェクトに pyproject.toml / setup.cfg がある場合のみ）

5. 環境変数設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local もサポート）。
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabu API 用パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン（通知用）
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB パス（デフォルト data/monitoring.db）

.example の .env 内容例:
```
# .env.example
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡易ガイド）

以下は Python REPL / スクリプトでの利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# ":memory:" を指定するとインメモリ DB
```

2) 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 今日分を実行
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

4) ファクター計算（例: モメンタム）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2025, 3, 1))
# records は [{ "date": ..., "code": "7203", "mom_1m": ..., ...}, ...]
```

5) 将来リターンと IC 計算
```python
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2025,3,1), horizons=[1,5,21])
# factor_records は別途算出した factor リスト
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)
```

6) カレンダー更新ジョブ（夜間バッチなどで）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

注意:
- jquants_client は urllib を用いて HTTP リクエストを行います。J-Quants の API 使用に際しては API 利用規約・レート制限に従ってください（実装は120 req/min を守る仕組みを持ちます）。
- news_collector は defusedxml を利用し安全に RSS をパースします。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を示します）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings 管理
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント・保存ロジック
    - news_collector.py  — RSS 収集・記事保存・銘柄抽出
    - schema.py  — DuckDB スキーマ定義・init_schema/get_connection
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - etl.py  — ETL 公開 API（ETLResult の再エクスポート）
    - stats.py  — zscore_normalize 等の統計ユーティリティ
    - features.py — features の公開インターフェース（zscore re-export）
    - quality.py — データ品質チェック
    - calendar_management.py — マーケットカレンダーとユーティリティ
    - audit.py — 監査ログ（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py  — momentum/volatility/value の計算
    - feature_exploration.py  — 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py (戦略実装のプレースホルダ)
  - execution/
    - __init__.py (発注周りのプレースホルダ)
  - monitoring/
    - __init__.py (監視機能のプレースホルダ)

---

## よくある運用ポイント / 注意点

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。テスト時など自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマは冪等的に作成されます。初回は init_schema() を呼び出してください。
- ETL は Fail-Fast ではなく各ステップでエラーハンドリングし続行します（ETLResult にエラー・品質問題を収集）。運用時は ETLResult を確認して通知・アラートを出してください。
- news_collector は RSS の XML を解析する際に多数の安全策（SSRF、XML Bomb、サイズ制限など）を講じていますが、運用環境のネットワーク制限やプロキシ設定に注意してください。
- J-Quants API のトークンは Settings が要求します。get_id_token は refresh token から id token を取得します。トークンの管理は安全に行ってください。
- DuckDB の SQL 実行ではパラメータバインド（?）を利用して SQL インジェクションリスクを低減しています。

---

## 開発 / テスト

- 単体ファイルに対しては各モジュールごとのユニットテストを作成してください（duckdb の in-memory DB を使うと高速にテストできます）。
- network を伴うテストは外部呼び出しをモック化して行うことを推奨します（例: jquants_client._request, news_collector._urlopen のモック）。

---

README はここまでです。具体的な利用シナリオ（バッチ化、監視、Slack 通知連携、実取引開始のフロー等）やサンプルスクリプトが必要であれば、用途に合わせた例を追記します。どの部分のサンプルが欲しいか教えてください。