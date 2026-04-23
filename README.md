# KabuSys

日本株自動売買システムの一部を切り出した実装リポジトリ（ライブラリ風構成）。  
この README はリポジトリ内のスクリプト／モジュールから抽出した情報に基づき、セットアップ・起動・主要機能を日本語でまとめたものです。

注意: 本リポジトリは実運用システムのコンポーネント群を含みます。実際に「live」環境で発注を行う前に、設定・アクセスキー・テストを十分に行ってください。

---

目次
- プロジェクト概要
- 機能一覧
- 動作要件（推奨）
- セットアップ手順
- 主要環境変数（要設定）
- 使い方（起動コマンド例）
- 重要な挙動メモ
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株を対象とした自動売買／リサーチ／監視のためのコンポーネント群です。
- 本コードベースには以下の役割のモジュールが含まれます:
  - Execution：発注エンジン（実運用 / ペーパートレード切替）
  - Monitoring：システム・発注・リスク監視（Kill Switch 等）
  - Portfolio：銘柄選定・重み算出・株数決定ロジック
  - Research：ファクター計算・特徴量探索（DuckDB を利用）
  - AI：ニュースセンチメント / レジーム判定のための LLM 呼び出し（OpenAI）
  - Utils：ログ設定、プロセス優先度設定などユーティリティ
  - Tools：ペーパートレード検証レポート生成等の補助スクリプト

機能一覧
- 環境設定ウィザード（.env の対話的作成）: kabusys.config_setup
- 設定検証 CLI（.env や config/*.yaml の基本チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）: run_execution.py
  - KABUSYS_ENV=paper_trading では MockBrokerClient を使用し paper_trading DB を使用
- SystemMonitor／MonitoringEngine による定期監視ループ: run_monitoring.py
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
  - Monitoring は環境に関係なく本番 sqlite_path を使用（監視用 DB に一元）
- RiskMonitor: ドローダウン監視、ポジション上限の監視・イベント記録
- KillSwitch: 条件で data/kill.flag を書き込み Execution を停止させる仕組み
- Portfolio モジュール: 候補選定、等配分／スコア配分、ポジションサイズ計算、セクター制限、レジーム乗数
- Research モジュール: momentum/value/volatility ファクターの DuckDB ベース計算、IC 計算等
- AI モジュール:
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini 等）で評価して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）MA 等と LLM 評価を合成して市場レジーム判定
- Tools:
  - paper_verification_report: ペーパートレード検証レポート生成（稼働率・注文成功率・レイテンシなど）

動作要件（推奨）
- Python 3.10 以上（ソースでの型注釈や構文を考慮）
- 必要な Python パッケージ（概略）
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（設定ファイル検証を行う場合に推奨）
- SQLite（標準ライブラリで使用）
- ネットワーク API（kabuステーション 等）を利用する場合は実ネットワーク接続と資格情報が必要

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン / 取得
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate（Windows）
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 実行環境に応じて追加パッケージが必要になる場合あり
4. 環境変数設定 (.env)
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）
5. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできる
6. DB ディレクトリ等の作成
   - logs/ や data/ はコードが自動で作成することもあるが、権限等により作成に失敗する場合あり
   - sqlite / duckdb のパスは .env または環境変数で指定

主要環境変数（抜粋）
- 必須（最低これらは設定してください）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト development）
    - paper_trading の場合、発注はモックで paper_trading.db に記録される
- DB / ログ
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト data/paper_trading.db)
  - LOG_LEVEL (DEBUG/INFO/...)
  - LOG_DIR
- AI
  - OPENAI_API_KEY (AI 機能を利用する場合必要)
- 実行制御
  - PID_FILE_PATH (実行プロセス PID 保存ファイル)
  - KILL_FLAG_PATH (KillSwitch が書き込むフラグ)
  - KILL_FLAG_CLEAR_ON_START (1 にすると起動時に kill flag を自動クリア)
- Monitoring
  - MONITOR_POLL_INTERVAL（秒） — run_monitoring のポーリング間隔（デフォルト 60）
  - PAPER_FILL_MODE（ペーパートレード時の fill 挙動）: instant|partial|never|reject

使い方（起動例）
- 環境構築が済んでいることを前提とします。

1) 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2) 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3) ExecutionEngine を起動（発注エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV を paper_trading にするとモックブローカーを使用:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

   挙動:
   - 起動時にプロセス優先度を "high" に設定（psutil を利用）。
   - paper_trading 環境では PAPER_TRADING_SQLITE_PATH に注文を記録して本番 DB と分離。
   - data/stop_requested.flag が存在する場合は起動を抑止または実行中に停止する。

4) Monitoring を起動（監視ループ）
   - python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で変更:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   挙動:
   - 監視用 DB（Settings.sqlite_path）に接続し監視テーブルを初期化
   - SystemMonitor.check_once() を定期実行しログ・DB 書き込み・KillSwitch 評価等を行う

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は data/paper_trading.db。--db オプションで指定可能。

6) AI 機能（ニューススコアリング / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY 環境変数、または関数引数で指定）
   - kabusys.ai.score_news（関数呼び出し）や kabusys.ai.regime_detector.score_regime を呼んで利用
   - 注意: LLM 呼び出しはエラー時にフォールバック処理を行うが、API コスト・レート制限に注意

重要な挙動メモ
- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env（および .env.local）を自動読み込みします。
  - OS 環境変数優先。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- Monitoring は環境変数 KABUSYS_ENV に依らず常に Settings.sqlite_path（本番監視 DB）を使用します。
- Execution の paper_trading は本番 DB と完全分離して PAPER_TRADING_SQLITE_PATH を使用します。
- ログ:
  - 共通のログ設定ユーティリティ (kabusys.utils.logging_setup) を利用し、stdout と日次ローテートファイル（logs/<app>.log）に出力します。
- Kill Switch / stop flag:
  - data/kill.flag：KillSwitch が書き込むファイル。ExecutionEngine は起動時あるいは監視でこのファイルを検知して停止します。
  - data/stop_requested.flag：run_monitoring / run_execution がループ終了や停止判定で使用するフラグ（プロジェクト内で共通）。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を最初に呼びます（psutil に依存。権限不足だと警告でスキップ）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存 DB に対する小さなスキーマ追加（ALTER TABLE）も行います。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（.env 自動読み込み機能含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (実装に応じて存在)
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装に応じて存在)
  - execution/                 — ExecutionEngine 周り（broker, order_manager, risk_manager 等）
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (ランタイムで生成)
    - kill.flag, stop_requested.flag, execution.pid, monitoring.db / paper_trading.db など
  - logs/ (ランタイムで生成)
    - execution.log, monitoring.log, ...

（実際のファイル一覧はリポジトリ内の src/kabusys 以下を参照してください）

---

よくある運用上の注意
- KABUSYS_ENV=live の場合は誤操作で実際に発注が行われます。LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や Kill Switch 設定を必ず確認してください。
- 本番で KILL_FLAG_CLEAR_ON_START=1 を設定するのは危険です（Kill Switch が自動でクリアされます）。デフォルトは 0 推奨。
- OpenAI を利用する機能は API 負荷・コストを伴います。API キーの管理と利用制限に注意してください。
- ログディレクトリや DB ファイルの作成に十分な権限があることを事前に確認してください。権限不足時はファイル出力が失敗し、コンソール出力のみになる場合があります。

---

この README はコードベースのソースコメント・関数ドキュメントを元に作成しました。詳細な実装や追加のコマンド、設定テンプレート（.env.example、config/*.yaml 生成スクリプト等）はリポジトリ内の該当ファイルを参照してください。質問や追加で README に含めたい内容があれば教えてください。