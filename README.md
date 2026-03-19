KabuSys — 日本株自動売買プラットフォーム
================================

概要
----
KabuSys は日本株向けのデータ取得・ETL・特徴量生成・シグナル生成・監査ログまでを含む
自動売買基盤のコアライブラリです。本リポジトリは以下のレイヤーを含むモジュール群を提供します。

- data: J-Quants からのデータ取得クライアント、DuckDB スキーマ/初期化、ETL パイプライン、RSS ニュース収集 等
- research: ファクター計算・特徴量探索ユーティリティ（モメンタム / ボラティリティ / バリュー 等）
- strategy: 特徴量の正規化・統合と売買シグナル生成ロジック
- execution: 発注関連（骨組み） — 将来的な発注実装のための層
- monitoring: 監視・Slack 通知など（設定参照）

設計方針の要点
- DuckDB をデータストアに使用（ローカルバイナリ DB）。
- ルックアヘッドバイアスを排除するため、target_date 時点のデータのみを参照する設計。
- J-Quants API 呼び出しはレート制御・リトライ・トークン自動更新を実装。
- DB 保存は冪等（ON CONFLICT / DO UPDATE）で安全な再実行が可能。

主な機能一覧
----------------
- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）/財務データ/市場カレンダーの取得（ページネーション対応）
  - レートリミット管理、リトライ、トークン自動更新
  - DuckDB への冪等保存ユーティリティ（save_* 系）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：市場カレンダー→株価→財務データ→品質チェックの一括実行
  - 差分更新、バックフィル対応

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 各レイヤーのテーブル定義・初期化 (init_schema)

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、前処理、記事保存、銘柄コード抽出
  - SSRF/サイズ上限/XML 攻撃対策（defusedxml, SSRF チェック等）

- 研究・ファクター計算（kabusys.research）
  - モメンタム / ボラティリティ / バリューファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー

- 特徴量生成（kabusys.strategy.feature_engineering）
  - research モジュールの生ファクターをマージしユニバースフィルタ、Z スコア正規化、features テーブルへ UPSERT

- シグナル生成（kabusys.strategy.signal_generator）
  - features + ai_scores を統合して final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存
  - Bear レジームで BUY を抑制、エグジット判定（ストップロス等）

セットアップ手順
-----------------

前提
- Python 3.10 以上（PEP 604 の Union 型 (|) や型注釈の利用のため）
- pip, virtualenv 推奨
- DuckDB を Python パッケージとして利用（pip でインストール）
- defusedxml（RSS パースの安全性向上）

例: 仮想環境の作成と依存のインストール
- 仮想環境作成（Unix/macOS）
  - python -m venv .venv
  - source .venv/bin/activate
- 依存インストール（最低限）
  - pip install duckdb defusedxml

（プロジェクト形態に応じて requirements.txt / pyproject.toml を用意している場合はそちらを使用してください）

環境変数（.env）
- パッケージは起動時にプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動読み込みします。
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（config.Settings で参照）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注層で使用）
- SLACK_BOT_TOKEN — Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知先）

任意/デフォルト設定
- KABUSYS_ENV（development|paper_trading|live、デフォルト: development）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD（1 で自動 env ロードを無効化）
- KABU_API_BASE_URL（kabu API の base URL、デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）

初期 DB 作成
- DuckDB スキーマを作成するには Python で次を実行します:

  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

使い方（例）
------------

1) DuckDB 初期化
- 必要なテーブルを作成して接続を取得:

  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

2) 日次 ETL の実行（J-Quants からデータ取得して保存）
- run_daily_etl を使うと市場カレンダー→株価→財務→品質チェックを順に実行します。

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

3) 特徴量の構築
- DuckDB 接続と target_date を渡して features テーブルを構築します。

  from kabusys.strategy import build_features
  from datetime import date
  count = build_features(conn, target_date=date.today())
  print(f"built features: {count}")

4) シグナル生成
- features / ai_scores / positions を参照して signals テーブルへ書き込みます。

  from kabusys.strategy import generate_signals
  from datetime import date
  total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total_signals}")

5) ニュース収集ジョブ
- RSS ソースからニュースを収集して raw_news / news_symbols へ保存します。

  from kabusys.data.news_collector import run_news_collection
  res = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  print(res)

6) カレンダー更新バッチ
- 夜間バッチとして calendar_update_job を呼ぶことで market_calendar を更新できます。

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

設定の注意点
- 環境変数が不足していると Settings のプロパティで ValueError が送出されます（必須項目の事前確認を推奨）。
- get_id_token は refresh token を使って idToken を取得し、J-Quants API 呼び出しで自動リフレッシュが行われます。
- ETL / API 呼び出しはネットワーク/認証エラーが起こり得るため、運用側でのリトライ・アラート設定を検討してください。

ディレクトリ構成（主要ファイル）
--------------------------------
以下はパッケージ内の主要ソースファイルです（抜粋）。

src/kabusys/
- __init__.py
- config.py                — 環境変数と設定管理
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得/保存）
  - news_collector.py      — RSS ニュース収集・前処理・DB 保存
  - schema.py              — DuckDB スキーマ定義・初期化
  - stats.py               — Z スコア等の統計ユーティリティ
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - features.py            — data.stats の公開ラッパ
  - calendar_management.py — 市場カレンダー管理・ユーティリティ
  - audit.py               — 監査ログ用スキーマ定義
- research/
  - __init__.py
  - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン/IC/統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — features テーブル構築
  - signal_generator.py    — シグナル生成ロジック
- execution/
  - __init__.py
- monitoring/
  - (監視・通知関連の実装を追加予定)

ローカルでの開発ヒント
- .env.example を用意し、必要な環境変数を設定する（JQUANTS_REFRESH_TOKEN 等）。
- テスト目的で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- DuckDB のインメモリモード(":memory:") を使うと一時的な実行・テストに便利です。
- logging レベルは LOG_LEVEL で制御できます（DEBUG 推奨で詳細ログを観察）。

貢献・拡張
---------
- execution 層のブローカー固有アダプター（kabuステーション実装）や、リスク管理モジュールの追加が想定されます。
- AI スコア連携や強化学習ベースのポジション最適化などは ai_scores の生成部分を拡張して統合してください。
- テスト・CI の整備（ユニット/統合テスト）を推奨します。ETL/HTTP 部分は外部 API をモックしてテスト可能です。

ライセンス
----------
（本リポジトリのライセンス情報をここに記載してください）

問題・問い合わせ
-----------------
使い方やバグ報告、仕様提案は Issue を作成してください。README に記載されていない想定使い方があれば説明を追加します。

以上。必要なら「.env.example」のサンプルや具体的な CLI スクリプト例、より詳細な DB テーブル一覧を追記します。