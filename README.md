KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買・研究・監視ユーティリティ群を含む Python パッケージです。  
以下の README は、プロジェクト概要、主な機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめたものです。

プロジェクト概要
----------------
KabuSys は次の目的を持つモジュール群で構成されています。

- 自動売買エンジン（ExecutionEngine）とその周辺コンポーネント（注文管理、リスク管理、ブローカー抽象化）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（候補選定・配分・ポジションサイズ計算・セクター制限）
- 研究用ユーティリティ（ファクター計算、特徴量探索、IC 計算）
- AI を使ったニュースセンチメント評価・レジーム判定（OpenAI API を使用）
- 各種 CLI / ユーティリティ（.env ウィザード、設定検証、Paper Trading レポート等）
- ロギング・プロセス優先度・DB 初期化などの共通ユーティリティ

主な特徴
--------
- 環境分離:
  - KABUSYS_ENV により development / paper_trading / live を切り替え（paper_trading は専用 SQLite DB を使用）
- フェイルセーフ設計:
  - API 失敗やデータ欠損時は例外を吸収して安全にフォールバック（例: AI 呼び出しで 0.0 を返す等）
- 監視と Kill Switch:
  - 稼働状況・データ鮮度・ドローダウン等を監視し、閾値超過で data/kill.flag を書き込んで発注エンジンを停止可能
- DuckDB / SQLite を利用した分析と永続化
- OpenAI（gpt-4o-mini など）を使ったニュース NLP と市場レジーム判定（任意）
- ポートフォリオ構築は純粋関数ベースでテスト・再利用しやすい実装

セットアップ手順
----------------
前提:
- Python 3.10 以上を想定（typing の記法から）
- システムに duckdb, psutil, openai 等のライブラリが必要です（requirements.txt がある前提で pip install）。

例（開発環境）:
1. リポジトリをクローン / checkout
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合、少なくとも以下を入れてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証時に必要）
4. 初期設定 (.env) を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成してプロジェクトルートに置く
   - 自動ロード: .env / .env.local は Settings モジュール起動時に自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit(1)）
6. DB ディレクトリ等の準備
   - デフォルトで data/ 配下に DB を作成します。必要に応じて .env で DUCKDB_PATH / SQLITE_PATH を設定してください。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL（DEBUG/INFO/...）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔（秒）、デフォルト 60）

使い方（主要コマンド）
---------------------
- 実行エンジン（Execution）
  - 本番またはペーパートレードの発注セッションを起動します。
  - python -m kabusys.run_execution
  - 起動前に data/stop_requested.flag が存在すると起動をキャンセルします。
  - Execution は settings.is_paper に応じて paper_trading 用 DB を使用（本番 DB と分離）
  - Execution の PID は data/execution.pid（デフォルト）に書き出されます。

- 監視プロセス（Monitoring）
  - システム / 注文 / リスク のポーリングを行います。
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - run_monitoring は常に本番 sqlite_path を使用して監視ログを記録します（KABUSYS_ENV に依存しない）
  - 停止方法: プロジェクトルートの data/stop_requested.flag を作成するとループが終了します

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env の初期作成・更新を対話的に行えます

- 設定検証
  - python -m kabusys.validate_config
  - .env や config/*.yaml の基本チェックと警告表示

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - --from / --to で期間指定（YYYY-MM-DD）
  - 環境変数 PAPER_TRADING_SQLITE_PATH または --db で DB ファイルを指定可能

- AI 関連（プログラム経由で利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news を解析して ai_scores テーブルへ書き込み（OpenAI API が必要）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 とマクロニュースでレジーム判定を行い market_regime テーブルへ書き込む

停止 / Kill スイッチ
- KillSwitch はリスク閾値を満たした場合に data/kill.flag（デフォルト）を書き込み、ExecutionEngine に停止を要求します
- 手動で停止するには data/kill.flag を作成してください（Execution が定期的に確認します）
- 一時的に監視 / 実行ループを止めたい場合は data/stop_requested.flag を作成してください（run_* スクリプトはここを参照）

ログ
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" 等)
- デフォルトで stdout と logs/<app_name>.log（日次ローテーション、30日保持）に出力
- ログディレクトリは LOG_DIR 環境変数またはデフォルト "logs/"

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数の解決・バリデーション・デフォルト管理
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- utils/
  - logging_setup.py — ログ設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス存在の監視
  - trade_monitor.py — （注文監視: ファイル内実装あり）
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — kill.flag の生成・管理
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — （通知管理、LINE 等と連携する想定）
- execution/ (発注ロジック関連)
  - order_manager.py, order_repository.py, execution_engine.py, reconciler.py, risk_manager.py, broker_factory.py など
- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数計算・上限・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム / バリュー / ボラティリティ等の計算（DuckDB 利用）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- ai/
  - news_nlp.py — ニュースの LLM ベースセンチメント算出
  - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- data/ （ランタイム生成・動的ファイル）
  - monitoring DB / paper_trading DB / pid/flag ファイル等（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag）

注意事項 / 運用のヒント
----------------------
- .env は機密情報を含むため Git にコミットしないでください（config_setup でも強調されています）。
- 本番環境では KABUSYS_ENV=live とし、KILL_FLAG_CLEAR_ON_START は 0 を推奨します（誤って Kill Switch を消してしまうのを防止）。
- OpenAI API を利用する機能は API キーが必要です。API 呼び出しの失敗はフォールバックする実装ですが、頻繁に失敗する場合は運用上の確認が必要です。
- monitoring / execution はプロセス優先度を高く設定する処理を実行します（set_process_priority）。権限不足で警告が出る場合がありますが、処理は継続します。
- DuckDB を分析ストアとして利用します。大規模データを扱う場合は duckdb の最適化やファイル配置に注意してください。

サンプル実行フロー（簡易）
- 環境準備 → .env 作成
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config
- Paper Trading で発注エンジン起動（別プロセスで監視を併用推奨）
  - python -m kabusys.run_execution  (KABUSYS_ENV=paper_trading を .env に設定)
  - python -m kabusys.run_monitoring
- 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

さらに詳しい開発者向けドキュメント
--------------------------------
- 各モジュールの docstring に設計意図や使用上の注意が記載されています。特に portfolio/*、research/*、ai/*、monitoring/* に重要な実装ノートがあります。
- tests が存在する場合は pytest 等でユニットテストを実行して挙動を確認してください。

お問い合わせ / 貢献
------------------
- バグ報告や改善提案は Issue を立ててください。Pull Request は歓迎します。

以上が README の概要です。必要であれば、セットアップコマンドや .env のサンプル（.env.example 風）を追記します。どの情報をより詳しく書くか指定してください。