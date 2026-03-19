# KabuSys

日本株自動売買プラットフォームのリファレンス実装（ライブラリ）

このリポジトリは、日本株向けのデータ取得、ETL、特徴量生成、リサーチユーティリティ、監査ログ、ニュース収集などを含むバックエンドコンポーネント群を提供します。実際の発注処理は発注 API（例: kabuステーション）との連携を想定しており、戦略・実行層を組み合わせて自動売買システムを構築できます。

主な設計方針
- DuckDB を中心としたローカルデータベースでデータの冪等保存を行う
- J-Quants API からのデータ取得はレート制限・リトライ・トークン自動リフレッシュに対応
- ETL/品質チェックは Fail-Fast ではなく問題を収集して報告
- Research コードは本番口座や発注 API にアクセスしない（データのみ参照）

## 機能一覧
- データ取得 / 保存
  - J-Quants からの株価日足、財務データ、マーケットカレンダー取得（ページネーション対応）
  - 取得データを DuckDB に冪等保存（ON CONFLICT）
- ETL パイプライン
  - 差分更新（最終取得日基準）とバックフィル
  - 市場カレンダーの先読み
  - 品質チェック（欠損、重複、スパイク、日付不整合）
- データスキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義および初期化
  - 監査ログ用スキーマ（signal_events, order_requests, executions 等）
- ニュース収集
  - RSS から記事を取得して正規化・重複排除して保存
  - 記事→銘柄コードの紐付け（簡易抽出）
  - SSRF 対策・サイズ制限・XML 脆弱性対策あり
- Research（特徴量・解析）
  - Momentum / Volatility / Value などのファクター計算
  - 将来リターン計算、IC（スピアマンランク相関）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- マーケットカレンダー管理
  - 営業日判定・前後営業日取得・期間内営業日リスト取得
- 監査トレーサビリティ
  - シグナルから約定に至る監査ログを保存・検索するためのテーブル群

## 必須要件
- Python 3.10 以上（モダンな型アノテーション（X | Y）を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

プロジェクトでは他に標準ライブラリのみで実装されている箇所が多いですが、実運用では HTTP クライアントや Slack など追加ライブラリが必要になる場合があります。

## セットアップ手順

1. リポジトリをクローン／チェックアウト

   git clone <repo-url>
   cd <repo>

2. 仮想環境を作成して有効化（例: venv）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell など)

3. 依存パッケージをインストール

   pip install duckdb defusedxml

   （プロジェクトが pyproject.toml / requirements.txt を持つ場合はそちらを利用してください）
   開発インストール:
   pip install -e .

4. 環境変数設定

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（優先順位: OS > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を環境変数にセットします。

   主な環境変数（必須のものは README 内で明示しています）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuAPI のパスワード（必須、発注機能利用時）
   - KABU_API_BASE_URL: kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot Token（必須、通知を使う場合）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須、通知）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視等用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development | paper_trading | live、デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

   .env 例（簡易）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

## 使い方（主要例）

以下は代表的な利用例です。実行には事前に必要な環境変数が設定されていること、および DuckDB の初期化が完了していることを前提とします。

- DuckDB スキーマ初期化

  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

  コメント:
  - ":memory:" を渡すとインメモリ DB が使えます。
  - init_schema は親ディレクトリを自動作成します。

- 日次 ETL を実行する

  from kabusys.data import schema
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = schema.init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

  コメント:
  - run_daily_etl は市場カレンダー→株価→財務→品質チェックの順で実行します。
  - J-Quants のトークンは settings.jquants_refresh_token を参照します（設定済みであれば自動使用）。

- J-Quants API を直接使ってデータ取得 / 保存

  from kabusys.data import jquants_client as jq
  from kabusys.config import settings
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)

- ニュース収集ジョブを実行する

  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema
  import duckdb

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes: 銘柄抽出に使用する有効な銘柄コード集合を渡すと紐付けが行われる
  res = run_news_collection(conn, known_codes={"7203", "6758"})

- Research（ファクター計算、IC 等）

  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

- 監査ログスキーマ初期化（発注監査用）

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")

- マーケットカレンダーユーティリティ

  from kabusys.data import calendar_management as cm
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  cm.calendar_update_job(conn)  # 夜間バッチ相当
  cm.is_trading_day(conn, date(2024,1,1))

- 品質チェックを単独で実行

  from kabusys.data.quality import run_all_checks
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date(2024,1,31))

## 自動環境変数読み込みの挙動
- パッケージの起動時に、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索し、`.env` と `.env.local` を自動読み込みします。
- 読み込みの優先順位:
  1. OS 環境変数
  2. .env.local（存在すれば上書き）
  3. .env（存在すれば設定）
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで使用）。

.env のパース仕様（主な点）
- 空行と `#` で始まる行は無視
- export VAR=val 形式も許容
- シングル/ダブルクォート内のエスケープに対応
- クォート無しの値では `#` の直前が空白/タブの場合にコメント扱い

## ディレクトリ構成（主要ファイル）
リポジトリはパッケージルート src/kabusys を想定しています。主要モジュールと概要は下記の通りです。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得 + 保存）
      - news_collector.py            — RSS ニュース収集・正規化・DB保存
      - schema.py                    — DuckDB スキーマ定義・初期化
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - etl.py                       — ETL 関連の公開型ラッパ
      - features.py                  — 特徴量ユーティリティのエクスポート
      - stats.py                     — 統計ユーティリティ（zscore_normalize）
      - quality.py                   — データ品質チェック
      - calendar_management.py       — マーケットカレンダー管理
      - audit.py                     — 監査ログ（シグナル→約定トレーサビリティ）
      - audit DB 初期化ユーティリティ等
    - research/
      - __init__.py
      - factor_research.py           — Momentum/Volatility/Value 等ファクター計算
      - feature_exploration.py       — 将来リターン、IC、サマリー
    - strategy/                       — 戦略関連（パッケージ化のエントリ）
    - execution/                      — 発注/執行関連（パッケージ化のエントリ）
    - monitoring/                     — 監視 / メトリクス（未実装箇所のエントリ）

（上記はコードベースからの抽出です。各モジュールに詳細なドキュメントが含まれています）

## 運用上の注意点
- 本リポジトリには発注処理の抽象・実装が含まれますが、実際の「本番取引」を行う前に十分なテストを行ってください。特に監査ログと冪等キー（order_request_id）の扱いは重要です。
- J-Quants など外部 API のキーは秘匿管理してください。`.env.local` を .gitignore に入れてローカルで管理することを推奨します。
- DuckDB のファイルはバックアップやバージョン管理（大きなバイナリは不可）を適切に行ってください。
- HFT 等の高頻度用途では本実装はレート制限や同期的な I/O がボトルネックになる可能性があるため、設計の見直しが必要です。

## 貢献・拡張
- strategy / execution / monitoring に戦略実装やブローカー連携をプラグインとして追加できます。
- ETL の品質チェックはプロダクションニーズに合わせてルールを拡張してください（例: 日中スパイクの閾値調整、銘柄別の許容差分など）。
- ニュースのソース追加や NLP による記事分類・センチメントスコアを追加すると特徴量として利用できます。

---

README の内容はコードベース（src/kabusys 内の各モジュール）を元に作成しています。実際に使用する際は、各モジュールの docstring と型注釈、ログ出力を参照して動作を確認してください。必要なら具体的なユースケース（ETL スケジュール、発注フロー、監査ポリシー）に合わせて README を拡張します。