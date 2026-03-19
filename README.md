# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（リサーチ / データプラットフォーム / 戦略 / 発注基盤の一部実装）。

このリポジトリは、J-Quants 等の外部データソースからデータを取得して DuckDB に保存し、
特徴量計算・シグナル生成までを行えるモジュール群を提供します。
実取引インターフェースやブローカー連携は execution 層に実装する想定です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（代表的なユースケース）
- 環境変数（設定項目）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下のレイヤーに分かれた構成を想定したライブラリです。

- Data Platform（data/）
  - J-Quants からの株価・財務・マーケットカレンダー取得（jquants_client）
  - RSS ニュース収集（news_collector）
  - DuckDB スキーマ定義と初期化（schema）
  - ETL パイプライン（pipeline）
  - カレンダー管理（calendar_management）
  - 各種ユーティリティ（stats, features, audit 等）
- Research（research/）
  - ファクター計算（momentum / volatility / value）（factor_research）
  - ファクター探索・IC・将来リターン計算（feature_exploration）
- Strategy（strategy/）
  - 特徴量エンジニアリング（feature_engineering）
  - シグナル生成（signal_generator）
- Execution（execution/）
  - 発注周りのインターフェースを想定するパッケージ（現状はモジュール格納用）
- Monitoring（monitoring/）
  - 監視・通知等のためのモジュールを想定（README に記載の通り将来的に実装）

設計における重要点:
- DuckDB をストアとして使用（オンプレ・ローカル・クラウドでの利用を想定）
- 冪等性（ON CONFLICT / トランザクションを多用）
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- API レートリミット・リトライや SSRF 対策などの実装留意

---

## 主な機能一覧

- 環境設定読み込み
  - .env / .env.local 自動読み込み（プロジェクトルート判定）
  - 必須/オプション変数のラッパー（kabusys.config.settings）

- データ取得
  - J-Quants API クライアント（トークン自動更新、レート制限、リトライ）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーの取得
  - RSS ベースのニュース収集（トラッキングパラメータ除去、SSRF/サイズ対策）

- DB スキーマ管理
  - DuckDB 用のスキーマ定義・初期化（raw / processed / feature / execution 層）
  - 必要なインデックスも作成

- ETL パイプライン
  - 差分取得（最終取得日を基準）、バックフィル、品質チェックフック
  - 日次バッチ run_daily_etl による一括 ETL 実行

- ファクター計算・特徴量
  - momentum / volatility / value を計算
  - cross-sectional Z スコア正規化ユーティリティ

- シグナル生成
  - features と ai_scores を統合して final_score を算出
  - BUY / SELL シグナルの生成（Bear レジーム判定、ストップロス等）
  - signals テーブルへ日付単位で置換（冪等）

- ニュースと銘柄紐付け
  - RSS から raw_news を保存、記事ID は正規化URLのハッシュで冪等性保証
  - テキストから銘柄コード抽出して news_symbols に紐付け

- カレンダー管理
  - market_calendar を使った営業日判定・next/prev_trading_day などのユーティリティ
  - 夜間のカレンダー更新ジョブ（calendar_update_job）

- 監査ログ設計（audit）
  - signal → order_request → execution といったトレーサビリティ用のDDL（設計記述あり）

---

## セットアップ手順

前提: Python 3.9+（ソース上の型注釈から推定）。プロジェクトルートに pyproject.toml 等がある想定。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（最低限）
   - pip install duckdb defusedxml
   - （必要に応じてプロジェクトの extras / requirements を用意している場合はそちらを利用）

   参考: 本コードでは urllib / stdlib を多用しています。J-Quants との認証には追加ライブラリ不要です。

4. パッケージのインストール（開発モード）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置することで自動読み込みされます。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（主な設定項目）

kabusys.config.Settings で参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token() で ID トークン取得に使用。

- KABU_API_PASSWORD (必須)
  - kabuステーション等の発注 API 用パスワード（実装側で利用想定）。

- KABU_API_BASE_URL (任意)
  - kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン（monitoring / 通知モジュールで想定）。

- SLACK_CHANNEL_ID (必須)
  - 通知先チャンネル ID。

- DUCKDB_PATH (任意)
  - DuckDB ファイルの保存先。デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)
  - 監視用 SQLite 等のパス（デフォルト: data/monitoring.db）

- KABUSYS_ENV (任意)
  - 環境: development | paper_trading | live。デフォルト: development

- LOG_LEVEL (任意)
  - ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL。デフォルト: INFO

欠落している必須変数を参照すると ValueError が発生します（Settings._require の動作）。

---

## 使い方（代表的な例）

