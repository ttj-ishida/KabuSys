# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、DuckDB によるデータ管理、ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、実行（発注／ポジション管理）など、戦略実装に必要な基盤機能を含みます。

バージョン: 0.1.0

---

## 主な概要

- J-Quants API から株価・財務・カレンダーを取得して DuckDB に保存する ETL パイプライン
- Research / Strategy 層のファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量（features）正規化・作成（Z スコア正規化・クリップ）
- シグナル生成ロジック（最終スコア算出、BUY/SELL 判定、エグジット判定）
- ニュース収集（RSS → raw_news、記事と銘柄の紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- DuckDB スキーマ定義・初期化、ロギング・設定管理

設計方針の一部:
- ルックアヘッドバイアス防止（計算は target_date 時点のデータのみ使用）
- 冪等性（DB への保存は ON CONFLICT 等で上書き/重複排除）
- 外部ライブラリへの依存を最小化（主要ロジックは標準ライブラリ + 必要最小限のパッケージ）

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（レート制御、リトライ、トークン自動更新、DuckDB 保存ユーティリティ）
  - pipeline: 日次 ETL（prices / financials / calendar）、差分取得・バックフィル、品質チェックフック
  - schema: DuckDB スキーマ定義と init_schema()
  - news_collector: RSS フィード取得・前処理・DB 保存・銘柄抽出
  - calendar_management: 営業日判定・next/prev/get_trading_days、calendar_update_job
  - stats: zscore_normalize など統計ユーティリティ
- research/
  - factor_research: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials 参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリ
- strategy/
  - feature_engineering.build_features: 生ファクターを統合して features テーブルへアップサート
  - signal_generator.generate_signals: features + ai_scores から final_score を算出して signals を作成
- その他
  - config: 環境変数読み込みと Settings（J-Quants トークン、kabu API パスワード、Slack トークン、DB パス等）

---

## 動作要件 / 必要環境

- Python 3.10 以上（| 型ヒント等の構文を使用）
- DuckDB（Python パッケージ duckdb）
- defusedxml（RSS XML パースの安全化）
- ネットワークアクセス（J-Quants API、RSS）

推奨パッケージ（最低限）:
- duckdb
- defusedxml

インストール例:
- pip install duckdb defusedxml

（パッケージを pip で配布する場合は requirements.txt / pyproject.toml を利用してください）

---

## 環境変数

設定は .env ファイルまたは環境変数からロードされます（自動ロードはプロジェクトルートに .env/.env.local がある場合有効）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視等で利用する SQLite path（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — execution 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml

   （パッケージ管理に pyproject.toml / requirements.txt がある場合はそれに従ってください）

3. 環境変数を設定（.env を作成）
   - プロジェクトルートに .env または .env.local を配置
   - 上記の必須環境変数を設定

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行:
     from kabusys.config import settings
     from kabusys.data.schema import init_schema
     init_schema(settings.duckdb_path)

   - あるいはインメモリでテスト:
     from kabusys.data.schema import init_schema
     init_schema(":memory:")

---

## 使い方（主要な API とワークフロー例）

以下は代表的なワークフローの呼び出し例（簡易）。すべて DuckDB 接続（duckdb.DuckDBPyConnection）を渡して動作します。

1) DB の初期化（例）
- schema.init_schema() を使う（上記セットアップ参照）

2) 日次 ETL（J-Quants からデータ取得して保存）
- 例:
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date 省略で今日
  print(result.to_dict())

3) 特徴量（features）構築
- 例:
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  from datetime import date
  build_features(conn, date(2024, 1, 15))

  ※ build_features は features テーブルに対して日付単位で置換（冪等）

4) シグナル生成
- 例:
  from kabusys.strategy import generate_signals
  from datetime import date
  cnt = generate_signals(conn, date(2024, 1, 15))
  print(f"generated {cnt} signals")

  - 引数で threshold（BUY閾値）や weights（ファクター重み）を上書きできます。

5) ニュース収集ジョブ
- 例:
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  print(res)

6) マーケットカレンダー更新（夜間バッチ）
- 例:
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"saved {saved} calendar records")

7) J-Quants の個別データ取得（テストやスクリプト）
- fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=..., date_to=..., code="7203")
  jq.save_daily_quotes(conn, records)

注意:
- 各操作はログ出力と例外処理を行います。バッチ運用ではログ・監視設定（Slack 通知等）を整えてください。
- generate_signals / build_features は発注層（execution）の実際の注文実行を行いません。execution 層は別モジュールで処理する想定です。

---

## ディレクトリ構成（抜粋）

プロジェクトのルート配下（src/kabusys）には以下の主要モジュールがあります:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数設定管理 (Settings)
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存ユーティリティ
    - pipeline.py           — 日次 ETL パイプライン
    - schema.py             — DuckDB スキーマ定義 / init_schema
    - stats.py              — zscore_normalize 等
    - news_collector.py     — RSS 取得・保存・銘柄抽出
    - calendar_management.py— カレンダー更新 / 営業日判定
    - features.py           — 再エクスポート（zscore_normalize）
    - audit.py              — 監査ログの DDL（未完の可能性あり）
  - research/
    - __init__.py
    - factor_research.py    — calc_momentum / calc_volatility / calc_value
    - feature_exploration.py— calc_forward_returns / calc_ic / factor_summary / rank
  - strategy/
    - __init__.py
    - feature_engineering.py— build_features
    - signal_generator.py   — generate_signals
  - execution/              — （発注・監視ロジックを配置する予定）
  - monitoring/             — （監視系コードを配置する予定）

（ドキュメント内の DataPlatform.md / StrategyModel.md 等に基づいた設計があります。実運用ではそれらの設計書と合わせて参照してください）

---

## 運用上の注意点

- 環境変数（API トークン等）は厳重に管理してください。特に J-Quants トークンや broker の資格情報。
- DuckDB のファイルはバックアップ・権限管理を行ってください（重要な履歴が入ります）。
- ニュース RSS の取得では外部 RSS ソースの取り扱いに注意。fetch_rss は SSRF 対策や最大レスポンスサイズ制限を実装していますが、運用上のポリシーを整えてください。
- ETL / calendar_update_job などは定期ジョブ（Cron / scheduler）で安全に実行してください。エラー・例外は監視対象とすること。
- production（live）モードでは KABUSYS_ENV=live に設定し、実際の注文実行ロジックは厳密なガード（リスク制御）を実装してください。

---

## 貢献 / 開発

- コードベースはモジュールごとに分割されています。新しい機能を追加する際は、ユニットテスト・インテグレーションテストを追加してください。
- 外部 API を模擬するために jquants_client や network 呼び出しをモック可能な設計になっています（例: _urlopen の差し替え等）。
- ドキュメント（DataPlatform.md / StrategyModel.md 等）が存在する場合は必ず参照し、実装と整合性を取ってください。

---

必要であれば、README に含めるサンプルスクリプト（バッチ起動スクリプト、systemd / cron 用の例）や .env.example のテンプレートを作成します。どちらを追加しますか？