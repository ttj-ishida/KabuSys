# KabuSys

日本株向けの自動売買/データプラットフォーム用ライブラリです。  
DuckDB をデータ基盤として、J-Quants から市場データを取得 → ETL → 特徴量生成 → シグナル生成 → 発注／監査までの一連処理を想定したモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアス防止（各処理は target_date 時点のデータのみを使用）
- 冪等性（DB への保存は ON CONFLICT 等で重複を抑制）
- 外部 API 呼び出しは data 層に集約、strategy / execution 層は発注 API に直接依存しない
- ネットワークや XML 処理に対する安全対策（レートリミット、リトライ、SSRF 防御、gzip 上限など）

## 機能一覧

- 環境設定
  - .env / .env.local の自動読み込み（設定の上書き制御、プロジェクトルート検出、無効化オプションあり）
  - 必須環境変数の検査（settings オブジェクト）
- データ取得（J-Quants クライアント）
  - 日次株価（OHLCV）、四半期財務データ、JPX カレンダーを取得
  - レートリミット、指数バックオフ、401 の自動トークンリフレッシュ、ページネーション対応
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- ETL パイプライン
  - 差分取得 / バックフィル / 市場カレンダー先読み
  - 品質チェックフレームワーク呼び出し（quality モジュール想定）
  - 日次 ETL 結果を ETLResult として返却
- スキーマ管理
  - DuckDB のスキーマ定義・初期化（init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
- ニュース収集
  - RSS フィード取得 → 前処理 → raw_news 保存 → 銘柄抽出（SSRF 対策、gzip 上限、トラッキングパラメータ除去）
- 特徴量エンジニアリング（戦略用）
  - research 側の生ファクターを集約、ユニバースフィルタ、Z スコア正規化、±3 でクリップして features テーブルへ UPSERT
- シグナル生成
  - features / ai_scores を統合して final_score を算出
  - Bear レジーム判定、BUY/SELL 条件判定（ストップロス等）、signals テーブルへの書き込み（冪等）
- 研究用ユーティリティ
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ等
- カレンダー管理
  - 営業日判定、前後営業日の取得、カレンダー夜間更新ジョブ
- 監査ログ（audit）
  - シグナル→発注要求→約定のトレーサビリティテーブル定義（UUID ベースの階層構造）
- 実行（execution）層のプレースホルダ（発注連携を実装可能）

## 必要条件

- Python 3.10 以上を推奨（typing のモダン機能を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API 等）

インストール例（最低限）:
```
pip install duckdb defusedxml
```

（プロジェクトをパッケージ化している場合は `pip install -e .` などを利用してください。requirements.txt がある場合はそちらを使用してください。）

## 環境変数 / 設定

config.Settings が参照する主な環境変数：

- JQUANTS_REFRESH_TOKEN  - J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      - kabuステーション API パスワード（必須）
- KABU_API_BASE_URL      - kabuAPI ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        - Slack Bot Token（必須）
- SLACK_CHANNEL_ID       - Slack チャンネル ID（必須）
- DUCKDB_PATH            - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            - SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV            - 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL              - ログレベル（DEBUG/INFO/...、デフォルト: INFO）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を親階層に探す）に `.env` / `.env.local` があれば自動読み込みされます。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意: README にある `.env.example` を参考に実際の `.env` を作成してください（コード内で参照する必須変数を設定すること）。

## セットアップ手順（最小手順）

1. Python と依存ライブラリをインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

2. 環境変数を準備
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトから init_schema を呼び出します（デフォルトファイルは settings.duckdb_path を参照）。
   例:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

4. 日次 ETL 実行（サンプル）
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

5. 特徴量生成 → シグナル生成（サンプル）
   ```python
   from datetime import date
   from kabusys.data.schema import get_connection
   from kabusys.strategy import build_features, generate_signals
   from kabusys.config import settings

   conn = get_connection(settings.duckdb_path)
   target = date.today()
   num_features = build_features(conn, target)
   print("features upserted:", num_features)

   num_signals = generate_signals(conn, target)
   print("signals created:", num_signals)
   ```

