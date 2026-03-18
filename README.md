# KabuSys

日本株向け自動売買 / データ基盤ライブラリ KabuSys の簡易 README（日本語）

概要
----
KabuSys は日本株のデータ取得・ETL・特徴量生成・リサーチ支援・監査ログ管理を行うための Python パッケージです。J-Quants API 経由で株価・財務・マーケットカレンダーを取得し、DuckDB に格納して分析・戦略実装へ供給します。発注・監視・戦略モジュールのための基盤やユーティリティも含みます。

主な設計方針
- DuckDB をデータストアとして使用（ローカルファイルまたはインメモリ）
- J-Quants API のレート制御・リトライ・トークン自動リフレッシュを内蔵
- ETL は差分更新かつ冪等（ON CONFLICT ベース）で保存
- News（RSS）収集は SSRF 対策・サイズ制限・トラッキングパラメータ除去を実装
- 研究（research）モジュールは外部サービスにアクセスせず、DuckDB の prices_daily / raw_financials のみを参照

機能一覧
--------
- 環境設定読み込み（.env、自動ロード、必須チェック）
- J-Quants API クライアント（fetch / save / ページネーション / レート制御 / リトライ）
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- ETL パイプライン（prices / financials / market calendar の差分取得・保存・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- News（RSS）収集・前処理・DB 保存・銘柄抽出
- 研究用ユーティリティ（モメンタム・ボラティリティ・バリュー計算、IC計算、Zスコア正規化）
- 監査ログ（signal / order_request / executions）スキーマと初期化ヘルパー

セットアップ
-----------
前提
- Python 3.10 以上（型アノテーションで | 演算子を使用）
- 必要ライブラリ（最低限）:
  - duckdb
  - defusedxml

推奨インストール例（仮にソースをクローンした後）
- 仮想環境作成 / 有効化（任意）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- 必要パッケージをインストール
  - pip install duckdb defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用）

環境変数
- 自動ロード:
  - パッケージ初回インポート時にプロジェクトルート（.git または pyproject.toml）を探索し、.env と .env.local を自動読み込みします。
  - 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要環境変数（必須/任意）
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabu API パスワード（発注系で使用）
  - KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
  - SLACK_CHANNEL_ID (必須) — 通知先チャンネル ID
  - DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH (任意) — 監視用 SQLite 等（デフォルト: data/monitoring.db）
  - KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

基本的な使い方
--------------

1) DuckDB スキーマ初期化
- Python REPL / スクリプトで:
```python
from kabusys.config import settings
from kabusys.data import schema

# settings.duckdb_path は Path を返す
conn = schema.init_schema(settings.duckdb_path)
```
- :memory: を使う場合:
```python
conn = schema.init_schema(":memory:")
```

2) 日次 ETL 実行
- run_daily_etl を呼んで prices/financials/calendar を差分取得し品質チェックする:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # 引数で target_date / id_token を渡せます
print(result.to_dict())
```

3) ニュース収集（RSS）
- run_news_collection を使って RSS を取得・保存・銘柄紐付けを行う:
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は既知の銘柄コード集合 (例: DB から抽出)
codes = {row[0] for row in conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()}
res = run_news_collection(conn, known_codes=codes)
print(res)  # {source_name: 保存件数}
```

4) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print("saved:", saved)
```

5) 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns

# 例: calc_momentum(conn, target_date)
```

6) 監査ログスキーマ初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

注意点 / 運用上のポイント
-----------------------
- J-Quants のレート制限は 120 req/min。jquants_client は固定間隔スロットリングとリトライを実装していますが、複数プロセスから同時に走らせるとレート超過となる可能性があるため運用設計に注意してください。
- ETL は差分 + バックフィルを行います。バックフィル日数は pipeline.run_* 関数の引数で制御できます。
- news_collector は外部からの RSS を扱うため、サイズ上限と SSRF 対策（リダイレクト検査・プライベートホスト拒否）を実装しています。外部フィードの追加は DEFAULT_RSS_SOURCES を拡張して行ってください。
- settings（kabusys.config.Settings）は環境変数をラッパーしており、未設定の必須変数アクセス時は ValueError を投げます。CI / デプロイ環境では .env の管理に注意してください。
- DuckDB スキーマ作成は冪等（IF NOT EXISTS）です。init_schema は親ディレクトリを自動作成します。

主要なディレクトリ構成
--------------------
（パッケージソースツリー内の概略）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - news_collector.py             — RSS 収集 / 前処理 / DB 保存
    - schema.py                     — DuckDB スキーマ DDL & init_schema
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - quality.py                    — 品質チェックルール
    - stats.py                      — 統計ユーティリティ（zscore）
    - features.py                   — features 公開インターフェース
    - calendar_management.py        — market_calendar の管理・ジョブ
    - audit.py                      — 監査ログスキーマ & 初期化
    - etl.py                        — ETL の公開型再エクスポート
  - research/
    - __init__.py
    - feature_exploration.py        — forward returns / IC / factor_summary
    - factor_research.py            — momentum / volatility / value 計算
  - strategy/                       — 戦略関連（未実装/拡張用）
  - execution/                      — 発注・約定・ポジション管理（拡張用）
  - monitoring/                     — 監視周り（拡張用）

拡張ポイント
-------------
- strategy / execution / monitoring パッケージは設計に沿って実装を追加できます。audit / signal のスキーマは既に定義済みで、戦略→監査→発注のトレーサビリティ確保が容易です。
- research モジュールの関数は DuckDB 接続を受け取るため、任意のデータセットで再利用可能です。
- news_collector の URL ソース追加や、銘柄抽出ロジックの拡張（NLP を用いた高度な抽出）なども想定されています。

トラブルシューティング
---------------------
- 環境変数が読めない / settings がエラーを投げる:
  - .env をプロジェクトルートに配置しているか、KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
  - 必須変数（JQUANTS_REFRESH_TOKEN 等）が未設定だと ValueError が発生します。
- DuckDB への接続や DDL で失敗する:
  - ディスクの書き込み権限やパスが正しいか確認してください。init_schema は親ディレクトリを作成しますが、OS 権限による失敗は起こります。

最後に
-----
この README はコードベースの公開 API と設計ノートを簡潔にまとめたものです。各モジュール内に詳細な docstring（設計方針・注意点・引数説明等）がありますので、実装やカスタマイズ時は該当ソースコードのドキュメントを参照してください。必要であれば利用例や運用手順ドキュメントを追加で作成します。