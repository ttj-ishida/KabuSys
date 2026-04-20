KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・リサーチ・監視ツール群（KabuSys）のコア実装です。  
本 README はコードベース（src/kabusys 以下）を参照して、導入・起動方法、主要機能、ディレクトリ構成を日本語でまとめたものです。

概要
---
KabuSys は以下の役割を持つモジュール群で構成されています。

- ExecutionEngine: 発注・注文管理・リスク管理を担うエンジン（本番 / ペーパートレード対応）
- Monitoring: システム状態・注文状態・リスク監視、Kill Switch（危険時の自動停止）
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、リスク調整
- Research: DuckDB を使ったファクター計算・特徴量探索
- AI: OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント、レジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定、プロセス優先度制御 等

主な特徴
---
- 実行環境切替: KABUSYS_ENV により development / paper_trading / live を切替可能
  - paper_trading モードでは MockBrokerClient を使用し、発注履歴は専用 DB（data/paper_trading.db）に分離
- 監視と自動停止:
  - SystemMonitor / TradeMonitor / RiskMonitor による定期監視
  - KillSwitch によるフラグファイル（data/kill.flag）書き込みで ExecutionEngine を安全停止
- DuckDB を利用したリサーチ処理（prices_daily / raw_financials 等を想定）
- OpenAI でニュースセンチメントを取得（バッチ・リトライ・バリデーション実装）
- 設定ウィザード（.env 生成）と検証 CLI を提供
- ログはコンソール + 日次ローテートファイルで統一的に管理

セットアップ手順
---
前提
- Python 3.9+（型ピンや一部ライブラリの機能に依存）
- 任意の仮想環境（venv / pipenv / poetry 等）を推奨

1. リポジトリをクローンしてワークディレクトリへ
   - git clone … && cd <repo>

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - ここに requirements.txt は含まれていませんが、少なくとも以下のパッケージが必要です:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml を検証する場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

4. 環境変数（.env）の作成
   - 対話式ウィザードで .env を作成できます:
     - python -m kabusys.config_setup
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - OpenAI を使う場合:
     - OPENAI_API_KEY を設定

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を指定すると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
---
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ロギング設定
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（起動・実行）
---
以下はメインのコマンド例です。プロセス優先度やログは標準で設定されます。

- 環境設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（注文実行エンジン）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録（完全分離）
    - 起動時に data/execution.pid に PID を書く、data/stop_requested.flag があれば起動しない
    - 停止は data/stop_requested.flag を作成することで行えます（run_execution は起動中に監視して停止）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使います（監視は本番 DB を対象）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルトを上書き）

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーを設定し、ライブラリ関数を利用します。サンプル:
    - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime; c=duckdb.connect('data/kabusys.duckdb'); print(score_news(c, datetime.date(2026,4,1), api_key='…'))"
  - 注意: APIキーと課金に関する管理は実運用で十分注意してください

停止と Kill Switch
---
- ExecutionEngine の停止トリガー:
  - KillSwitch はリスク検出時に data/kill.flag を書き込みます。ExecutionEngine は起動中に kill.flag をチェックして安全に停止します。
- 手動停止:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループは検出して終了します。

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を通して設定されます。
- デフォルト:
  - コンソール出力は stdout
  - ファイル出力は logs/<app_name>.log を日次ローテート（30日保持）
- LOG_LEVEL / LOG_DIR 環境変数で上書き可能

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込みと Settings クラスを提供
- config_setup.py
  - .env を対話式で生成・更新するウィザード
- validate_config.py
  - .env と config/*.yaml を起動前に検証する CLI
- run_execution.py
  - ExecutionEngine のエントリポイント（スレッドでエンジン実行、PID 管理、stop flag）
- run_monitoring.py
  - SystemMonitor をポーリングする監視スクリプト
- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py — 監視ログの永続化層（SQLite）
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py —（TradeMonitor 実装ファイルが同階層にある想定）
  - risk_monitor.py — ドローダウン・ポジション数監視
  - kill_switch.py — Kill Switch 実装
  - monitoring_engine.py — 複数 Monitor を束ねる
  - alert_manager.py —（アラート送信用の実装がある想定）
- execution/ (発注関連の実装群)
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など（起動ロジックは run_execution.py 参照）
- portfolio/
  - portfolio_builder.py — 候補選定・スコア順ソート
  - position_sizing.py — 株数決定・資金配分
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — モメンタム・バリュー・ボラティリティなど
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し・バッチ処理）
  - regime_detector.py — レジーム判定（ETF MA + マクロセンチメント）
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

注意事項・運用上のヒント
---
- KABUSYS_ENV=live（本番）では設定ミスが重大になり得ます。validate_config で入念にチェックしてください。
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください（config_setup.py の出力ヘッダでもその旨を明記しています）。
- OpenAI を使う処理は外部 API 呼び出し・コストが発生します。rate limit やエラー処理（コード内で実装済み）を理解した上で運用してください。
- DuckDB / SQLite のパスはデフォルトで data/ 以下を参照します。運用時は適切に場所を指定してください。
- Logging ディレクトリに書き込めない場合はファイルログが無効化されコンソールのみになります。権限とディレクトリの存在を確認してください。

サンプル .env（抜粋）
---
以下は最小限の例（実際の値はご自身のものに置き換えてください）:

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

最後に
---
この README は現状のコードベース（src/kabusys/*）を基に作成しています。実運用にあたっては config/*.yaml の内容、BrokerClient の実装、OrderEngine の詳細や取引所 API の挙動を十分に確認してください。追加の質問や特定モジュールの詳しいドキュメントが必要であれば、どの箇所を深掘りするか教えてください。