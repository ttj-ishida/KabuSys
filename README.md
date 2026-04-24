# KabuSys

日本株向け自動売買フレームワーク（プロトタイプ）  
このリポジトリは、戦略・発注・監視・研究・AI支援（ニュースNLP / レジーム判定）などを含む自動売買システムの主要コンポーネントを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件
- セットアップ手順
- 環境変数（代表的なもの）
- 使い方（起動スクリプト / CLI）
- 運用上の注意点
- ディレクトリ構成（主要ファイルの説明）

---

## プロジェクト概要

KabuSys は日本株を想定した自動売買システムの基盤コンポーネント群です。戦略で生成されたシグナルをもとにポートフォリオ構築、ポジションサイジング、リスク管理、発注（kabuステーションまたはモック）を行い、並行して監視・アラート・Kill Switch を提供します。研究用に DuckDB を用いたファクター計算や特徴量解析、OpenAI を利用したニュースセンチメント評価やレジーム判定のモジュールも含まれます。

---

## 主な機能一覧

- ExecutionEngine: 発注処理（本番は kabuステーション、paper_trading ではモック）
- Monitoring: システム状態・データ鮮度・トレード状態・リスク監視、Kill Switch 書き込み
- MonitoringDB: SQLite による監視ログ永続化（system_status, trade_logs, risk_logs, positions, dashboard）
- Portfolio construction:
  - 候補選定 (select_candidates)
  - 重み計算（等額 / スコア加重）
  - ポジションサイズ決定（risk_based 等）
  - セクターキャップ・レジーム乗数
- Research:
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC、統計サマリー
- AI:
  - ニュース NLP（OpenAI を用いた銘柄別センチメント）
  - レジーム判定（ETF MA + マクロニュース）
- ツール:
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の起動前検証
  - paper_verification_report: ペーパートレード検証レポート生成

---

## 必要条件

- Python 3.9+
- 主要ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（validate_config 中の YAML 検証時に必要）
- SQLite（Python 標準ライブラリに含まれる）
- （運用）kabuステーション API アクセスが必要な場合は当該 API 環境

※ requirements.txt は本リポジトリに含めていない場合があるため、最低限上記パッケージを pip で導入してください。

例:
pip install duckdb psutil openai PyYAML

---

## セットアップ手順（簡易）

1. リポジトリをクローン / 取得
2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML
4. .env ファイルを作成
   - 対話式ウィザードを使用:
     python -m kabusys.config_setup
   - または .env.example を参考に手動作成
5. ディレクトリ作成（初回）
   mkdir -p data logs
6. 設定検証（任意）
   python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱い（exit code 1）

---

## 環境変数（代表例）

重要な環境変数（デフォルト値や説明）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI モジュール使用時に必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、ExecutionEngine はモックブローカを使用し、paper 用 DB に記録します
- LOG_LEVEL (DEBUG/INFO/...)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の fill 動作: instant / partial / never / reject)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時の kill.flag 自動クリア: "1" で有効 — 本番では推奨しない)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔（秒）。run_monitoring で使用、デフォルト 60)

.env を作成していれば、Settings モジュールが起動時に自動読み込みします（プロジェクトルートの .env / .env.local を探索）。

---

## 使い方（主要コマンド）

本パッケージはモジュールを直接実行するスタイルを想定しています。プロジェクトルートで実行してください（.env 読込のため）。

- .env 作成ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に発注ログを保存します。
  - 実行中、data/execution.pid が作成されます。停止は data/stop_requested.flag（停止フラグ）や外部から engine.stop() を呼ぶ方法で行います。
  - 起動前に data/stop_requested.flag が存在する場合は起動を中止します。

- Monitoring（監視ループ）起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用（KABUSYS_ENV に依存せず本番 DB を参照する設計）
  - data/stop_requested.flag が存在すると監視ループは終了します

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / レジーム判定・ニューススコア
  - kabusys.ai.score_news や kabusys.ai.regime_detector.score_regime をプログラム的に呼び出して使用
  - OpenAI API キー（OPENAI_API_KEY）が必要

---

## 運用上の注意点 / Kill Switch

- Kill Switch: RiskMonitor が条件を満たすと kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）を書き込み、ExecutionEngine に停止シグナルを与えます。kill.flag は ExecutionEngine 起動時の設定により自動クリアされる場合があります（KILL_FLAG_CLEAR_ON_START）。
- stop_requested.flag: run_execution/run_monitoring の外部停止トリガーとして data/stop_requested.flag が使用されています。これを作成するとループが安全に終了します。
- PID ファイル: ExecutionEngine は起動時に pid ファイルを書きます（Settings.pid_file_path）。複数インスタンスの誤起動防止に利用してください。
- Paper Trading: paper_trading 環境は本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 以下の主要ファイル／モジュールの要約です。

- run_execution.py
  - ExecutionEngine を組み立て起動するエントリポイント。KABUSYS_ENV=paper_trading のときは MockBroker を使用。data/execution.pid、stop フラグを扱う。

- run_monitoring.py
  - SystemMonitor をポーリングする監視ループエントリポイント。MONITOR_POLL_INTERVAL で間隔指定。

- config.py
  - Settings クラス。環境変数 / .env の読み込み・検証。Settings インスタンス経由で各種パス・フラグ・閾値を取得。

- config_setup.py
  - 対話式 .env 生成ウィザード。

- validate_config.py
  - 起動前の設定チェック CLI（必須環境変数・パス・config/*.yaml の存在などを検査）。

- utils/
  - logging_setup.py: ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
  - process_priority.py: プロセス優先度・CPU affinity 設定
  - その他補助ユーティリティ群

- monitoring/
  - monitoring_db.py: SQLite を用いた監視ログの永続化（テーブル作成・Migration を含む）と MonitoringDB クラス
  - system_monitor.py: CPU/メモリ/ディスクやデータ鮮度、Execution プロセスの死活監視
  - trade_monitor.py: trade_logs の監視（滞留注文、成立異常チェック） — （ファイル一部はここに存在）
  - risk_monitor.py: ドローダウン / ポジション上限の監視（Kill Switch の入力）
  - kill_switch.py: kill.flag の作成 / 管理
  - monitoring_engine.py: 個別モニタを束ねてポーリング実行（run_once / run）

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  - 発注ロジック、リスク制御、ブローカ抽象化を実装（実際の詳細は各ファイル参照）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数決定・資金割当ロジック
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー計算（DuckDB を使用）
  - feature_exploration.py: 将来リターン計算・IC・統計サマリー

- ai/
  - news_nlp.py: OpenAI を用いたニュースセンチメント評価、ai_scores テーブルへの書き込み
  - regime_detector.py: ETF MA とマクロニュースを合成した日次レジーム判定（OpenAI 使用）

- tools/
  - paper_verification_report.py: ペーパートレード検証レポート生成スクリプト

---

## 参考・運用ヒント

- .env は決して Git にコミットしないでください（config_setup もヘッダで注意を出します）。
- 本番（KABUSYS_ENV=live）での起動前に validate_config を実行してリスク設定や通知設定（LINE など）を確認してください。
- AI モジュールは外部 API（OpenAI）に依存します。キーとコスト管理に注意してください。API 失敗時はフォールバック動作（0.0 等）が実装されていますが、挙動確認を行ってください。
- ログ: logs/<app_name>.log に日次ローテーションで出力されます。LOG_DIR 環境変数で変更可能です。

---

README は以上です。各モジュールの詳細な利用方法や拡張方法は、該当ソースファイルの docstring を参照してください。必要であればコマンド別の起動例やデプロイ手順、systemd / supervisor 用のユニットファイル例も作成できますので依頼してください。