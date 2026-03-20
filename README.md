KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株のデータ収集（J-Quants）、Data Platform（DuckDB）上での加工、研究用ファクター計算、特徴量生成、シグナル生成、および発注/監査ログ基盤を想定した自動売買システムの実装コアです。  
モジュール設計は「Raw → Processed → Feature → Execution」の多層アーキテクチャに沿っており、ETL・品質チェック・研究環境・戦略層を分離して実装しています。

主な機能
--------
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - 株価日足、財務データ、マーケットカレンダー取得
- DuckDB ベースのスキーマ定義と初期化（冪等）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ニュース収集（RSS → 正規化 → raw_news 保存、銘柄抽出）
- 研究モジュール（モメンタム / ボラティリティ / バリュー等のファクター計算）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（ファクター + AI スコア統合、BUY/SELL の判定ロジック）
- 発注・監査用スキーマ（signal / order / execution / audit テーブル群）
- 汎用統計ユーティリティ（Z スコア正規化 等）

セットアップ手順
--------------
前提
- Python 3.10 以上（型注釈（X | Y）を使用しているため）
- DuckDB（Python パッケージ）、defusedxml 等が必要

推奨インストール例（仮想環境を推奨）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージ（例）
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

3. 開発環境としてローカルで使う場合
   - pip install -e .  （パッケージ化されている場合）

環境変数（最低限必要なキー）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（省略時: development）
- LOG_LEVEL — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL（省略時: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（省略時: data/monitoring.db）

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある .env / .env.local が自動読み込みされます。
- 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡易 .env.example
- JQUANTS_REFRESH_TOKEN=xxxxxxxx
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=CXXXXXXX
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

基本的な使い方
--------------

1) DuckDB スキーマ初期化
- DuckDB ファイルを作成し、全テーブルを初期化します。

例:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL（J-Quants から差分取得 → 保存 → 品質チェック）
- run_daily_etl はカレンダー取得 → 株価取得 → 財務取得 → 品質チェックを順次実行します。

例:
from kabusys.data.pipeline import run_daily_etl
from datetime import date
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

戻り値は ETLResult（取得件数、保存件数、品質問題一覧、エラー要約等）です。

3) 特徴量構築（features テーブルへ保存）
- 研究モジュールで計算した raw ファクターを正規化・合成して features テーブルに保存します。

例:
from kabusys.strategy import build_features
from datetime import date
count = build_features(conn, date(2025, 1, 15))
print(f"features upserted: {count}")

4) シグナル生成（signals テーブルへ保存）
- features と ai_scores、positions を参照して BUY/SELL シグナルを生成します。

例:
from kabusys.strategy import generate_signals
from datetime import date
n = generate_signals(conn, date(2025, 1, 15))
print(f"signals written: {n}")

オプション:
- generate_signals(..., threshold=0.65, weights={"momentum": 0.5, ...})

5) ニュース収集
- RSS フィードから記事を収集して raw_news に保存、既知銘柄との紐付けも可能です。

例:
from kabusys.data.news_collector import run_news_collection
known = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known)
print(results)

6) J-Quants データ取得 API（必要に応じて直接利用）
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- 保存用ヘルパー: save_daily_quotes, save_financial_statements, save_market_calendar

ログ・環境判定ユーティリティ
- kabusys.config.settings により環境変数をラップ。利用例:
from kabusys.config import settings
print(settings.env, settings.is_live, settings.duckdb_path)

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動読み込みと Settings クラス
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（レート制御・リトライ等）
  - news_collector.py        — RSS 収集と記事保存・銘柄抽出
  - schema.py                — DuckDB スキーマ定義・初期化
  - stats.py                 — 汎用統計（zscore_normalize）
  - pipeline.py              — ETL パイプライン（差分更新・品質チェック呼び出し）
  - features.py              — data.stats の再エクスポート
  - calendar_management.py   — 市場カレンダー操作ユーティリティ
  - audit.py                 — 監査ログスキーマ（signal_events / order_requests / executions 等）
- research/
  - __init__.py
  - factor_research.py       — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py   — 将来リターン / IC / 統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py   — features 作成・正規化・ユニバースフィルタ
  - signal_generator.py      — final_score 計算と BUY/SELL シグナル生成
- execution/                  — 発注ロジック用パッケージ（空の __init__ が含まれる）
- monitoring/                 — 監視・メトリクス用（将来的な拡張）

各モジュールの責務（簡略）
- data.jquants_client: API 呼び出し（ページネーション、トークン、保存ユーティリティ）
- data.schema: データベース DDL の集中管理（冪等）
- data.pipeline: 差分 ETL の Orchestrator
- data.news_collector: RSS の安全な取得と DB 保存（SSRF・XML Bomb 対策あり）
- research.*: 研究用のファクター計算・相関評価ユーティリティ
- strategy.*: 特徴量合成とシグナル生成（戦略ロジック本体）
- execution: 実際のブローカー接続・注文送信を実装する層（この実装では未実装部分あり）
- audit: 発注から約定までの完全なトレーサビリティ用スキーマ

注意点・設計上の方針（抜粋）
--------------------------
- ルックアヘッドバイアス対策: 戦略・特徴量モジュールは target_date 時点の情報のみを使用するよう設計されています。
- 冪等性: API 保存処理は ON CONFLICT / UPSERT を用いて再実行可能に設計されています。
- セキュリティ: news_collector では SSRF 対策、XML パーサの安全化、レスポンスサイズ制限等を導入しています。
- テスト容易性: pipeline や client 関数は id_token の注入や _urlopen のモック差替えを想定しています。
- Python 3.10 を想定（型表記に依存）。

よくある操作の例（スクリプト）
-----------------------------
1. 初期 DB を作ってETLを1回実行するスクリプト例
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2. 特徴量→シグナルの流れ（研究→本番）
from kabusys.strategy import build_features, generate_signals
from datetime import date

d = date(2025, 1, 15)
build_features(conn, d)
generate_signals(conn, d)

サポート / 開発
----------------
- README に書かれていない仕様（StrategyModel.md、DataPlatform.md 等）の参照が想定されています。実運用・詳細設計はこれらのドキュメントに準拠してください。
- 実ブローカー接続（発注層）は別実装が必要です。execution 層にブリッジを実装して安全性（冪等・リトライ・障害時の回復）を担保してください。

ライセンス
---------
プロジェクトに付与されたライセンスに従ってください（ここでは明示されていません）。商用利用や API トークンの扱いには注意してください。

---

必要であれば、README に含めるサンプル .env.example や、より詳細な CLI / systemd / cron による定期実行例、自動テストの書き方（pytest でのモック例）なども作成します。どれを追加しますか？