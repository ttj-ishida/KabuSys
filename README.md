# KabuSys

バージョン: 0.1.0

日本株向けの自動売買プラットフォーム（研究・データパイプライン・戦略・実行・監査を含む軽量ライブラリ群）。  
本リポジトリは DuckDB を中心としたローカルデータレイクを用い、J‑Quants API／RSS フィード等からデータを収集して特徴量を作成し、戦略シグナルを生成するためのユーティリティを提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみ使用）
- DuckDB を用いた冪等な保存（ON CONFLICT / トランザクション）
- API 呼び出しに対してレート制御・リトライ・トークン自動リフレッシュを実装
- ニュース収集における SSRF / XML Bomb / 大容量レスポンス対策

---

## 機能一覧

- データ収集・保存
  - J‑Quants からの株価日足・財務データ・市場カレンダー取得（jquants_client）
  - RSS フィードからのニュース収集（news_collector）
  - DuckDB スキーマ定義と初期化（data.schema）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）（data.pipeline）

- データ処理・特徴量
  - モメンタム / ボラティリティ / バリューなどのファクター計算（research.factor_research）
  - Z スコア正規化などの統計ユーティリティ（data.stats）
  - 特徴量の構築と features テーブルへの保存（strategy.feature_engineering）

- 戦略・シグナル生成
  - features / ai_scores を統合して final_score を計算、BUY/SELL シグナル生成（strategy.signal_generator）
  - ストップロス等のエグジット判定を含む冪等な signals 書き込み

- カレンダー管理・ユーティリティ
  - 営業日判定 / 前後営業日取得 / 期間内営業日取得（data.calendar_management）
  - 夜間カレンダー更新ジョブ（calendar_update_job）

- 実行・監査
  - signal / order / execution / positions 等の実行レイヤー用スキーマ（data.schema）
  - 監査ログ（signal_events / order_requests / executions 等）（data.audit）

---

## 必要条件（主な依存）

- Python 3.10+
- duckdb
- defusedxml

（プロジェクト上の他モジュールは標準ライブラリを多用する設計です。環境によって追加パッケージをインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate （Windows の場合は .venv\Scripts\activate）
3. パッケージと依存をインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （ローカル開発）pip install -e .

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みは既定で有効）。
   - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（ライブラリの一部機能で必須）:
- JQUANTS_REFRESH_TOKEN — J‑Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabu API のパスワード（execution 層利用時）
- SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルト:
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — DEBUG/INFO/...（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB など（default: data/monitoring.db）

例 (.env):
JQUANTS_REFRESH_TOKEN=eyJ...  
KABU_API_PASSWORD=your_kabu_password  
SLACK_BOT_TOKEN=xoxb-...  
SLACK_CHANNEL_ID=C01234567  
KABUSYS_ENV=development

---

## 使い方（クイックスタート）

以下は Python REPL / スクリプトからの基本的な実行例です。

1) DuckDB スキーマ初期化
- 初回はスキーマを作成して接続を取得します。
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL（株価・財務・カレンダー収集 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

3) 特徴量の構築（features テーブルの作成 / 更新）
  from datetime import date
  from kabusys.strategy import build_features
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")

4) シグナル生成（features + ai_scores → signals）
  from kabusys.strategy import generate_signals
  n = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {n}")

  - 重みをカスタムにしたい場合:
    weights = {"momentum": 0.5, "value": 0.2, "volatility": 0.15, "liquidity": 0.15, "news": 0.0}
    generate_signals(conn, date.today(), weights=weights)

5) ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # あらかじめ有効な銘柄コードを用意
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)

6) カレンダー夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

注意:
- すべての操作は冪等に設計されています（同一日付の上書きはトランザクションで行われます）。
- ETL / API 呼び出し時のトークンやネットワークエラーは内部でリトライされますが、最終的にエラーとなる場合は例外が投げられます。

---

## API（主な公開関数・用途）

- kabusys.config.settings
  - 環境変数を集約した Settings オブジェクト。settings.jquants_refresh_token 等で取得。

- data.schema
  - init_schema(db_path) → DuckDB 接続（テーブル作成）
  - get_connection(db_path)

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl → 日次 ETL の統合エントリポイント

- data.news_collector
  - fetch_rss(url, source) → RSS 取得（記事リスト）
  - save_raw_news(conn, articles) → raw_news へ保存
  - run_news_collection(conn, sources, known_codes)

- research.factor_research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)

- strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold, weights)

その他、calendar_management / audit / data.stats（zscore_normalize）など多数のユーティリティを提供しています。詳細は各モジュールの docstring を参照してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py — J‑Quants API クライアント（取得・保存）
  - news_collector.py — RSS ニュース収集
  - schema.py — DuckDB スキーマ定義と初期化
  - pipeline.py — ETL パイプライン（差分更新 / run_daily_etl 等）
  - calendar_management.py — 市場カレンダー管理
  - features.py — zscore_normalize の再エクスポート
  - stats.py — 統計ユーティリティ
  - audit.py — 監査ログ用スキーマ
- research/
  - __init__.py
  - factor_research.py — モメンタム/ボラティリティ/バリュー等の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — features 構築
  - signal_generator.py — final_score 計算と signals 生成
- execution/  （発注・実行関連の拡張用ディレクトリ）
- monitoring/  （監視・メトリクス関連の拡張用ディレクトリ）

---

## 開発・デバッグのヒント

- 自動 .env 読み込みを無効化したい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ログレベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/...）
- テスト用にメモリ DB を使う場合:
  conn = init_schema(":memory:")
- news_collector は外部ネットワークにアクセスするため、テスト時は _urlopen をモックできます。

---

## 注意事項・制約

- 本ライブラリは実運用での発注機能を完全に提供するものではありません。execution 層（証券会社 API のラッパー）やリスク管理は別途実装が必要です。
- KABUSYS_ENV によって動作モード（development / paper_trading / live）を切り替えます。live 実行時は特に十分なテストと安全対策を行ってください。
- DuckDB の外部キー制約や ON DELETE のサポート範囲はバージョンに依存します。スキーマ内の注意書きを参照してください。

---

この README はコードベースの概要、導入方法、代表的な使い方をまとめたものです。より詳細な仕様や設計資料（StrategyModel.md, DataPlatform.md 等）がプロジェクトに同梱されている想定ですので、各モジュールの docstring と併せて参照してください。