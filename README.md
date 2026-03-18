# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群です。データ収集（J-Quants / RSS）、DuckDB ベースのスキーマと ETL、ファクター算出（リサーチ用）、品質チェック、監査ログなどを含むモジュール群を提供します。

主な設計方針は「冪等性」「Look-ahead-bias の回避」「テスト容易性」「外部ライブラリへの不要な依存を避ける（標準ライブラリ優先）」です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ユースケース）
- 環境変数（.env）例
- ディレクトリ構成

---

プロジェクト概要
- DuckDB をデータ層に用いたデータパイプラインとスキーマ定義
- J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS ベースのニュース収集（SSRF 対策、サイズ制限、トラッキング除去）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ファクター計算（モメンタム／ボラティリティ／バリュー等）とリサーチ用ユーティリティ
- 監査ログ（シグナル→注文→約定のトレース用テーブル群）

---

機能一覧
- 環境変数設定読み込み（.env / .env.local、自動ロード、上書き制御）
- DuckDB スキーマ初期化（raw / processed / feature / execution 層）
- J-Quants クライアント
  - 日足・財務・マーケットカレンダー取得（ページネーション対応）
  - レートリミット制御、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存用 save_* 関数
- ETL パイプライン
  - 差分取得（最終取得日に基づく差分）＋バックフィル
  - カレンダー先読み（lookahead）
  - 品質チェック統合（quality モジュール）
  - run_daily_etl による一括実行
- ニュース収集
  - RSS 取得、前処理、SHA256 による冪等 ID、DuckDB への保存、銘柄抽出
  - SSRF / Gzip bomb / レスポンスサイズ対策
- リサーチ（research）
  - calc_momentum / calc_volatility / calc_value 等のファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- データ品質チェック（quality）
  - 欠損・スパイク・重複・日付不整合検出（QualityIssue を返す）
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブルと初期化ユーティリティ

---

前提・要件
- Python 3.10+（typing に union 型 | を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
（プロジェクトの packaging によって requirements.txt / pyproject.toml を用意してください）

セットアップ手順（ローカル）
1. リポジトリをクローンしてワークディレクトリへ
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   （他に必要なパッケージがあれば pyproject.toml / requirements.txt を参照）
4. 環境変数を用意（.env をプロジェクトルートに配置、例は下記）
   - 自動ロードは kabusys.config がプロジェクトルート（.git または pyproject.toml）を探索して行います
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

主な環境変数（必須・任意）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — development | paper_trading | live （デフォルト development）
- LOG_LEVEL (任意) — DEBUG | INFO | WARNING | ERROR | CRITICAL

例 (.env)
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

使い方（サンプル）

1) 設定参照
from kabusys.config import settings
token = settings.jquants_refresh_token
if settings.is_live:
    # 本番フラグなどで分岐

2) DuckDB スキーマ初期化
from kabusys.data import schema
conn = schema.init_schema(settings.duckdb_path)  # Path または ":memory:" を指定可能

3) ETL（日次パイプライン）実行
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())  # ETLResult を辞書化してログ出力等に利用

4) ニュース収集ジョブ（RSS）
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes があれば記事→銘柄抽出を行う
known_codes = {"7203", "6758", "9432"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
# res は {source_name: saved_count} の辞書

5) J-Quants から個別データ取得（テスト用途）
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))

6) リサーチ用ファクター計算
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize
mom = calc_momentum(conn, target_date=date(2024,2,20))
vol = calc_volatility(conn, target_date=date(2024,2,20))
val = calc_value(conn, target_date=date(2024,2,20))
# zscore 正規化など
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

7) 品質チェックを単独で実行
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2024,2,20))
for i in issues:
    print(i)

8) 監査ログの初期化（別 DB に分ける場合）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

注意点
- DuckDB の接続はスレッドセーフ性や同時書き込みの特性に注意して運用してください。
- J-Quants の API レートリミット（120 req/min）をクライアントで制御していますが、ETL 実行計画は実運用に合わせて調整してください。
- .env のパスワードやトークンは厳重に管理してください。

---

ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py
- config.py        — 環境変数 / 設定管理（自動 .env ロード、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（fetch/save）
  - news_collector.py     — RSS 収集・前処理・DB 保存
  - schema.py             — DuckDB スキーマ定義・初期化
  - stats.py              — zscore_normalize 等の統計ユーティリティ
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - features.py           — features 互換インターフェース（再エクスポート）
  - calendar_management.py— market_calendar の管理・ジョブ・営業日判定
  - audit.py              — 監査ログスキーマ初期化
  - etl.py                — ETLResult の公開再エクスポート
  - quality.py            — 品質チェック実装
- research/
  - __init__.py
  - feature_exploration.py — 将来リターン / IC / summary 等
  - factor_research.py     — momentum / volatility / value の計算
- strategy/   — 戦略層（未実装の placeholder）
- execution/  — 発注/約定/ポジション管理（未実装の placeholder）
- monitoring/ — 監視・メトリクス（placeholder）

注: strategy/ と execution/、monitoring/ は __init__.py のみで詳細実装はここに含まれていません（拡張ポイント）。

---

開発・テストのヒント
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テストで環境を制御したい場合）。
- jquants_client の HTTP 呼び出しはモジュールレベルでレート制御・トークンキャッシュを持つため、単体テストでは get_id_token や _request をモックすることを推奨します。
- news_collector._urlopen や RSS 関連のネットワーク I/O はモック可能な構造になっています。

---

ライセンス・貢献
- 本リポジトリのライセンスや貢献ルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（本 README は実装コードに基づく技術的な概要です）。

質問や改善要望があれば具体的なユースケース（ETL のスケジュール、DB 運用方針、戦略実装の要件など）を添えて教えてください。README の内容を環境や運用に合わせてカスタマイズして提供できます。