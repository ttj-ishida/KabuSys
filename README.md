# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ KabuSys の README です。  
このリポジトリは市場データ取得・ETL・特徴量計算・シグナル生成・ニュース収集・監査ログ等を含む一連の仕組みを提供します。

目次
- プロジェクト概要
- 主な機能一覧
- 前提条件 / 必要な環境
- セットアップ手順
- 使い方（主要 API・実行例）
- 環境変数（設定項目）
- ディレクトリ構成（主要ファイル説明）
- 補足 / 注意事項

---

## プロジェクト概要

KabuSys は日本株に対する研究 → 運用までを支えるライブラリ群です。  
主な目的は以下です：

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたローカルデータベースの管理（Raw / Processed / Feature / Execution 層）
- 研究用ファクター計算とクロスセクション正規化（Zスコア）
- 戦略用特徴量生成（feature layer）とシグナル生成（BUY/SELL 判定）
- RSS ベースのニュース収集と銘柄紐付け
- 発注・約定・ポジション等の監査ログスキーマ（トレース可能な監査フロー）
- ETL パイプラインと品質チェック

設計は「ルックアヘッドバイアスの防止」「冪等性」「外部 API のレート制御／リトライ」「DB トランザクションを用いた原子性確保」を重視しています。

---

## 主な機能一覧

- data/jquants_client:
  - J-Quants API 呼び出し（認証、自動リフレッシュ、ページネーション、レート制御、保存用ユーティリティ）
  - 生データの DuckDB への冪等保存（raw_prices, raw_financials, market_calendar など）
- data/schema:
  - DuckDB のスキーマ定義と初期化（init_schema）
- data/pipeline:
  - 日次 ETL（run_daily_etl）: カレンダー・株価・財務の差分取得と保存、品質チェック
  - 個別 ETL ジョブ: run_prices_etl / run_financials_etl / run_calendar_etl
- data/news_collector:
  - RSS 取得、記事前処理、raw_news 保存、銘柄抽出と紐付け
  - SSRF 対策、サイズ制限、XML 安全パーサ使用（defusedxml）
- data/calendar_management:
  - market_calendar の管理、営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - カレンダー更新ジョブ（calendar_update_job）
- data/audit:
  - シグナル → 発注 → 約定 をトレースする監査スキーマ定義
- data/stats:
  - zscore_normalize（クロスセクション Z スコア正規化）
- research:
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（前方リターン、IC 計算、統計サマリー）
- strategy:
  - feature_engineering.build_features（raw ファクターを正規化して features テーブルに保存）
  - signal_generator.generate_signals（features と ai_scores を統合して BUY/SELL シグナル生成）
- execution:
  - 発注／execution 層の入出力用スキーマ（orders / trades / positions 等）を含む（実際のブローカー接続は別実装）

---

## 前提条件 / 必要な環境

- Python 3.10 以上（コード内で使用されている型ヒント（X | Y）に対応）
- 必要パッケージ（一例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）
- J-Quants や Slack 等の API トークン（環境変数で設定）

（実際の requirements.txt / poetry 設定に従ってインストールしてください）

---

## セットアップ手順

1. リポジトリを取得してインストール（開発モード例）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```
   または poetry / pipenv 等を使用して依存を解決してください。

2. 必要パッケージのインストール（例）
   ```
   pip install duckdb defusedxml
   ```

3. 環境変数の準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須の環境変数（例は下の「環境変数」セクション参照）。

4. DuckDB スキーマ初期化
   Python REPL やスクリプトから:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   これで必要なテーブルが作成されます。

---

## 使い方（主要 API・実行例）

以下はライブラリを使った代表的な処理例です。

1. DuckDB の初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（市場データ取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量計算（feature layer 生成）
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   count = build_features(conn, target_date=date.today())
   print(f"features upserted: {count}")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   n = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals generated: {n}")
   ```

5. ニュース収集ジョブの実行
   ```python
   from kabusys.data.news_collector import run_news_collection

   # known_codes: 銘柄コード（文字列）のセット。存在しれば記事から銘柄抽出して紐付けを行う。
   results = run_news_collection(conn, known_codes={"7203", "6758"})
   print(results)  # ソースごとの新規保存数
   ```

6. カレンダー更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print(f"market_calendar saved: {saved}")
   ```

注意:
- これらは DB に対する変更を行います。まずは ":memory:" を指定して試すか、別ファイルを使って検証してください。
- run_daily_etl は品質チェックを実行します。品質異常が検出されても ETL は継続され、結果オブジェクトに問題が記録されます。

---

## 環境変数（設定項目）

kabusys は環境変数（または .env ファイル）で設定を読み込みます。主要なもの:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携を行う場合）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（通知連携を実装している場合）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")。デフォルト "development"
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)。デフォルト "INFO"
- KABU_API_BASE_URL: kabu API のベース URL。デフォルト "http://localhost:18080/kabusapi"
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト "data/kabusys.duckdb"
- SQLITE_PATH: 監視用 SQLite パス。デフォルト "data/monitoring.db"
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合は 1 を設定

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## ディレクトリ構成（主要ファイルの説明）

以下はパッケージの主要な構成（src/kabusys）です。提供されたコードに基づく抜粋です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード (.env/.env.local) と Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、リトライ、レートリミット、保存ユーティリティ）
    - news_collector.py
      - RSS フィード取得、前処理、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB の DDL 定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - features.py
      - zscore_normalize のエクスポート
    - calendar_management.py
      - market_calendar 管理と営業日ユーティリティ、calendar_update_job
    - audit.py
      - 監査ログ（signal_events / order_requests / executions 等）の DDL
    - stats.py
      - zscore_normalize の実装
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py
      - build_features（生ファクター → features テーブルへの正規化・UPSERT）
    - signal_generator.py
      - generate_signals（features + ai_scores から final_score → signals テーブル）
  - execution/
    - __init__.py
    - （発注・ブローカー連携の実装は別途）

この README は上記ファイル群の主要な役割を示しています。実際の詳細仕様（StrategyModel.md, DataPlatform.md 等）は別ドキュメントを参照してください。

---

## 補足 / 注意事項

- DuckDB の DDL は外部キー制約や ON DELETE 挙動などで DuckDB のバージョン依存の注意点があります（コード内コメント参照）。
- J-Quants API 呼び出しではレート制限（120 req/min）や 401 自動リフレッシュ、429 の Retry-After を考慮した実装になっています。大量取得時は API 制限に注意してください。
- ニュース収集では XML パースに defusedxml を使用して安全性を高めています。HTTP レスポンスサイズやリダイレクト先のプライベート IP 検査など SSRF／DoS 対策を組み込んでいます。
- 本ライブラリは研究・運用両方を想定していますが、実際のブローカー発注や資金管理は慎重に行ってください（paper_trading 環境の活用を推奨します）。

---

必要に応じて README に追記します。たとえば、CI / テスト方法、より詳しいサンプルワークフロー、各テーブルのスキーマ説明などが必要であれば指示してください。