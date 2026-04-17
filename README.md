README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要機能を含みます。
- 発注・実行エンジン（ExecutionEngine） — 本番/ペーパートレード対応
- 監視コンポーネント（System / Trade / Risk Monitor）とアラート／Kill Switch
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ決定）
- 研究用ファクター計算・特徴量解析（DuckDB を用いた処理）
- ニュースNLP / レジーム判定（OpenAI を利用したセンチメント評価）
- 各種ユーティリティ（環境設定ウィザード・設定検証・レポート生成）

主な設計方針
- 本番 DB とペーパートレード DB を分離（PAPER_TRADING_SQLITE_PATH）
- ルックアヘッドバイアスを避ける設計（date.today() 等の直接参照回避）
- フェイルセーフ志向（API失敗時のフォールバック、部分書き込みで既存データ保護）
- 単体関数化・副作用最小化（研究関数・ポートフォリオ関数は純粋関数）

機能一覧
--------
- 環境セットアップウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config [--strict]
- ExecutionEngine 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db を利用
- Monitoring 起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]
- ニュースセンチメント評価（ai.news_nlp.score_news）および市場レジーム判定（ai.regime_detector.score_regime）
- ポートフォリオ構築ユーティリティ（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）
- 監視データの永続化（SQLite）とロギング／リスクイベント管理
- プロセス優先度設定・CPU affinity ユーティリティ（psutil ベース）

セットアップ手順
----------------
1. ソース取得
   - Git からクローンする、またはソースを配置してください。

2. Python 環境準備（例）
   - Python 3.9+ を想定
   - 仮想環境作成:
     python -m venv .venv
     source .venv/bin/activate
   - 必要パッケージをインストール（プロジェクトに requirements.txt がある想定）:
     pip install duckdb psutil openai requests
   - 追加（任意）:
     pip install PyYAML  # config/*.yaml の構文チェックに使用

3. .env 設定
   - ウィザードで対話的に作成:
     python -m kabusys.config_setup
   - または手動で .env をプロジェクトルートに作成
   - 重要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (paper_trading 時の約定挙動: instant | partial | never | reject; デフォルト instant)
     - OPENAI_API_KEY (ニュースNLP / レジーム判定で必要)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID （アラート送信に必要）
     - LOG_LEVEL（DEBUG/INFO/...）
   - 自動ロード:
     プロジェクトルートに .env/.env.local があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

4. 設定検証
   - 生成した .env と config/*.yaml の存在/整合性をチェック:
     python -m kabusys.validate_config
   - 警告も失敗扱いにする:
     python -m kabusys.validate_config --strict

使い方（代表的コマンド）
-----------------------
- 環境設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動（デーモン等で実行）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定してペーパートレード用 DB を使う:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  停止方法:
  - Kill Switch（監視が条件を満たした場合）により data/kill.flag が書き込まれ ExecutionEngine に停止指示が出ます。
  - 手動で監視停止フラグを使うにはプロジェクトルート/data/stop_requested.flag を作成すると起動中のループが検知して終了します。

- Monitoring 起動
  python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI (ニュース / レジーム)
  - OpenAI API キーを設定した状態で関数を呼び出します。
  - 例: ai.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date を与えて使用します。
  - OPENAI_API_KEY 未設定時は例外が発生します。

設定・ファイル関連の挙動
-----------------------
- DB
  - 監視用 SQLite: settings.sqlite_path（デフォルト data/monitoring.db）
  - ペーパートレード SQLite: settings.paper_sqlite_path（デフォルト data/paper_trading.db）
  - DuckDB（分析用）: settings.duckdb_path（デフォルト data/kabusys.duckdb）
  - init_monitoring_db() により監視用テーブルの作成・簡易マイグレーションを行います（冪等）。

- Kill / Stop フラグ
  - data/kill.flag: Kill Switch が書き込むファイル。存在すると ExecutionEngine は停止を受けます（Settings.kill_flag_path）。
  - data/stop_requested.flag: run_execution/run_monitoring のループ停止トリガー（手動停止用）。

- PID ファイル
  - 実行エンジンは data/execution.pid に PID を書きます（既存の PID が生きていない場合は stale と見做し削除されます）。

- ログ / アラート
  - AlertManager は LINE Messaging API を使って通知（token と user_id が設定されている場合）。同一カテゴリ・レベルの通知はクールダウン（デフォルト 30 分）で抑制されます。

依存関係（主なもの）
-------------------
- duckdb — 分析クエリ / research / ai の DuckDB 接続
- psutil — プロセス・CPU・メモリ・ディスク使用率取得 / プロセス優先度設定
- openai — ニュース NLP / レジーム判定の LLM 呼び出し
- requests — LINE API 呼び出し
- PyYAML（任意） — validate_config が config/*.yaml のパース検証を行う場合に必要

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 起動前設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — Monitoring ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py
- others...
- config/                      — 設定 YAML（system_config.yaml 等）を想定（リポジトリ外または生成）

注意点 / 運用メモ
-----------------
- 本番環境（KABUSYS_ENV=live）では特に kill.flag の取り扱い、LINE の通知設定、KILL_FLAG_CLEAR_ON_START の設定に注意してください（validate_config がライブ用の追加チェックを行います）。
- .env は機密情報を含むため Git にコミットしないでください（config_setup で生成される .env のヘッダにも同旨の注意書きがあります）。
- OpenAI API を利用する機能は API 利用料が発生します。利用の際はキー管理とコストに注意してください。
- run_monitoring は Monitoring 用に本番 sqlite_path を使用します（環境に関わらず監視は本番 DB を参照する設計です）。

貢献・拡張
-----------
- config/*.yaml の雛形生成スクリプトや requirements.txt を整備すると初回セットアップが容易になります。
- BrokerClient や ExecutionEngine の拡張、ログ出力の整備、単体テストの追加を歓迎します。

ライセンス
---------
（ここにライセンス情報を記載してください）

問い合わせ
----------
実装方針・利用上の不明点は実装者にお問い合わせください。README に含める連絡先やドキュメント参照先があれば追記してください。