以下は Python REPL やバッチスクリプトからの利用例です。

- DuckDB スキーマの初期化
  - Python:
    >>> from kabusys.data.schema import init_schema
    >>> conn = init_schema("data/kabusys.duckdb")

- 日次 ETL の実行
  - Python:
    >>> from kabusys.data.schema import init_schema
    >>> from kabusys.data.pipeline import run_daily_etl
    >>> conn = init_schema("data/kabusys.duckdb")
    >>> result = run_daily_etl(conn)  # target_date を省略すると今日（内部で営業日に調整）
    >>> print(result.to_dict())

- 特徴量の構築（build_features）
  - Python:
    >>> from kabusys.data.schema import init_schema
    >>> from kabusys.strategy import build_features
    >>> from datetime import date
    >>> conn = init_schema("data/kabusys.duckdb")
    >>> count = build_features(conn, date(2024, 1, 15))
    >>> print(f"features upserted: {count}")

- シグナル生成（generate_signals）
  - Python:
    >>> from kabusys.strategy import generate_signals
    >>> from kabusys.data.schema import init_schema
    >>> from datetime import date
    >>> conn = init_schema("data/kabusys.duckdb")
    >>> total = generate_signals(conn, date(2024, 1, 15))
    >>> print(f"signals written: {total}")

- RSS ニュース収集
  - Python:
    >>> from kabusys.data.schema import init_schema
    >>> from kabusys.data.news_collector import run_news_collection
    >>> conn = init_schema("data/kabusys.duckdb")
    >>> known_codes = {"7203", "6758", "9984"}  # 有効な銘柄コードセット（例）
    >>> results = run_news_collection(conn, known_codes=known_codes)
    >>> print(results)

- カレンダー更新ジョブ
  - Python:
    >>> from kabusys.data.calendar_management import calendar_update_job
    >>> from kabusys.data.schema import init_schema
    >>> conn = init_schema("data/kabusys.duckdb")
    >>> saved = calendar_update_job(conn)
    >>> print(f"calendar saved: {saved}")

注:
- 各操作は DuckDB 接続を引数に取り、既にスキーマが初期化されていることを前提にする関数が多いです。初回は init_schema() を呼んでテーブルを作成してください。
- J-Quants へのリクエストはネットワーク・レート制限に依存します。認証トークンは settings.jquants_refresh_token を通じて供給されます。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリー（src/kabusys）内の主要ファイル一覧と簡単な説明です。

- src/kabusys/
  - __init__.py
    - パッケージのエクスポート定義（data, strategy, execution, monitoring）
  - config.py
    - 環境変数の自動読み込み（.env / .env.local）と Settings クラス
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、fetch/save/認証/リトライ/レート制御
    - news_collector.py
      - RSS 取得、前処理、raw_news / news_symbols への保存
    - schema.py
      - DuckDB スキーマ（DDL）定義と init_schema / get_connection
    - pipeline.py
      - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - features.py
      - data.stats.zscore_normalize の re-export
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - calendar_management.py
      - market_calendar 管理、営業日判定、calendar_update_job
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）の DDL（設計）
    - (そのほか quality 等の品質チェックモジュールが想定される)
  - research/
    - __init__.py
    - factor_research.py
      - momentum / volatility / value の計算ロジック（prices_daily / raw_financials 参照）
    - feature_exploration.py
      - 将来リターン計算、IC（Spearman）計算、統計サマリー等
  - strategy/
    - __init__.py
    - feature_engineering.py
      - research 側の raw factor を正規化して features テーブルへ保存
    - signal_generator.py
      - features と ai_scores を統合して BUY/SELL シグナルを生成し signals へ保存
  - execution/
    - __init__.py
    - （発注層の実装はここに置く想定）
  - monitoring/
    - （監視・通知用モジュールを置く想定）

（上記は実際のソースファイルに基づく抜粋です。詳細はソースをご参照ください。）

---

## 補足・注意事項

- 本リポジトリのコードは「ライブラリ/基盤部分」を実装しています。実際のブローカーへの接続やリスク管理ポリシー、資金管理、運用オペレーションは別途実装・評価が必要です。
- 本番環境（live）での利用前に paper_trading / development 環境で入念な検証を行ってください。
- 環境変数の自動読み込みはプロジェクトルートの検出 (.git または pyproject.toml) を行います。テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 利用時は API 利用規約・レート制限に従ってください。

---

必要であれば、README に含める CLI コマンド例や .env.example のテンプレート、よくあるトラブルシュート（トークン更新、DuckDB パス権限、ネットワークタイムアウト等）を追加して作成します。どの情報を追加しますか？