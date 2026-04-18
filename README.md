KabuSys — 日本株自動売買システム
=================================

このリポジトリは、日本株向けの自動売買・研究・監視を行う軽量フレームワーク（プロトタイプ）です。
主な機能は戦略の研究用ユーティリティ、ポートフォリオ構築、発注エンジン（本番 / ペーパートレード）、監視 / アラート、AI ベースのニュースセンチメント評価などです。

主な特徴
--------
- 戦略研究用モジュール
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）などの統計ユーティリティ
- ポートフォリオ構築
  - 候補選出、重み計算（等金額 / スコア加重）、単元株丸め、リスクベース配分
  - セクター上限適用、レジーム乗数
- 発注（Execution）
  - ExecutionEngine を起動してブローカーに発注を行う（KABUSYS_ENV によって MockBroker を利用可能）
  - paper_trading モードでは data/paper_trading.db に完全分離して記録
- 監視（Monitoring）
  - システムリソース・データ鮮度・注文ログ・リスク指標を定期的に記録・評価
  - Kill Switch（data/kill.flag）により条件で ExecutionEngine を停止
- AI モジュール
  - OpenAI を用いたニュースのセンチメント集約（gpt-4o-mini を想定）
  - 市場レジーム判定（ETF MA と LLM マクロセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成スクリプト 等

必須 / 主要ファイル・エントリポイント
------------------------------------
- 起動スクリプト
  - python -m kabusys.run_execution  — ExecutionEngine 起動
  - python -m kabusys.run_monitoring  — SystemMonitor ポーリングループ起動
- 設定関連
  - python -m kabusys.config_setup    — .env を対話式に作成 / 更新するウィザード
  - python -m kabusys.validate_config — 設定の静的検証 CLI
- ツール
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

セットアップ手順
----------------
1. リポジトリをクローンし、プロジェクトルートへ移動します。
   - この README はパッケージ配布前後でも動作するよう、コードは __file__ を基準にパスを解決します。

2. Python 仮想環境を作成して有効化します（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストールします（例）。
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限以下を入れてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML をパースする場合）
   - 開発時は pip install -e . でローカルインストールすると便利です。

4. 環境変数を用意します（.env を作成）。
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（例は下記参照）。
   - 自動ロード:
     - ランタイム開始時、プロジェクトルートに .env/.env.local があれば自動で読み込まれます。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（抜粋・デフォルト）
---------------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN  — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD      — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV            — development | paper_trading | live（デフォルト: development）
- DB パス
  - DUCKDB_PATH            — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH            — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- ログ関係
  - LOG_LEVEL              — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR                — ログ保存ディレクトリ（デフォルト: logs/）
- OpenAI
  - OPENAI_API_KEY         — LLM 利用時に必要
- その他
  - MONITOR_POLL_INTERVAL  — SystemMonitor のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH          — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH         — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1、デフォルト: 0)

簡単な .env 例
--------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

使い方（起動例）
----------------
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- 実行エンジン（発注）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、paper_trading 用 DB へ保存します（本番 DB と分離）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更できます（デフォルト 60 秒）。
  - 停止方法: プロジェクトルート/data/stop_requested.flag を作成すると、ループが次のサイクルで終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

停止 / Kill Switch
------------------
- ExecutionEngine の停止シグナル
  - KillSwitch は監視基準（ドローダウンやポジション上限）を満たすと data/kill.flag に理由を書き込みます。
  - ExecutionEngine は起動時にこのフラグを確認し、存在すれば起動を行いません。
  - kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）で指定されます。
  - Kill フラグは手動で削除するか、必要に応じて設定で自動クリアできます（KILL_FLAG_CLEAR_ON_START=1 は本番では危険なため注意）。

ログ
---
- 共通のログ設定ユーティリティは kabusys.utils.logging_setup.setup_logging を使用します。
- 出力先は標準出力（stdout）と日次ローテートするファイル（logs/<app_name>.log）です。
- ログレベルは引数 > 環境変数 LOG_LEVEL > デフォルト INFO の順に決定されます。

データベース
-----------
- DuckDB（分析用）: data/kabusys.duckdb（デフォルト）
- SQLite（監視用）: data/monitoring.db（デフォルト）
- Paper trading 用 SQLite（分離）: data/paper_trading.db（paper_trading モード）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 配下の主要モジュール・ファイルの抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロードと Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（テーブル作成・CRUD ラッパー）
    - system_monitor.py      — システム資源・データ鮮度監視
    - trade_monitor.py       — 注文ログ監視（※実装あり）
    - risk_monitor.py        — ドローダウン、ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       — （アラート送信管理：LINE 等）（※実装想定）
  - execution/               — 発注関連（Engine、OrderManager、BrokerFactory 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースの LLM センチメント評価
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py

注意事項 / 運用上のヒント
-----------------------
- 本番環境（KABUSYS_ENV=live）では kill.flag や PID ファイルの扱いに注意してください。validate_config の警告を必ず確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup でも注意喚起あり）。
- OpenAI 等の外部 API を用いるモジュールは API キー必須、API コールの失敗時はフェイルセーフ（0.0 フェールバックやスキップ）する設計です。ただし運用ではレートリミットやエラー対策を十分検討してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソールのみになります。

開発 / 貢献
-----------
- テスト: 各ユニットは副作用を避けるために DB への直接書き込みを最小化しています。duckdb/SQLite を使った統合テストや API 呼び出しのモック化を推奨します。
- 依存ライブラリのバージョン固定は requirements.txt / pyproject.toml を用意してください。

追加情報
--------
- より具体的な仕様（PortfolioConstruction.md、StrategyModel.md 等）はドキュメントとして別途管理する想定です（このコード内に設計コメントが多数含まれています）。

問題・質問があれば、使用しているモジュール名と実行コマンド、発生しているエラーメッセージを添えて報告してください。