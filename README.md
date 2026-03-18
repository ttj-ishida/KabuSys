# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
データ取得（J-Quants）、ETLパイプライン、DuckDBスキーマ、ファクター計算、ニュース収集、品質チェック、監査ログなどを包含するモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計された内部向けライブラリです。

- J-Quants API から株価・財務・カレンダー情報を取得して DuckDB に保存する（差分更新・冪等保存）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース（RSS）収集と記事の前処理・銘柄紐付け
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と Research 用ユーティリティ
- 発注/監査用スキーマ（監査ログ・オーダー要求・約定など）
- 研究用途・戦略実装のための基盤 API を提供

設計方針として、本番取引 API へのアクセスは分離し、DuckDB を中核にしてデータのトレーサビリティと冪等性を確保しています。

---

## 機能一覧

- データ取得
  - J-Quants API クライアント（レート制御、リトライ、トークン自動更新、ページネーション）
  - 株価日足、財務データ、マーケットカレンダーの取得・保存
- データ基盤
  - DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit 層）
  - スキーマ初期化ユーティリティ（init_schema / init_audit_db）
- ETL
  - 日次差分 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェックの順
  - 個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
- 品質管理
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェック
- ニュース収集
  - RSS 取得、前処理、重複排除、raw_news に冪等保存、記事と銘柄の紐付け
  - SSRF 対策、レスポンスサイズ上限、gzip 解凍、XML の安全パース
- Research / Strategy
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算（calc_forward_returns）・IC 計算（calc_ic）
  - 統計ユーティリティ（zscore_normalize / factor_summary / rank）
- 監査（Audit）
  - signal_events, order_requests, executions テーブルとインデックス
  - 発注〜約定までのトレーサビリティ設計

---

## 前提条件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants / RSS ソースへアクセス）
- J-Quants / Slack 等の API トークン（環境変数で設定）

（実際の packaging / requirements はプロジェクトの pyproject.toml / requirements.txt に従ってください）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install duckdb defusedxml
   - その他プロジェクトに応じた依存をインストール
4. パッケージを開発モードでインストール（任意）
   - pip install -e .

### 環境変数（必須）

主に以下の環境変数を使用します。.env ファイルをプロジェクトルートに置くと自動で読み込まれます（自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API 用パスワード（発注明示的に使う場合）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャンネル ID

任意（デフォルト値あり）:
- KABUSYS_ENV : development | paper_trading | live （デフォルト development）
- LOG_LEVEL : DEBUG | INFO | WARNING | ERROR | CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env の自動読み込みを抑止
- DUCKDB_PATH : DuckDB データベースパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL : kabuAPI ベース URL（デフォルト http://localhost:18080/kabusapi）

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## 使い方（基本）

以下は Python REPL やスクリプトから使う基本例です。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行（J-Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)
print(result.to_dict())
```

- News コレクション（RSS 取得 → 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes を与えると本文から銘柄コード抽出して紐付けします
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

- Research: ファクター計算（例: モメンタム）
```python
from kabusys.research import calc_momentum
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2024, 3, 1))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

- IC（Information Coefficient）計算例
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,3,1), horizons=[1])
# factor_records は例えば calc_momentum の出力を zscore_normalize 等で前処理したもの
rho = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- スキーマの監査テーブルを初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

ノート:
- run_daily_etl 等の関数はエラーや品質チェックを独立に扱い、1 ステップ失敗でも他のステップは継続します。戻り値（ETLResult）で詳細を確認してください。
- テスト時は id_token を外部から注入してネットワーク呼び出しを制御できます。

---

## 開発・デバッグのヒント

- 自動で .env を読み込みますが、テストなどで無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テスト用にインメモリ DB を使うには db_path に ":memory:" を指定します。
- ネットワーク呼び出し（J-Quants / RSS）をモックするには各モジュール内のヘルパ（例: _urlopen, _request）を差し替えると容易です。
- DuckDB は SQL を直接投げてデバッグしやすいため、conn.execute(...) を使って状態確認ができます。

---

## ディレクトリ構成（主なファイルと説明）

- src/kabusys/
  - __init__.py : パッケージ定義・バージョン
  - config.py : 環境変数 / 設定読み込み・Settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py : J-Quants API クライアント（取得・保存関数）
    - news_collector.py : RSS ニュース収集・前処理・保存
    - schema.py : DuckDB スキーマ定義と init_schema / get_connection
    - stats.py : 汎用統計ユーティリティ（zscore_normalize）
    - pipeline.py : ETL パイプライン（run_daily_etl 等）
    - features.py : data.stats の再エクスポート
    - calendar_management.py : market_calendar 管理・営業日判定・更新ジョブ
    - audit.py : 監査ログ（signal_events, order_requests, executions）
    - etl.py : ETLResult の公開インターフェース
    - quality.py : データ品質チェック
  - research/
    - __init__.py : 研究向けユーティリティのエクスポート
    - feature_exploration.py : 将来リターン計算, IC, factor_summary, rank
    - factor_research.py : モメンタム/ボラティリティ/バリュー等の計算
  - strategy/
    - __init__.py : 戦略関連モジュール（未実装のプレースホルダ）
  - execution/
    - __init__.py : 発注/実行関連（未実装のプレースホルダ）
  - monitoring/
    - __init__.py : 監視・メトリクス関連（プレースホルダ）

---

## 注意事項

- このリポジトリは発注のための完全なブローカー統合を含んでいるわけではありません。発注関連の実装は別モジュール／運用規約に従って行ってください。
- 本ライブラリは市場データや発注に関わるため、テストやデプロイ時にキーや本番口座の取り扱いに注意してください（本番モードでは is_live フラグが True になります）。
- DuckDB のバージョン差異による機能差（ON DELETE CASCADE 等）はドキュメント内コメントに記載しています。環境に応じた対応をしてください。

---

この README はコードベースの主要機能と使い方を簡潔にまとめたものです。詳細な仕様や API の挙動は各モジュールの docstring を参照してください。必要であればサンプルスクリプトや運用手順のテンプレートも作成します。興味のある箇所を教えてください。