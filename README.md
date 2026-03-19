# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（ETL / 特徴量生成 / シグナル生成 / データ収集 等）。

このリポジトリは、J-Quants など外部データソースからデータを取り込み、DuckDB に格納して戦略用の特徴量（features）を作成し、最終的に売買シグナルを生成するためのモジュール群を提供します。監査・実行層やニュース収集・市場カレンダー管理など、実運用を意識した設計が施されています。

---

## 主な機能一覧

- 環境変数管理（.env/.env.local の自動読み込み）
- J-Quants API クライアント
  - 日足（OHLCV）取得、財務データ取得、マーケットカレンダー取得
  - レート制限、リトライ、トークン自動リフレッシュ、ページネーション対応
- DuckDB スキーマ定義と初期化（冪等）
- ETL パイプライン（日次差分取得・保存・品質チェック）
- 特徴量計算（Momentum / Volatility / Value 等）
- 特徴量正規化（Zスコア正規化）
- シグナル生成（複数コンポーネントスコアの統合、BUY/SELL 判定、エグジット判定）
- ニュース収集（RSS -> raw_news 保存、銘柄コード抽出）
- 市場カレンダー管理（営業日判定、次/前営業日の取得、夜間バッチ更新）
- 監査ログ用スキーマ（signal_events / order_requests / executions 等）
- 基本的な統計ユーティリティ（IC 計算、将来リターン、ファクターサマリ等）

---

## 前提条件

- Python 3.10 以上（PEP 604 の `X | None` などの構文を利用しているため）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全対策）
- 標準ライブラリのみで実装されている箇所も多いですが、実行環境では上記パッケージをインストールしてください。

推奨パッケージ（最小限）
- duckdb
- defusedxml

必要に応じて Slack SDK や kabu API クライアント等を追加してください（本コードでは環境変数として Slack トークン等を要求する箇所があります）。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限：
     ```
     pip install duckdb defusedxml
     ```
   - 開発用に requirements.txt を用意している場合はそれを利用してください。
   - （オプション）パッケージを editable install にする場合：
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（execution 層で利用）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - オプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB 等に使用（デフォルト: data/monitoring.db）

   例 `.env` の最低例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABU_API_PASSWORD=your_password
   ```

---

## 使い方（基本的な手順・サンプル）

以下は Python スクリプト／REPL から主要処理を呼ぶ最小例です。

1. DuckDB スキーマを初期化
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")  # ディスク DB（parent ディレクトリは自動作成）
   # またはインメモリ:
   # conn = init_schema(":memory:")
   ```

2. 日次 ETL の実行（J-Quants から差分取得 → DuckDB に保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を指定しなければ今日を基準に実行
   print(result.to_dict())
   ```

3. 特徴量の作成（features テーブルへ書き込み）
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   n = build_features(conn, date(2024, 1, 1))
   print(f"features upserted: {n}")
   ```

4. シグナル生成（signals テーブルへ書き込み）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total = generate_signals(conn, date(2024, 1, 1), threshold=0.6)
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブ（RSS -> raw_news）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   # known_codes は記事中の4桁銘柄コード抽出に使用する有効コード集合（省略可）
   known_codes = {"7203", "6758", "9984"}  # 実運用では全銘柄セットを準備
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(res)
   ```

6. カレンダー更新ジョブ（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意:
- 上記の実行はすべて DuckDB 接続（conn）を共有して行うことを想定しています。
- 本リポジトリは CLI ツールを提供していないため、運用ではこれらをラッパーするスクリプトやジョブスケジューラ（cron / Airflow など）を用意して運用してください。

---

## 環境変数の自動ロードについて

- kabusys.config モジュールは実行時にプロジェクトルート（.git または pyproject.toml を探索）を検出し、`.env` → `.env.local` の順で自動ロードを行います。
- OS 環境変数は上書きされません（.env の上書きを防ぐ）。`.env.local` は上書きモードでロードされます。
- 自動ロードを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## 推奨ログ設定

- LOG_LEVEL 環境変数でログレベルを制御できます（デフォルト: INFO）。
- ランタイムでは標準的な logging 設定（ハンドラ、フォーマット、ファイル出力等）をアプリ側で行ってください。

---

## ディレクトリ構成（主要ファイル・モジュール解説）

（リポジトリルートの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 自動読み込み、Settings クラスによる設定取得
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ含む）
    - news_collector.py
      - RSS フィード収集、記事前処理、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等）
    - calendar_management.py
      - 営業日判定、calendar_update_job、next/prev/get_trading_days
    - audit.py
      - 監査ログ用の DDL（signal_events / order_requests / executions 等）
    - features.py
      - data.stats の再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - Momentum/Volatility/Value のファクター計算（prices_daily / raw_financials を参照）
    - feature_exploration.py
      - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py
      - 生ファクターの正規化・ユニバースフィルタ適用・features テーブルへの UPSERT
    - signal_generator.py
      - features と ai_scores を統合して final_score 計算、BUY/SELL シグナル生成、signals テーブルへの保存
  - execution/
    - __init__.py
      - （実装が含まれていないが発注・ブローカー連携用のエントリプレース）
  - monitoring/
    - （モニタリング関連の実装に使われる想定。現在は __all__ に含まれるのみ）

---

## 開発・運用上の注意点

- ルックアヘッドバイアス対策: ファクター計算・シグナル生成は target_date 時点で利用可能なデータのみを使う設計になっています。ETL の取得時刻（fetched_at）や DuckDB の保存時刻を活用してトレーサビリティを確保してください。
- 冪等性: 多くの保存処理（raw_prices / raw_financials / market_calendar / raw_news 等）は ON CONFLICT / DO UPDATE / DO NOTHING 等で冪等に設計されています。
- エラーハンドリング: ETL やニュース収集ジョブはソース単位でエラーを隔離し、他の処理は継続する設計になっています。監査・ログを有効にして問題解析を容易にしてください。
- テスト: 外部 API 呼び出し部分はトークン注入や internal helper のモック化が可能なように設計されています。ユニットテストを作る際は HTTP 層・ネットワーク呼び出しをモックしてください。

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートが .git または pyproject.toml により検出されない場合、自動ロードはスキップされます。必要であれば環境変数を直接 OS に設定するか、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にして手動で読み込んでください。
- DuckDB にテーブルが作成されない
  - init_schema() を実行してから ETL を呼んでください。DB ファイルの親ディレクトリが作成されることを確認してください。
- J-Quants API の 401 が出る
  - jquants_client は 401 でトークンを自動リフレッシュする実装がありますが、refresh token が正しく設定されているか確認してください。トークン取得処理（get_id_token）が失敗すると例外になります。

---

必要に応じて README を拡張（運用手順、サンプルワークフロー、CI/CD、テストの書き方など）します。追加で記載したい項目や、運用シナリオ（paper_trading / live）に関するガイドがあれば教えてください。