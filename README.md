# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ。  
市場データの取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ管理などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つ Python モジュール群です。

- J-Quants API からの市場データ / 財務データ / 市場カレンダー取得（レート制御・リトライ付き）
- DuckDB を用いたデータベーススキーマ定義と冪等な保存
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 特徴量エンジニアリング（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（複数ファクター + AI スコアの重み付け合成、BUY/SELL 判定）
- RSS ベースのニュース収集と銘柄抽出（SSRF 対策、トラッキングパラメータ除去）
- 監査ログ（発注〜約定のトレーサビリティ）など

設計上のポイント:
- ルックアヘッドバイアスを避けるため、各処理は target_date 時点で利用可能なデータのみを参照
- DuckDB によるローカルデータベースで高速に集計・保存が可能
- 外部 API 呼び出しは専用クライアントに集約（認証・リトライ・レート制御）
- 冪等性を重視した DB 保存（ON CONFLICT / INSERT ... RETURNING 等）

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、トークン自動リフレッシュ、リトライ、レート制御）
  - schema: DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - pipeline: 日次 ETL（差分取得、保存、品質チェック）
  - news_collector: RSS 取得・前処理・DB 保存・銘柄紐付け
  - calendar_management: 営業日判定・カレンダー更新ジョブ
  - stats / features: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Value / Volatility / Liquidity 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリー
- strategy/
  - feature_engineering: research の生ファクターを正規化・合成して features テーブルへ保存
  - signal_generator: features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成
- audit / execution / monitoring: 監査ログ・発注・モニタリングの拡張ポイント（スキーマ・テーブル定義あり）

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部機能を利用）
- DuckDB が pip でインストール可能な環境
- ネットワーク経由で J-Quants API に接続できること（API トークンが必要）

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト配布に requirements.txt があればそれを使用してください）

3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注連携時）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - 任意（デフォルトあり）:
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視データベース（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/...

4. （オプション）パッケージとしてインストール
   - プロジェクト配布に setuptools 設定があれば `pip install -e .` など

---

## 使い方（簡易チュートリアル）

以下は代表的な利用例です。Python REPL / スクリプトで実行してください。

1. DuckDB スキーマの初期化
   - 例: ファイル DB を初期化して接続を取得する
     ```python
     from kabusys.data import schema
     from kabusys.config import settings

     conn = schema.init_schema(settings.duckdb_path)  # デフォルト: data/kabusys.duckdb
     ```

   - メモリ DB（テスト）:
     ```python
     conn = schema.init_schema(":memory:")
     ```

2. 日次 ETL の実行
   - J-Quants から差分取得して DB に保存、品質チェックまで実行
     ```python
     from kabusys.data.pipeline import run_daily_etl
     result = run_daily_etl(conn)  # target_date を指定可能
     print(result.to_dict())
     ```

3. 特徴量構築（strategy.feature_engineering）
   - research の生ファクターを正規化して features テーブルへ保存
     ```python
     from kabusys.strategy import build_features
     from datetime import date
     n = build_features(conn, date(2024, 1, 5))
     print(f"features upserted: {n}")
     ```

4. シグナル生成（strategy.signal_generator）
   - features / ai_scores / positions を参照して BUY/SELL シグナルを作成し signals テーブルへ保存
     ```python
     from kabusys.strategy import generate_signals
     from datetime import date
     total = generate_signals(conn, date(2024, 1, 5))
     print(f"signals written: {total}")
     ```

5. ニュース収集（RSS）
   - RSS を取得して raw_news に保存、銘柄紐付け
     ```python
     from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     saved_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
     print(saved_map)
     ```

6. J-Quants 生データ取得（低レベル）
   - jquants_client の fetch / save 関数を直接利用可能
     ```python
     from kabusys.data import jquants_client as jq
     recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
     jq.save_daily_quotes(conn, recs)
     ```

注意点:
- J-Quants API はレート制限（デフォルト 120 req/min）を守るため内部で待機します。
- get_id_token はリフレッシュトークンから ID トークンを取得します。環境変数 JQUANTS_REFRESH_TOKEN を設定してください。
- ETL やニュース収集はエラー発生時にも他ソース・他ステップを継続するよう設計されています（ログを確認してください）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード（発注に必要）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 を設定）

.env の読み込みルール:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` を自動で読み込み。
- `.env.local` は `.env` を上書きする（OS 環境変数の保護あり）。
- 複雑な .env のパース（クォート、コメント、export プレフィックスなど）に対応。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - features.py
      - stats.py
      - audit.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (パッケージ参照用に想定されているが実装はモジュールに依存)
- pyproject.toml / setup.cfg / README.md （プロジェクト構成ファイル）

各パッケージの概要:
- kabusys.config: 環境変数・設定管理（自動 .env 読み込み、必須チェック）
- kabusys.data: データ取得・保存・スキーマ・ETLに関する実装
- kabusys.research: リサーチ用のファクター計算・統計ユーティリティ
- kabusys.strategy: 特徴量の組み立てとシグナル生成
- kabusys.execution / monitoring: 発注・監視・監査関連（スキーマ・ログ設計が含まれる）

---

## 開発 / テスト時のヒント

- テスト時は環境ファイルの自動読み込みを無効化:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- メモリ DB を使えばファイル IO を避けて軽量テストが可能:
  - schema.init_schema(":memory:")
- ニュース RSS 取得は外部ネットワークに依存するため、fetch_rss / _urlopen をモックして単体テストを行うことを推奨。
- J-Quants クライアントはトークン取得とレート制御を内部で行うため、API のモックを作ると安定したテストが可能。

---

## トラブルシューティング

- 「環境変数が設定されていません」と出る:
  - 必須の環境変数（JQUANTS_REFRESH_TOKEN 等）を .env または OS 環境に設定してください。
- DuckDB に接続できない / テーブルがない:
  - schema.init_schema(path) を実行してテーブルを作成してください。
- API 呼び出しで 429 や 500 が頻発:
  - jquants_client はリトライ・バックオフ・RateLimiter を備えていますが、短時間に多数のリクエストを出していると制限にかかります。取得対象を絞るか、間隔を空けてください。
- RSS 取得で「プライベートアドレス」関連の警告が出る:
  - SSRF 防御のためです。リダイレクトやホスト解決結果がプライベート/ループバックだった場合は拒否されます。

---

この README はコードベースの主要機能・使い方をまとめた概要です。実運用にあたっては DataPlatform.md / StrategyModel.md 等の設計ドキュメント、及び各モジュール内の docstring を参照してください。必要であれば、導入用のサンプルスクリプトや CI 設定、requirements ファイルの追加もサポートします。