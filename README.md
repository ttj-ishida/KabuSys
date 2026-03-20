# KabuSys — 日本株自動売買基盤（README）

概要
---
KabuSys は日本株向けのデータプラットフォームと戦略層を備えた自動売買基盤の軽量実装です。本リポジトリは以下の責務を持つモジュール群を含みます。

- データ取得・保存（J-Quants 経由の株価・財務・カレンダー / RSS ニュース）
- DuckDB を用いたデータスキーマと永続化（Raw / Processed / Feature / Execution 層）
- 研究用ファクター計算（モメンタム / ボラティリティ / バリュー等）
- 特徴量正規化、シグナル生成ロジック（BUY / SELL 判定）
- ETL パイプライン、カレンダー管理、ニュース収集、監査（audit）機能
- 設定は環境変数（.env）で管理

主な特徴
---
- DuckDB ベースのシンプルな永続化スキーマ（冪等性を重視した INSERT / ON CONFLICT 処理）
- J-Quants API クライアント（レート制限・再試行・トークン自動リフレッシュ対応）
- RSS 収集時の SSRF 防止・XML 攻撃対策（defusedxml、リダイレクト検査、受信サイズ制限）
- ルックアヘッドバイアスを避ける設計（target_date 時点のデータだけを使用）
- 研究/本番で同じロジックが使えるように分離された research / strategy / data 層
- ETL の差分更新・バックフィル、品質チェックフレームワーク

セットアップ手順
---
前提
- Python 3.10 以上（Union 型記法（X | Y）を使用しているため）
- Git、pip

1. リポジトリを取得
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

   ※ 本コードベースは標準ライブラリを多用しています。上記は必須ライブラリの例です。

4. 環境変数の設定
   プロジェクトルートに `.env` を作成することで自動読み込みされます（既定で OS 環境変数 > .env.local > .env の順で読み込み）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB）
   必要なディレクトリを作成し、スキーマを初期化します（Python スクリプトで実行）。

   サンプル:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```

使い方（主要 API）
---
下記は代表的なユースケースと呼び出し例です。各関数は DuckDB の接続オブジェクト（duckdb.connect の戻り値）を受け取ります。

1. DuckDB 接続を作る / スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema, get_connection

   # 初回: スキーマ作成して接続を受け取る
   conn = init_schema("data/kabusys.duckdb")

   # 既存 DB へ接続するだけ（スキーマ初期化は行わない）
   conn2 = get_connection("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（J-Quants から株価・財務・カレンダーを取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

   - 既定で API トークンは `settings.jquants_refresh_token`（環境変数）から取得します。
   - run_daily_etl は品質チェック（quality モジュール）も実行します（オプションで無効化可）。

3. 特徴量の構築（features テーブル）
   ```python
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024, 1, 5))
   print(f"features upserted: {count}")
   ```

4. シグナル生成（signals テーブルへ書き込み）
   ```python
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection
   from datetime import date

   conn = get_connection("data/kabusys.duckdb")
   signals_written = generate_signals(conn, target_date=date(2024, 1, 5))
   print(f"signals written: {signals_written}")
   ```

   - generate_signals はデフォルト重み・閾値を使います。第 3 引数 weights で重みを調整できます。

5. ニュース収集（RSS）と保存
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9984"}  # 抽出時に参照する有効銘柄コードセット
   results = run_news_collection(conn, sources=None, known_codes=known_codes)
   print(results)
   ```

6. J-Quants から個別にデータ取得して保存
   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   # 例: ある銘柄の期間を取得して保存
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31), code="7203")
   saved = jq.save_daily_quotes(conn, records)
   print(f"saved: {saved}")
   ```

設定・環境変数
---
主に以下の環境変数が使用されます。必須のものは Settings で _require() されます。

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（execution 層で利用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 送信先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 (development|paper_trading|live)（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）

自動 .env ロード:
- プロジェクトルート（.git か pyproject.toml があるディレクトリ）にある `.env` / `.env.local` が自動的に読み込まれます。
- 自動ロードを停止する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

ディレクトリ構成（概要）
---
以下はソースに含まれる主要モジュールとその役割（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（レート制御、リトライ、保存ユーティリティ）
    - news_collector.py
      - RSS 取得・記事保存・銘柄抽出ロジック（SSRF/XML 対策）
    - schema.py
      - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution）
    - stats.py
      - 汎用統計関数（zscore_normalize）
    - pipeline.py
      - ETL パイプライン（run_daily_etl など）
    - calendar_management.py
      - 市場カレンダー管理（is_trading_day, next_trading_day 等）
    - audit.py
      - 監査ログ用 DDL（signal_events / order_requests / executions）
    - features.py
      - data.stats の公開ラッパー
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py
      - 将来リターン計算・IC（Spearman）・統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - research の生ファクターを合成して features テーブルに書き込む
    - signal_generator.py
      - features + ai_scores を統合して final_score を算出、signals テーブルに保存
  - execution/
    - __init__.py
      - （発注・約定を扱う層、未実装／別モジュールで拡張想定）
  - monitoring/
    - （監視・メトリクス連携は別モジュールで実装想定）

設計上の注意点
---
- ルックアヘッドバイアス防止: feature / signal 計算は target_date 時点で利用可能なデータのみで行われます。
- 冪等性: 保存処理は可能な限り ON CONFLICT / INSERT ... DO UPDATE / INSERT ... DO NOTHING を使い冪等化を図っています。
- DB 初期化: init_schema は既存テーブルがある場合はスキップするので、本番で複数回呼んでも安全です。
- テスト容易性: jquants_client の id_token や news_collector の _urlopen などは注入・モックしやすい形で実装されています。

開発者向け情報
---
- Python 型ヒント・ロギングを積極的に利用しています。ユニットテストを書く際は duckdb のインメモリ接続（":memory:"）を使うと高速に実行できます。
- ニュース収集・外部 API 呼び出しはネットワーク依存なので、テストでは HTTP 層をモックすることを推奨します。
- エラー発生時は各種ジョブ（ETL / news collection 等）は部分的に継続する設計です。呼び出し元は ETLResult の has_errors / has_quality_errors を確認して追加処理してください。

ライセンス・貢献
---
（ここにプロジェクトのライセンス、貢献方法、連絡先などを追記してください）

---

この README はコードの現状（src 以下にあるモジュール）を基に作成しています。運用やデプロイ、CI/CD、実際のブローカー連携（kabu ステーションとの発注処理）については別ドキュメント（運用ガイド / API キー管理 / セキュリティ）を用意することを推奨します。必要であれば README に追加したい項目（例: よくあるエラーと対処法、サンプル設定ファイルの完全版、テストの実行方法）を指定してください。