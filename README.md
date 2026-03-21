# KabuSys

バージョン: 0.1.0

日本株の自動売買プラットフォーム用ライブラリ群（データ収集・ETL・特徴量生成・シグナル生成・監視/監査補助）です。DuckDB をデータ層に使用し、J-Quants API など外部データソースからの取得・品質検査・戦略向け特徴量作成・シグナル生成までの基本機能を提供します。

---

## 概要

KabuSys は以下のレイヤーを意識した設計になっています。

- Raw Layer: API から取得した生データ（株価、財務、ニュース等）
- Processed Layer: 整形済み市場データ（prices_daily 等）
- Feature Layer: 戦略/AI 用特徴量（features / ai_scores）
- Execution Layer: シグナル・発注・約定・ポジションの記録（signals / orders / trades 等）

主な目的は「データの堅牢な収集と前処理」「ルックアヘッドバイアスを防いだ特徴量/シグナル生成」「発注/監査に必要なテーブル設計の提供」です。

---

## 機能一覧

主な実装済み機能（モジュール名を併記）:

- 環境設定読み込み・管理（kabusys.config）
  - .env / .env.local を自動読み込み（無効化可）
  - 必須環境変数チェック
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レート制御・リトライ・トークン自動リフレッシュ対応
  - 株価・財務・マーケットカレンダー取得 + DuckDB への冪等保存
- ETL パイプライン（kabusys.data.pipeline）
  - 日次差分 ETL（market calendar → prices → financials）
  - 品質チェック呼び出しフック（quality モジュール連携）
- RSS ニュース収集（kabusys.data.news_collector）
  - URL 正規化、SSRF対策、gzip/サイズ制限、重複排除、記事→銘柄紐付け
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev_trading_day / calendar 更新ジョブ
- 統計ユーティリティ（kabusys.data.stats）
  - クロスセクション Z スコア正規化
- 研究用ファクター計算（kabusys.research）
  - momentum / volatility / value ファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー
- 特徴量作成（kabusys.strategy.feature_engineering）
  - research の生ファクターを正規化・フィルタし features テーブルへ保存
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成
  - Bear レジーム抑制、エグジット条件（ストップロス等）実装
- 監査ログ設計（kabusys.data.audit）
  - シグナル→発注→約定のトレース用テーブル（監査用 DDL）

---

## セットアップ手順

1. リポジトリをクローン（あるいはパッケージを取り込み）

   git clone <repo-url>
   cd <repo-dir>

2. Python 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール

   pip install duckdb defusedxml

   ※ 実行環境や追加機能により他パッケージが必要になる場合があります（例: requests 等）。プロジェクトの requirements.txt がある場合はそれを利用してください。

4. パッケージのインストール（開発時）

   pip install -e .

5. 環境変数（.env）を準備

   プロジェクトルートに `.env` や `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack Bot トークン
   - SLACK_CHANNEL_ID: 通知用 Slack チャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: モニタリング用 SQLite パス（デフォルト data/monitoring.db）

---

## 使い方（基本例）

以下は典型的なワークフローの Python スニペット例です。実行は仮想環境内で行ってください。

- DuckDB スキーマ初期化

  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)

- 日次 ETL を実行（J-Quants トークンは settings から自動取得）

  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)
  print(result.to_dict())

- 特徴量を構築（戦略層）

  from kabusys.strategy import build_features
  from datetime import date

  cnt = build_features(conn, target_date=date(2025, 1, 1))
  print(f"features upserted: {cnt}")

- シグナル生成

  from kabusys.strategy import generate_signals
  from datetime import date

  total_signals = generate_signals(conn, target_date=date(2025, 1, 1))
  print(f"signals written: {total_signals}")

- RSS ニュース収集（news → raw_news、news_symbols）

  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", ...}  # 既知銘柄コードセット
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # sourceごとの保存件数

- カレンダー更新ジョブ（夜間バッチ想定）

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

注意点:
- settings のプロパティは必須 env が未設定の場合 ValueError を投げます。
- ETL・API 呼び出しはネットワークと API トークンが必要です。
- DuckDB ファイルへ書き込むためのディレクトリ権限を確認してください。

---

## 主要 API / コマンド一覧（抜粋）

- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date, threshold=0.6, weights=None)
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.calendar_management.calendar_update_job(conn, lookahead_days=90)

各関数はドキュメンテーション文字列および型アノテーションを備えているため、IDE の補完や help() で詳細を確認できます。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              # J-Quants API クライアント + 保存ロジック
    - news_collector.py              # RSS ニュース収集・保存
    - pipeline.py                    # ETL パイプライン（run_daily_etl 等）
    - schema.py                      # DuckDB スキーマ定義 / init_schema
    - stats.py                       # 統計ユーティリティ（zscore_normalize）
    - calendar_management.py         # カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                       # 監査ログ用 DDL
    - features.py                    # 再エクスポート（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py             # momentum/volatility/value 等ファクター計算
    - feature_exploration.py         # forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py         # features テーブル構築
    - signal_generator.py            # final_score 計算 & signals 生成
  - execution/                        # 発注/Execution 層（未詳述ファイル群）
  - monitoring/                       # モニタリング関連（未詳述ファイル群）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト development)
- LOG_LEVEL (DEBUG/INFO/...、デフォルト INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動読み込みを無効化できます（テスト用途）。

---

## トラブルシューティング

- ValueError: 環境変数が未設定
  - settings.* のプロパティは必須 env をチェックします。.env を作成し必要キーを設定してください。

- DuckDB の書き込みエラー
  - 指定した DUCKDB_PATH の親ディレクトリが存在するか・書き込み権限を確認してください。init_schema は親ディレクトリを自動作成しますが、OS 権限で失敗することがあります。

- API エラー・レートリミット
  - J-Quants クライアントは 120 req/min を想定しており、内部でレート制御とリトライを実装しています。429 や 5xx が大量に出る場合はリクエスト頻度を下げてください。

---

## 開発 / テストのヒント

- 自動で .env を読み込む実装があるため、CI や単体テストで環境操作を制御したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- network IO（API / RSS）を伴う関数は外部呼び出しをモックしてユニットテストを書くと良いです。例: jquants_client._request / news_collector._urlopen をモック。
- DuckDB の :memory: を使えばインメモリでスキーマ初期化・単体テストが可能です:
  conn = init_schema(":memory:")

---

この README はコードベースの主要機能を簡潔にまとめたものです。詳細な設計仕様（StrategyModel.md, DataPlatform.md 等）や運用手順は別途ドキュメントを参照してください。必要があれば README に含めるサンプルや運用フロー（cron / systemd / Docker）の例も作成します。