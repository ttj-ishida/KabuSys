# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。データ取得・ETL、ファクター計算、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等を含むモジュール群を提供します。本リポジトリはパッケージ化されており、DuckDB をバックエンドにデータを保管して戦略/運用パイプラインを構築できます。

主な用途：
- J-Quants API と連携した株価・財務・カレンダー等の差分 ETL
- 研究用ファクター計算（Momentum / Value / Volatility 等）
- 特徴量の正規化・合成（features テーブル生成）
- 戦略の最終スコア計算と売買シグナル生成（signals テーブル）
- RSS ベースのニュース収集と銘柄紐付け
- マーケットカレンダーの管理（営業日判定など）
- 発注・約定・ポジション等の監査ログ（監査用テーブル定義）

---

## 機能一覧

- 環境設定読み込みと管理（.env / .env.local / 環境変数）
- J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ）
- DuckDB スキーマ定義と初期化（冪等な DDL 実行）
- 日次 ETL パイプライン（prices / financials / calendar の差分取得と保存）
- ファクター計算（momentum / volatility / value）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（コンポーネントスコア集約、BUY/SELL 判定、エグジット判定）
- ニュース収集（RSS 取得・前処理・記事保存・銘柄抽出）
- マーケットカレンダー管理・営業日ユーティリティ
- 監査ログ用スキーマ（signal_events, order_requests, executions 等）
- 汎用統計ユーティリティ（zscore_normalize 等）

---

## セットアップ手順

1. Python 環境を用意（推奨: Python 3.9+）
   - 仮想環境を作成して有効化する例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .venv\Scripts\activate.bat  # Windows (cmd)
     ```

2. 必要なパッケージをインストール
   - 本リポジトリに requirements.txt がない場合は最低限以下をインストールしてください:
     ```
     pip install duckdb defusedxml
     ```
     （実行環境や追加機能に応じて他ライブラリが必要になることがあります）

3. パッケージを編集可能モードでインストール（プロジェクトルートに pyproject.toml または setup ファイルがある前提）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意/デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 を設定）
   - .env 自動読み込み:
     - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に対して .env と .env.local を自動読み込みします。
     - 読み込み順序: OS 環境変数 > .env.local > .env

   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

---

## 使い方（簡易例）

以下は代表的な利用フローの例です。すべて Python API を直接呼び出す方法です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ファイルを作成してスキーマ初期化
  ```

- 日次 ETL を実行（市場カレンダー・株価・財務を差分取得して保存）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # デフォルトは今日
  print(result.to_dict())
  ```

- 特徴量（features）を構築
  ```python
  from datetime import date
  from kabusys.strategy import build_features
  build_count = build_features(conn, date(2024, 1, 4))
  print(f"features upserted: {build_count}")
  ```

- シグナル生成
  ```python
  from datetime import date
  from kabusys.strategy import generate_signals
  count = generate_signals(conn, date(2024, 1, 4))
  print(f"signals written: {count}")
  ```

- ニュース収集ジョブ実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes: 事前に存在する銘柄コードセット（extract_stock_codes に利用）
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)
  ```

- マーケットカレンダー更新（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar records saved: {saved}")
  ```

- 設定値へアクセス
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live
  ```

注意点：
- ETL / データ取得系は J-Quants API を使用するため、J-Quants の認証情報が必要です。
- news_collector は外部 RSS を取得するためネットワークアクセスが必要です。SSRF や XML 爆弾などに対する防御（defusedxml・ホスト判定・サイズ制限）を実装済みです。
- generate_signals / build_features は DuckDB 内のテーブル（prices_daily / raw_financials / features 等）に依存します。事前に ETL とスキーマ初期化を行ってください。

---

## ディレクトリ構成（主なファイル）

以下はパッケージ内の主要モジュールと役割の一覧です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（J-Quants トークン、kabu API、Slack、DB パス、環境設定）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（fetch / save 関数、レート制限・リトライ）
    - news_collector.py
      - RSS 取得・正規化・DB 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - stats.py
      - zscore_normalize 等統計ユーティリティ
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（ETL パイプライン）
    - features.py
      - data.stats の再エクスポート
    - calendar_management.py
      - market_calendar 操作・営業日判定・更新ジョブ
    - audit.py
      - 監査ログ用テーブル定義（signal_events, order_requests, executions 等）
    - (その他: quality モジュールを想定)
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value ファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - strategy/
    - __init__.py
      - build_features, generate_signals を公開
    - feature_engineering.py
      - features テーブル構築（ファクター結合・Zスコア正規化・ユニバースフィルタ）
    - signal_generator.py
      - final_score 計算、BUY/SELL 生成、signals テーブル書き込み
  - execution/
    - __init__.py
      - 発注・実行層のエントリ（将来的な拡張ポイント）
  - monitoring (参照用)
    - （モジュールがあれば監視・メトリクス関連）

---

## 開発・運用上の注意

- 自動 .env ロードはプロジェクトルートの .env / .env.local を読み込みます。テスト等で無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化は init_schema() を必ず一度呼んでください。既存テーブルがあれば冪等的にスキップします。
- J-Quants API のレート制限（デフォルト 120 req/min）に注意。jquants_client は固定間隔スロットリングとリトライを実装しています。
- ニュース取得や外部 URL の処理は SSRF / XML 攻撃対策を行っていますが、運用中の監視と適切なネットワーク制御は推奨されます。
- KABUSYS_ENV により本番（live）／ペーパー（paper_trading）／開発（development）の挙動分岐を行います。live 実行時は特にリスク管理を厳格にしてください。

---

## 参考・今後の拡張

- execution 層（実際のブローカー API 連携）、リスク管理（ポジション制限・ドローダウン制御）、バックテスト用のラッパー等は今後の拡張対象です。
- テスト・CI、ドキュメント（StrategyModel.md, DataPlatform.md 等）を充実させることで再現性と運用信頼性を高めてください。

---

質問や README の補足（詳しい API 使用例、テーブル定義の解説、運用ガイドなど）を希望される場合は、どの部分を詳しく書いてほしいか教えてください。