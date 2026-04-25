# KabuSys

日本株自動売買システムのミニマル実装（ライブラリ + 起動スクリプト群）

このリポジトリは、シンプルな自動売買基盤のコンポーネント群を含みます。主な役割は以下の通りです。
- 実行エンジン（ExecutionEngine）：発注・注文管理・リスク管理 を担う
- 監視（Monitoring）：システム状態・注文挙動・リスクを定期チェックしてアラートや Kill Switch を発動
- ポートフォリオ構築・サイズ決定ロジック（純粋関数群）
- 研究/リサーチ用モジュール（ファクター計算・IC 計算等）
- ニュースの NLP スコアリング / レジーム判定（OpenAI を利用）
- ユーティリティ（ログ設定・プロセス優先度等）と CLI ツール群

以下はこのコードベースの簡易 README です。

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（python -m kabusys.run_execution）
  - ブローカークライアントの抽象化（paper_trading 時は MockBrokerClient を使用）
  - OrderManager / OrderRepository / Reconciler / RiskManager 等の組み立て
  - paper_trading 環境では data/paper_trading.db に完全分離して記録

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせる MonitoringEngine
  - SQLite に system_status, trade_logs, positions, risk_logs, dashboard テーブルを保持（init は冪等）
  - Kill Switch（条件に応じて data/kill.flag を書き込み Execution を停止）
  - run_monitoring スクリプト（ポーリングループ、MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能）

- Portfolio construction
  - 候補選定、等重・スコア重み付け、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイズ計算（リスクベース／等配分／スコア配分、単元株丸め、集約キャップ調整）

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）の計算、統計サマリ

- AI（OpenAI）
  - ニュース記事をまとめて銘柄ごとのセンチメントを計算し ai_scores テーブルに書き込む（kabusys.ai.news_nlp）
  - マクロニュース＋ETF MA を組み合わせて市場レジーム判定を行い market_regime に記録（kabusys.ai.regime_detector）

- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）: .env の作成・更新を対話式で支援
  - 設定検証 CLI（python -m kabusys.validate_config）: .env や config/*.yaml の不足を起動前に検出
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - openai
     - psutil
     - （任意）PyYAML（validate_config が YAML のパースを行えるようにする）
   - 例:
     - pip install duckdb openai psutil pyyaml

   ※ requirements.txt は本 README に含まれていません。プロジェクトで使用する環境に合わせてパッケージをインストールしてください。

4. 環境変数（.env）を用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 手動で .env を作る場合は .env.example を参照してください（主要キーは下記参照）。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラーとして扱いたい場合: python -m kabusys.validate_config --strict

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）. default=development
  - paper_trading: 発注は MockBrokerClient に記録され data/paper_trading.db を使用
  - live: 実際の発注が行われる前提（設定は慎重に）

- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring.db）のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト 60
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行/監視制御に関する設定
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant/partial/never/reject）

注意: Settings モジュールは起動時にプロジェクトルートの .env / .env.local を自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 使い方（起動例）

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパー共通エントリ）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid が生成される（pid_file の設定で変更可能）
    - 停止は data/stop_requested.flag を作成するか、KillSwitch により data/kill.flag が作成され実行エンジンが停止される

- Monitoring 起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
    - Monitoring は KABUSYS_ENV に関係なく production の sqlite_path（Settings.sqlite_path）を使用
    - 停止は同様に data/stop_requested.flag による

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(...) を呼んでニュースセンチメントを ai_scores に書き込めます（OpenAI API キーが必要）
  - kabusys.ai.regime_detector.score_regime(...) で市場レジームを計算・書き込み

ログ出力
- ログは kabusys.utils.logging_setup.setup_logging を通じて設定され、デフォルトでは logs/<app_name>.log に日次ローテーションで保存されます。
- 起動スクリプトは setup_logging を呼んでいるため、各アプリ（execution / monitoring）のログファイルは logs/execution.log, logs/monitoring.log になります。

停止・Kill
- 手動停止: プロジェクトルート下の data/stop_requested.flag を作成すると run_execution/run_monitoring が次のループで検知して終了します。
- 自動停止（Kill Switch）: RiskMonitor 等の判定により KillSwitch が data/kill.flag を書き込むと ExecutionEngine 側で検知して発注処理を停止します。KillSwitch は Settings.kill_flag_path を使用（デフォルト data/kill.flag）。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py                  — 環境変数 / Settings 管理（.env 自動ロード）
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring ポーリングループ起動スクリプト

packages / サブパッケージ
- execution/                  — Execution 関連（Engine, OrderManager, BrokerFactory 等）
- monitoring/
  - monitoring_db.py          — SQLite スキーマ初期化 + 永続化ラッパ
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
- ai/
  - news_nlp.py               — OpenAI を用いたニューススコアリング
  - regime_detector.py
- data/
  - pipeline.py (参照される価格取得ヘルパ等)
- tools/
  - paper_verification_report.py

utils/
- logging_setup.py            — ログの初期化ユーティリティ
- process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ

その他
- data/                      — 実行時に使う SQLite / flag / pid ファイル（デフォルト）
- logs/                      — ログ出力ディレクトリ（デフォルト）

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では設定や API キー管理に十分注意してください。validate_config は本番向けの簡易チェックを提供します。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- Monitoring は SQLite の sqlite_path を直接使います。paper_trading 環境でも監視 DB は production の sqlite_path を参照する設計です（実行エンジンは paper_trading 用 DB に書き分け）。
- OpenAI を利用する機能は API 料金・レイテンシリスクがあります。API キーの管理・コール頻度に注意してください。
- process_priority や CPU affinity の設定は環境依存で失敗することがあります（psutil による権限エラー等）。その場合は警告ログが出てスキップされます。

---

もし README をプロジェクトルートに配置する形で markdown ファイルが必要であれば、この内容を README.md として保存してください。追加で起動スクリプトの systemd ユニットや Dockerfile、requirements.txt を用意したい場合は教えてください。