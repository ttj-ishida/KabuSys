# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリセットです。  
データ収集（J-Quants）、ETL、特徴量生成、戦略シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、戦略開発から運用までの基盤機能を提供します。

---

## プロジェクト概要

主な目的は「日本株の定量投資アルゴリズムを研究・運用するための基盤」を提供することです。  
モジュールは概念的に以下のレイヤーを含みます。

- Data Layer（J-Quants からの生データ取得、DuckDB スキーマ）
- Processed Layer（prices_daily など整形済みデータ）
- Feature Layer（ファクター計算・正規化・features テーブル）
- Strategy（ファクター合成、最終スコア・シグナル生成）
- Execution / Audit（発注・約定・ポジション・監査ログのためのスキーマ）
- Research（研究用の解析ユーティリティ・IC計算など）
- News（RSS 収集・記事保存・銘柄紐付け）
- Calendar（JPX カレンダー取得・営業日判定）
- 設定管理（環境変数 / .env 自動読み込み）

設計上の重要点:
- DuckDB を永続ストレージとして利用（スキーマは冪等に初期化可能）
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動更新を実装
- ルックアヘッドバイアス回避（target_date 時点のデータのみ使用）
- 多くの操作は冪等に実装（ON CONFLICT / 日付単位の置換）

---

## 機能一覧

主な提供機能（抜粋）:

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート基準）
  - 必須設定の取得ユーティリティ（settings オブジェクト）
- データ取得 / 保存（kabusys.data.jquants_client）
  - 日足（OHLCV）・財務データ・市場カレンダー取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT）
  - レートリミッタ・リトライ・401 の自動トークン更新
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema() による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日からの差分）
  - run_daily_etl による日次 ETL（カレンダー→price→financials→品質チェック）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news 保存、銘柄コード抽出・紐付け
  - SSRF / XML Bomb / 大容量レスポンス対策などの堅牢化
- 特徴量計算（kabusys.research.factor_research / kabusys.strategy.feature_engineering）
  - Momentum / Volatility / Value 等のファクター計算
  - Zスコア正規化（kabusys.data.stats）
  - ユニバースフィルタ（最低株価・最低売買代金）
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算
  - Bear レジーム抑制、BUY/SELL 判定、signals テーブルへの書き込み（冪等）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（先読み + バックフィル）
- 統計 / 研究ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、ファクターサマリ等
- 監査ログ（audit）: signal → order_request → execution のトレース用スキーマ

---

## 動作環境 / 依存

- Python 3.10 以降（型ヒントのパイプ型などを使用）
- 必要な主なパッケージ（最低限）:
  - duckdb
  - defusedxml

（プロジェクトには他に標準ライブラリのみを使っている部分が多いですが、運用環境に合わせて追加パッケージが必要になる場合があります。）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# パッケージとして開発インストールできる場合:
pip install -e .
```

---

## 環境変数（必須 / 任意）

kabusys.config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（execution 層利用時）
- SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV           : execution モード。development / paper_trading / live（デフォルト development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...。デフォルト INFO）
- KABU_API_BASE_URL     : kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）

オートロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動読み込みします。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意:
- settings.jquants_refresh_token などは取得時に ValueError を出すため、必須値は事前に設定してください。
- .env.example を参考に .env を作成する想定です（リポジトリに含まれていれば参照）。

---

## セットアップ手順（簡易）

1. Python 3.10+ の準備、仮想環境のアクティベート
2. 依存ライブラリをインストール
   - 例: `pip install duckdb defusedxml`
   - プロジェクトの依存ファイルがある場合は `pip install -r requirements.txt`
3. 環境変数を設定（.env をプロジェクトルートに置くのが便利）
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
5. 日次 ETL の実行（例）
   - run_daily_etl を使って日次 ETL を実行できます（J-Quants トークンは settings から利用）
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_daily_etl
     conn = init_schema("data/kabusys.duckdb")
     result = run_daily_etl(conn)
     print(result.to_dict())
     ```

---

## 使い方（よく使う API の例）

- DuckDB スキーマの初期化 / 接続
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")   # 初期化して接続
  # or
  conn = get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn)  # target_date を渡せます
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードセット（抽出精度向上のため）
  stats = run_news_collection(conn, known_codes={"7203", "6758"})
  ```

- 特徴量生成（戦略用 features テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  n = build_features(conn, target_date=date(2024, 1, 31))
  ```

- シグナル生成（signals テーブルへ書き込み）
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  count = generate_signals(conn, target_date=date(2024, 1, 31))
  ```

- 研究用ユーティリティ（IC 計算や forward returns）
  ```python
  from kabusys.research import calc_forward_returns, calc_ic
  fwd = calc_forward_returns(conn, date(2024,1,31))
  ic = calc_ic(factor_records, fwd, "mom_1m", "fwd_5d")
  ```

---

## ディレクトリ構成（主要部分の抜粋）

リポジトリの主要ファイル / モジュール構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント + 保存関数
    - news_collector.py        # RSS 収集・保存・銘柄抽出
    - schema.py                # DuckDB スキーマ定義・初期化
    - stats.py                 # zscore 正規化等の統計ユーティリティ
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   # マーケットカレンダーの管理
    - features.py              # 再エクスポート用（zscore）
    - audit.py                 # 監査ログ用スキーマ定義
    - (その他: quality.py など想定)
  - research/
    - __init__.py
    - factor_research.py       # Momentum/Value/Volatility の計算
    - feature_exploration.py   # forward returns, IC, summary
  - strategy/
    - __init__.py
    - feature_engineering.py   # raw factor -> normalized features -> features table
    - signal_generator.py      # final_score 計算、BUY/SELL 判定
  - execution/                 # execution 層（発注関連: 実装箇所は別ファイル）
  - monitoring/                # 監視・アラート類（別途実装）
  - (その他)

---

## 運用上の注意

- 本コードは発注（実口座）に使う前に十分なテスト・レビューを行ってください。特に execution 層と実ブローカーとの接続、エッジケース（再送、部分約定、価格欠損）のハンドリングを確認してください。
- 環境変数・シークレットは安全に管理してください（.env を Git にコミットしない）。
- J-Quants の API レート制限（120 req/min）を守るため、jquants_client 内にレートリミッタが組み込まれていますが、複数プロセスからの同時実行では追加の調整が必要です。
- DuckDB ファイルのリソース管理（バックアップ、ロック、共有アクセス）について運用ポリシーを作成してください。
- テーブルの外部キー制約や ON DELETE の制限は DuckDB のバージョン差異に影響されるため、実運用前にスキーマを確認してください。

---

必要であれば、README に含めるサンプル .env.example、より詳細な CLI/サービス起動手順、監視ダッシュボード連携方法、単体テストの実行方法などを追加します。どの情報がさらに必要か教えてください。