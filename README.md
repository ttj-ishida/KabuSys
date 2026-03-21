# KabuSys — 日本株自動売買基盤

KabuSys は日本株向けのデータプラットフォームと戦略モジュール群を備えた自動売買基盤のコードベースです。  
DuckDB をデータレイクとして用い、J-Quants からのデータ取得、ニュース収集、研究用のファクター/特徴量計算、シグナル生成、監査・実行層のためのスキーマとユーティリティを提供します。

主な設計方針:
- 研究（research）と実行（execution）を分離し、ルックアヘッドバイアスを防止するために target_date 時点のデータのみを使用
- DuckDB に対する冪等な保存（ON CONFLICT / INSERT … DO UPDATE 等）
- 外部 API 呼び出しはレート制限・リトライ・トークンリフレッシュを備えたクライアントで安全に扱う
- ニュース収集や RSS 処理で SSRF / XML 攻撃対策を実施

---

## 機能一覧

- データ取得・ETL
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - 差分更新 / バックフィルを考慮した ETL パイプライン（run_daily_etl 他）
  - DuckDB スキーマ定義と初期化（init_schema）
- データ処理 / Feature
  - ファクター計算（momentum / volatility / value）
  - クロスセクションの Z スコア正規化
  - features テーブル生成（build_features）
- 戦略（Signal）
  - 正規化済み特徴量と AI スコアの統合による final_score 計算
  - BUY / SELL シグナル生成（generate_signals）
  - Bear レジーム抑制、エグジット条件（ストップロス等）
- ニュース収集
  - RSS フィード収集・前処理・raw_news 保存、銘柄コード抽出と紐付け
  - SSRF / 大容量レスポンス / XML 攻撃への防御機構
- カレンダー管理
  - market_calendar の差分更新・営業日判定ユーティリティ（is_trading_day / next_trading_day 等）
- 監査・実行レイヤ用スキーマ
  - signals / orders / executions / positions / audit テーブル群

---

## 必要条件

- Python 3.9+（型注釈は 3.9 以降の表記を使用）
- DuckDB
- defusedxml
- （ネットワーク経由）J-Quants API トークンなどの環境変数

依存パッケージ（一例）
- duckdb
- defusedxml

プロジェクトに requirements.txt や pyproject.toml がある場合はそれに従ってください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   - git clone ...
   - pip install -e .

   依存が明示されている場合は `pip install -r requirements.txt` または `pip install .` を実行してください。

2. 必要な Python パッケージをインストール
   - pip install duckdb defusedxml

3. 環境変数の準備
   - ルートに .env ファイルを置くと自動で読み込まれます（プロジェクトルートの判定は .git または pyproject.toml に基づく）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須となる主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - （任意）DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - （任意）SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   .env の例（.env.example を用意しておくことを想定）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   Python REPL やスクリプトから以下を実行して DB とテーブルを作成します。

   - 例:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")

   init_schema はフォルダが存在しなければ自動作成し、DDL を冪等に実行します。

---

## 使い方（主要な API と実行例）

以下は代表的な操作の例です。実運用ではログ設定やエラーハンドリングを適切に追加してください。

- DuckDB の初期化（上記と同様）
  - from kabusys.data import schema
    conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（株価・財務・カレンダーの取得）
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn)  # target_date を指定可能
    print(result.to_dict())

- 市場カレンダー更新ジョブ
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)

- ニュース収集ジョブ（既知コードセットがあれば銘柄紐付けを実行）
  - from kabusys.data.news_collector import run_news_collection
    known = {"7203", "6758", ...}
    results = run_news_collection(conn, known_codes=known)

- 特徴量作成（features テーブルへ保存）
  - from kabusys.strategy import build_features
    from datetime import date
    cnt = build_features(conn, date(2026, 3, 20))

- シグナル生成（signals テーブルへ保存）
  - from kabusys.strategy import generate_signals
    from datetime import date
    total = generate_signals(conn, date(2026, 3, 20))

- J-Quants クライアントの個別利用例
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()
    recs = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,3,1))

注意点:
- run_daily_etl などは内部で J-Quants へリクエストを投げます。API レート・課金やトークンの取り扱いに注意してください。
- generate_signals / build_features は target_date 時点のデータのみを参照するよう設計されています。運用スケジューラ（cron 等）で対象日を適切に設定してください。

---

## ディレクトリ構成（主要ファイル）

（この README は src/kabusys のコード構成に基づきます）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env ロード、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（認証・ページネーション・保存）
    - news_collector.py      — RSS ニュース収集・前処理・DB保存
    - schema.py              — DuckDB スキーマ定義と init_schema
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — data.stats の再エクスポート
    - calendar_management.py — マーケットカレンダー管理ユーティリティ
    - audit.py               — 監査ログ用のテーブル定義（signal_events, order_requests, executions 等）
    - (その他: quality モジュール等がある想定)
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — IC/forward returns / 統計要約等の研究ユーティリティ
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル作成ロジック（build_features）
    - signal_generator.py    — final_score 計算・BUY/SELL シグナル生成（generate_signals）
  - execution/
    - __init__.py            — 発注・ブローカー連携等はここに実装（このコードベースでは初期化済み）
  - monitoring/              — 監視・モニタリング用モジュール（存在を示すエクスポート）
  - その他補助モジュールやドキュメントファイル（DataPlatform.md / StrategyModel.md など）

---

## 注意事項・運用メモ

- 環境変数は .env / .env.local から自動ロードされますが、OS 環境変数を優先します。.env.local は .env を上書きします。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
- J-Quants クライアントは 120 req/min のレート制限を守る設計です。大量の並列リクエストは避けてください。
- ニュース収集には SSRF・XML Bomb・大容量レスポンス対策を施していますが、外部ソースへのアクセスは運用上のリスクを考慮してください。
- 本パッケージは研究コード（research）と実行コード（execution）を含みます。実売買アカウントで利用する場合は十分なテストと安全対策（ペーパートレード、発注サンドボックス、レート制限、監査ログ確認など）を行ってください。

---

もし README に含めたい追加の運用手順（CI設定、Dockerization、systemd タイマー等）があれば教えてください。必要に応じてサンプル .env.example や簡易運用スクリプトも作成します。