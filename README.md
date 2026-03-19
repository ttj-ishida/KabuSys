# KabuSys

日本株向け自動売買基盤ライブラリ。データ収集（J-Quants）、ETL、特徴量作成、シグナル生成、ニュース収集、監査スキーマなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築を目的とした Python モジュール群です。J-Quants API から市場データや財務データ、マーケットカレンダーを取得して DuckDB に保存し、研究（research）で得られた生ファクターを用いた特徴量作成、戦略シグナル生成、ニュース収集・紐付け、監査ログ用スキーマなどを提供します。

設計上のポイント:
- DuckDB を中心としたローカル DB レイヤ構成（Raw / Processed / Feature / Execution）
- 冪等的なデータ保存（ON CONFLICT / INSERT ... DO UPDATE 等）
- ルックアヘッドバイアス回避（target_date 時点のデータのみを使用）
- API レートリミット遵守・自動リトライ・トークンリフレッシュ
- セキュリティ考慮（RSS 向け SSRF 対策、defusedxml の使用等）

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants から株価日足、財務データ、マーケットカレンダーを取得（jquants_client）
  - raw データを DuckDB に冪等保存（save_* 関数）
- ETL パイプライン
  - 差分取得・バックフィル対応の日次 ETL（data.pipeline.run_daily_etl）
  - 市場カレンダー更新ジョブ（data.calendar_management.calendar_update_job）
- データスキーマ
  - DuckDB の完全なスキーマ初期化（data.schema.init_schema）
- ニュース収集
  - RSS フィード収集とテキスト前処理、記事->銘柄紐付け（data.news_collector）
  - SSRF / サイズ制限 / 重複排除 等の堅牢な実装
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算・IC 計算・統計サマリー（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats）
- 戦略
  - 特徴量作成（strategy.feature_engineering.build_features）
  - シグナル生成（strategy.signal_generator.generate_signals）
- 監査ログ
  - signal / order / execution の監査スキーマ（data.audit）

---

## 必要条件 / 依存関係

最低限の依存（抜粋）:
- Python 3.9+ 推奨
- duckdb
- defusedxml

インストール例:
pip install duckdb defusedxml

（実運用では開発用の pyproject.toml / requirements.txt を参照して下さい）

---

## 環境変数（設定）

設定は環境変数、またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可）。必須の主要環境変数:

- JQUANTS_REFRESH_TOKEN  # J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      # kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN        # Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       # Slack 通知先チャンネル ID（必須）

任意 / デフォルト:
- KABUSYS_ENV            (development | paper_trading | live) デフォルト: development
- LOG_LEVEL              (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO
- DUCKDB_PATH            DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            監視用 SQLite パス（デフォルト: data/monitoring.db）

.env の例（.env.example を参照して作成）:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development

---

## セットアップ手順

1. リポジトリをクローン／プロジェクトを配置
2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate
3. 依存パッケージをインストール
   pip install duckdb defusedxml
   （プロジェクトに requirements / pyproject があればそれに従う）
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境に直接設定
5. DuckDB スキーマ初期化（Python REPL またはスクリプト）
   >>> from kabusys.data.schema import init_schema, get_connection
   >>> conn = init_schema("data/kabusys.duckdb")
   >>> conn.close()

注意:
- 自動で .env を読み込む際、OS 環境変数が優先され `.env.local` は `.env` より優先して上書きします。
- テスト時などで自動読み込みを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡易例）

以下は代表的なワークフローのサンプルコード（Python）です。

- スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量作成（features テーブル作成）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")

- シグナル生成（signals テーブルへの挿入）
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")

- ニュース収集ジョブ
  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  print(results)

運用のヒント:
- ETL はカレンダーを先に更新し、営業日に調整してから価格・財務を取得します（pipeline.run_daily_etl）。
- generate_signals は ai_scores テーブルや positions テーブルの状態を参照し、BUY/SELL を判定します。
- すべての DB 書き込みは日付単位で置換（Delete -> Insert）されているため冪等性が高いです。

---

## ディレクトリ構成（主なファイル）

プロジェクト内の主要モジュール一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API クライアント（取得 / 保存）
    - news_collector.py       # RSS ニュース収集・保存・銘柄抽出
    - schema.py               # DuckDB スキーマ定義・初期化
    - stats.py                # 統計ユーティリティ（zscore_normalize）
    - pipeline.py             # ETL パイプライン（run_daily_etl 等）
    - features.py             # data の公開インターフェース（zscore 再エクスポート）
    - calendar_management.py  # マーケットカレンダー管理
    - audit.py                # 監査ログスキーマ
    - quality.py?             # （品質チェックモジュール参照箇所あり ※実装ファイルがある前提）
  - research/
    - __init__.py
    - factor_research.py      # ファクター計算（momentum/volatility/value）
    - feature_exploration.py  # 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py  # features 作成（build_features）
    - signal_generator.py     # generate_signals（BUY/SELL 生成）
  - execution/
    - __init__.py             # 発注層は別途実装（placeholder）
  - monitoring/               # パッケージ公開名に含まれるが実装はここに（または未実装）
  - その他ドキュメントや補助スクリプト

（実際のリポジトリツリーはプロジェクトルートのファイルを参照してください）

---

## 注意事項 / 運用上の留意点

- 本パッケージは取引ロジックと発注 API の層を分離しており、戦略モジュールは直接注文送信を行わない設計です。実際の注文送信は execution 層やブローカーラッパーで実装してください。
- J-Quants API 利用にあたっては利用規約・レート制限を遵守してください。本実装では 120 req/min を想定した固定間隔レートリミッタを実装しています。
- データ品質チェック（quality モジュール）により欠損や異常が検出されても ETL は継続します。検出結果に基づく運用判断は呼び出し側で行ってください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動読み込みを無効化できます。

---

## 貢献 / ライセンス

貢献や Issue、Pull Request は歓迎します。実運用へ導入する際は十分なレビューとバックテストを行い自己責任で運用してください。ライセンス情報はリポジトリルートの LICENSE を参照してください。

---

何か追加で README に入れたい具体的なコマンド例や CI / デプロイ手順などがあれば教えてください。README をさらに運用向けに拡張します。