6. ニュース収集（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection
   from kabusys.config import settings

   conn = get_connection(settings.duckdb_path)
   # known_codes は銘柄抽出に使う有効コード集合（None だと銘柄抽出をスキップ）
   results = run_news_collection(conn, known_codes={"7203", "6758"})
   print(results)
   ```

## 使い方（主要 API）

- スキーマ初期化
  - init_schema(db_path) -> DuckDB 接続（最初に必ず実行）
  - get_connection(db_path) -> 既存 DB へ接続

- ETL / データ
  - run_daily_etl(conn, target_date=...) -> ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl （個別ジョブ）
  - jquants_client.fetch_* / save_* : 低レベル API（必要な場合のみ）

- 特徴量・戦略
  - build_features(conn, target_date) -> upsert 件数
  - generate_signals(conn, target_date, threshold=..., weights=...) -> signals 件数

- ニュース
  - run_news_collection(conn, sources=None, known_codes=None) -> {source: saved_count}

- カレンダー
  - is_trading_day(conn, date), next_trading_day(...), prev_trading_day(...), get_trading_days(...), calendar_update_job(...)

- 監査 / 発注（テーブル設計は実装済み、発注実装は execution 層で行う想定）

## ディレクトリ構成

リポジトリの主要なファイル/ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                        # 環境変数 / Settings
    - data/
      - __init__.py
      - jquants_client.py              # J-Quants API クライアント（取得・保存）
      - news_collector.py              # RSS ニュース収集・保存・銘柄抽出
      - schema.py                      # DuckDB スキーマ定義・init_schema
      - stats.py                       # zscore_normalize 等の統計ユーティリティ
      - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
      - features.py                    # data 層の特徴量ユーティリティ公開
      - calendar_management.py         # 市場カレンダー管理
      - audit.py                       # 監査ログ（シグナル→発注→約定トレーサビリティ）
      - (その他: quality.py 等は想定)
    - research/
      - __init__.py
      - factor_research.py             # モメンタム / ボラティリティ / バリュー計算
      - feature_exploration.py         # 将来リターン / IC / 統計サマリ
    - strategy/
      - __init__.py
      - feature_engineering.py         # features テーブル生成（build_features）
      - signal_generator.py            # signals 生成（generate_signals）
    - execution/
      - __init__.py                    # 発注ロジックはここに実装（現状プレースホルダ）
    - monitoring/                       # 監視・メトリクス用（SQLite 等）想定
    - その他モジュール...

（上記は現状の主要モジュールを示しています。細かいファイルはリポジトリをご確認ください。）

## 開発上の注意点 / 補足

- DuckDB はファイルベースですが並列アクセスやバックアップの運用設計は必要です。運用時は適切な DB パス設定、バックアップ戦略を検討してください。
- J-Quants API の利用にはトークンや利用規約が必要です。レート制限を守るためにクライアントの設定を変更しないでください。
- RSS の取得は外部 URL に依存します。SSRF 対策やレスポンス上限を実装していますが、追加のセキュリティ対策が必要な場合は強化してください。
- strategy 層は発注 API に依存しない設計です。実際の発注（execution 層）実装時は、監査テーブルと冪等キー設計を遵守してください。
- .env の自動ロードはプロジェクトルート検出に依存します。CI/デプロイ環境では環境変数で上書きすることを推奨します。

## 例: 簡易ワークフロー

1. init_schema で DB を初期化する
2. run_daily_etl でデータを取得・保存する
3. build_features で features を作成する
4. generate_signals で signals を生成する
5. execution 層で signals を処理し、orders / executions / positions を更新する
6. audit テーブルに各イベントを記録する

---

この README はコードベースの現状に基づいて要点をまとめたものです。詳細な仕様（StrategyModel.md、DataPlatform.md、など）は別途ドキュメントをご参照ください。必要であれば README に含める使い方のサンプルや運用手順（CRON / ワーカー構成、監視方法など）を追加で作成します。