KabuSys — 日本株自動売買／データ基盤ライブラリ
====================================

概要
----
KabuSys は日本株向けの自動売買・データ基盤・リサーチ用ユーティリティ群を提供する Python パッケージです。  
主に以下の機能を含みます。

- J-Quants API を用いた株価／財務／マーケットカレンダーの ETL（差分取得・保存・品質チェック）
- ニュース収集（RSS）と LLM（OpenAI） を用いたニュースセンチメント解析（銘柄ごと）
- マーケットレジーム判定（ETF の MA とマクロニュースの LLM センチメントを合成）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ 等）と統計ユーティリティ
- 監査ログ（signal / order / execution）用の DuckDB スキーマ初期化・ユーティリティ
- 環境設定管理（.env ロード、必須環境変数チェック）

主な機能一覧
-------------
- data.jquants_client
  - J-Quants API から日足・財務・マーケットカレンダー・上場銘柄情報の取得、DuckDB への冪等保存
  - ページネーション、レート制御、401 自動リフレッシュ、リトライ実装
- data.pipeline / etl
  - run_daily_etl を含む差分 ETL（calendar / prices / financials）と品質チェックの実行
  - ETL 結果を表す ETLResult
- data.news_collector
  - RSS フィード収集・前処理・raw_news への冪等保存（SSRF 対策、サイズ制限、URL 正規化）
- ai.news_nlp, ai.regime_detector
  - gpt-4o-mini を用いたニュースの銘柄別センチメント付与（score_news）
  - ETF(1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを合成した市場レジーム判定（score_regime）
- research
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - feature_exploration（将来リターン計算、IC、統計サマリ、ランク化）
- data.quality
  - 欠損・スパイク・重複・日付不整合などの品質チェック
- data.audit
  - signal_events / order_requests / executions を含む監査スキーマの初期化ユーティリティ（init_audit_db / init_audit_schema）
- config
  - .env 自動ロード（プロジェクトルート基準）、必須環境変数チェック、設定ラッパー settings

動作前提（推奨）
----------------
- Python >= 3.10
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外はインストールしてください）

セットアップ手順
----------------

1. Python インタプリタの用意（推奨: 3.10+）
2. リポジトリをクローン・配置
3. 依存パッケージをインストール
   - 例:
     pip install duckdb openai defusedxml
   - 開発用・固定化する場合は requirements.txt / poetry / pip-tools を使って管理してください。
4. 環境変数（もしくは .env/.env.local）を設定
   - 自動でプロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env を読み込みます。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須の環境変数（主なもの）
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（data.jquants_client に必要）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必要に応じて）
     - SLACK_CHANNEL_ID      : Slack チャンネル ID（必要に応じて）
     - OPENAI_API_KEY        : OpenAI API キー（AI スコアリングを行う場合）
   - 任意・デフォルト
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
   - .env のパースは export プレフィックス、シングル/ダブルクォート、行内コメントの一部をサポートします。

例: .env（テンプレート）
-----------------------
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

基本的な使い方（コード例）
-------------------------

- DuckDB 接続準備（例: ファイル DB）
  from pathlib import Path
  import duckdb
  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 監査スキーマを初期化（監査ログ用 DB）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # または既存接続へスキーマを適用:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)

- 日次 ETL を実行
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント付与（OpenAI 必須）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} symbols")

- 市場レジーム判定（OpenAI 必須）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- リサーチ用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  m = calc_momentum(conn, date(2026,3,20))
  v = calc_value(conn, date(2026,3,20))

- 設定値取得例
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

注意点 / 設計上の要点
--------------------
- Look-ahead バイアス対策:
  - AI・研究・ETL 処理の多くは内部で datetime.today() を直接参照せず、target_date を明示的に受け取ります。バックテストでは過去時点のみのデータを使って評価することを想定しています。
- 冪等性:
  - J-Quants の保存処理・ニュース挿入・監査テーブルの初期化などは基本的に冪等（ON CONFLICT / INSERT ... DO UPDATE / INSERT ... ON CONFLICT DO NOTHING）を意識して実装されています。
- フォールバック動作:
  - market_calendar が未取得の場合は曜日ベース（土日休場）で営業日判定を行います。
  - OpenAI / 外部 API が失敗した場合はフェイルセーフ（ゼロスコアやスキップ）で処理が継続するよう設計されています。
- 環境変数自動読み込み:
  - パッケージ import 時にプロジェクトルートの .env / .env.local を読み込みます（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

ディレクトリ構成（主要ファイル）
----------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境設定/.env ロード
- ai/
  - __init__.py
  - news_nlp.py                 — ニュースセンチメント（score_news）
  - regime_detector.py          — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py           — J-Quants API クライアント & DuckDB 保存
  - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
  - etl.py                      — ETLResult 再エクスポート
  - news_collector.py           — RSS 収集
  - calendar_management.py      — 市場カレンダー管理（is_trading_day 等）
  - quality.py                  — データ品質チェック
  - stats.py                    — 統計ユーティリティ（zscore_normalize）
  - audit.py                    — 監査スキーマ初期化（init_audit_db 等）
- research/
  - __init__.py
  - factor_research.py          — ファクター計算
  - feature_exploration.py      — 将来リターン/IC/統計サマリ
- (その他: strategy, execution, monitoring などパッケージ公開名あり)

ロギング / 環境モード
--------------------
- 環境: KABUSYS_ENV は以下をサポートします:
  - development, paper_trading, live
- ログレベル: LOG_LEVEL 環境変数で指定（DEBUG/INFO/...）
- settings.is_live / is_paper / is_dev を参照し挙動を切替可能

開発・運用上のヒント
-------------------
- OpenAI API 呼び出しはコストとレイテンシが発生するため、バッチ実行・キャッシュ・適切なリトライ設定を検討してください。
- DuckDB ファイルはバックアップ・ローテーションを検討してください（特に監査 DB は削除しない前提）。
- J-Quants API のレート制御は内蔵されていますが、大量取得時は運用ルールを確認してください。

ライセンス・貢献
----------------
本 README はコードベースの説明に基づく概要です。パッケージのライセンスや貢献ポリシーはリポジトリのトップレベル（LICENSE / CONTRIBUTING.md 等）を参照してください。

---

必要であれば、README にサンプル .env.example、より詳細なクイックスタート（Docker Compose 例、cron ジョブ例、監視・Slack通知の設定方法）を追加します。どの情報を深掘りしますか？