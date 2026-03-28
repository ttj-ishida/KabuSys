# KabuSys — 日本株自動売買プラットフォーム（README）

概要
---
KabuSys は日本株のデータ取得・品質管理・ファクター研究・ニュースNLP・市場レジーム判定・監査ログなど、量的投資および自動売買システムの基盤機能を集めた Python モジュール群です。  
主に DuckDB をデータストアに使用し、J-Quants API / RSS / OpenAI（LLM）等と連携して、ETL、品質チェック、ファクター計算、AI スコアリング、監査ログの初期化・運用を行うことができます。

主な特徴 / 機能一覧
---
- 環境設定
  - .env / .env.local および OS 環境変数から自動的に読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
  - 必須環境変数のチェック（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
- データ ETL / Data Platform
  - J-Quants API からの差分取得（株価日足、財務、上場情報、JPX カレンダー）。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）。
  - 日次 ETL パイプライン（run_daily_etl）を提供。
  - データ品質チェック（欠損、重複、スパイク、日付不整合）。
- ニュース収集 / NLP
  - RSS フィードの安全な収集（SSRF や XML 攻撃対策、トラッキングパラメータ除去）。
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント集計（score_news）。
  - マクロニュースと ETF MA を融合した市場レジーム判定（score_regime）。
- 研究ツール
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）。
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ。
  - Z スコア正規化ユーティリティ。
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等を持つ監査スキーマの初期化（init_audit_schema / init_audit_db）。
  - UUID を用いたトレーサビリティ設計。
- API クライアント
  - J-Quants API クライアント（レート制御、トークン自動リフレッシュ、リトライ、ページネーション対応）。
  - OpenAI クライアントを使用する箇所は API キーを引数で注入可能（テスト容易性を確保）。

セットアップ手順
---
前提
- Python 3.10+（型注釈に union 型等を使用）
- システムにネットワークアクセス（J-Quants, RSS, OpenAI）できること

1. 仮想環境を作成・アクティベート（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - その他プロジェクト固有の依存は pyproject.toml / requirements.txt を参照してインストールしてください（プロジェクト配布時の手順に従ってください）。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くことで自動読み込みされます（.env.local は上書き）。
   - 必須（例）
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...  （news_nlp / regime_detector 用。API キーは関数引数で上書き可）
   - 任意
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
   - 自動読み込みを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース初期化（監査DB 等）
   - 監査用 DB を作成してスキーマを初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

使い方（主要な利用シナリオ）
---
1) 日次 ETL 実行（データ取得 → 品質チェック）
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.config import settings
  - from kabusys.data.pipeline import run_daily_etl
  - conn = duckdb.connect(str(settings.duckdb_path))
  - result = run_daily_etl(conn)  # 戻り値は ETLResult
  - print(result.to_dict())

2) ニュースセンチメントスコア（銘柄別）
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n_written = score_news(conn, date(2026, 3, 20))  # 前日15:00 JST〜当日08:30 JST の記事を対象

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュース）
- 例:
  - from datetime import date
  - import duckdb
  - from kabusys.ai.regime_detector import score_regime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_regime(conn, date(2026, 3, 20))

  Note: OpenAI キーを関数引数で渡すことも可能（api_key="..."）。

4) 監査スキーマ初期化（既存接続へ）
- 例:
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

5) 研究用ファクター計算例
- 例:
  - from datetime import date
  - from kabusys.research.factor_research import calc_momentum
  - conn = duckdb.connect("data/kabusys.duckdb")
  - records = calc_momentum(conn, date(2026, 3, 20))

設定・環境変数（主要）
---
必須（動作に必須の値）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD — kabu API パスワード（注文連携で必要）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知機能を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID

OpenAI
- OPENAI_API_KEY — LLM を使う処理（news_nlp, regime_detector）で参照される。関数へ明示的に渡すことも可能。

その他
- KABUSYS_ENV — development / paper_trading / live（既定: development）
- LOG_LEVEL — ログレベル（既定: INFO）
- DUCKDB_PATH / SQLITE_PATH — データベースファイルパス

注意事項 / ベストプラクティス
---
- Look-ahead bias 対策: モジュール設計で datetime.today() 等を不必要に参照しないよう配慮されています。ETL やスコアリング関数は target_date を明示して呼び出してください。
- OpenAI / J-Quants の呼び出しはリトライおよびバックオフを行いますが、API 料金やレート制限に注意してください。
- RSS の収集では SSRF / XML ボム対策（ホワイトリスト的検査、defusedxml、最大読み込みサイズ等）を導入しています。外部フィードの追加時は信頼性を確認してください。
- DuckDB の executemany に空リストを渡せないバージョンの考慮がコードに入っています。DuckDB のバージョン依存に注意してください。

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py — パッケージ初期化、バージョン定義
- config.py — 環境変数/設定管理（.env 自動ロード、Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL パイプライン（run_daily_etl 他）
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（check_missing_data 等）
  - audit.py — 監査スキーマ初期化（init_audit_schema / init_audit_db）
  - news_collector.py — RSS 取得・前処理
- research/
  - __init__.py
  - factor_research.py — ファクター計算（momentum/value/volatility）
  - feature_exploration.py — 将来リターン / IC / サマリー等
- research/* / ai/* の他に strategy/, execution/, monitoring/ を想定（パッケージ __all__ に含むが実装はこのリポジトリの範囲に依存）

開発・テスト
---
- 自動環境変数ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト環境で .env の自動ロードを避けたい場合に有用）。
- OpenAI / ネットワークリクエストを含むモジュールは、外部呼び出しをモックしてユニットテストを実行してください（コード中にテスト用に差し替え可能な内部呼び出しポイントを設けています）。

ライセンス・貢献
---
本 README はコードベースの説明を目的としています。実際のライセンス・貢献フロー（CONTRIBUTING.md / LICENSE）はリポジトリのルートを参照してください。

補足（問い合わせ先）
---
不明点や追加のドキュメント要望（例: strategy 層の実装例、デプロイ手順、監視/アラート設計など）があれば教えてください。README を拡張してサンプルワークフローや運用ガイドを追加します。