# KabuSys

日本株向け自動売買システムのリポジトリ。バックテスト/リサーチ/ポートフォリオ構築、発注エンジン、監視・アラート、AI を利用したニュース・レジーム判定などを含むモジュール群で構成されています。

## 概要
KabuSys は以下の主要コンポーネントを提供します。

- ExecutionEngine：ブローカーとのやり取りを行い、発注・注文管理・リスク管理を行う実行エンジン
- Monitoring：システム状態・注文状況・リスク（ドローダウン、ポジション数）を定期的に監視し、Kill Switch による停止やアラート送出を行う
- Research / Portfolio：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）、ポートフォリオ構築／ポジションサイズ計算モジュール
- AI：OpenAI を用いたニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）
- Tools：検証レポート生成などユーティリティスクリプト
- Utils：ログ設定、プロセス優先度設定など共通ユーティリティ

設計上のポイント：
- DuckDB / SQLite をデータ格納に利用（分析用 DuckDB、監視用 SQLite）
- Paper Trading と本番（live）は DB を分離（paper_trading 用 DB を使用）
- .env による環境変数管理と対話式ウィザード・検証ツールを提供
- OpenAI 呼び出しには堅牢なリトライ／バリデーション実装

---

## 主な機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し data/paper_trading.db に記録
  - PID ファイル / stop flag による制御
- Monitoring 起動スクリプト（src/kabusys/run_monitoring.py）
  - 定期ポーリングで system / trade / risk をチェック
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - kill.flag による ExecutionEngine 停止トリガ
- Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）
- ファクター計算（kabusys.research.calc_*）
- ポートフォリオ構築、ウェイト算出、ポジションサイズ計算（kabusys.portfolio）
- OpenAI を使ったニューススコアリング / レジーム判定（kabusys.ai）

---

## セットアップ手順（開発/実行環境）
前提：Python 3.10 以上を推奨（ユニオン型 | を使用しているため）。

1. リポジトリをクローンしてワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 必要パッケージをインストール
   - 最低限必要な主な依存（プロジェクトに requirements.txt がない場合の例）:
     ```
     pip install duckdb psutil openai
     ```
   - オプショナル:
     - PyYAML（config/*.yaml の構文チェックを行う場合）:
       ```
       pip install PyYAML
       ```
   - テストや開発で使用する追加パッケージがあれば別途インストールしてください。

3. ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data logs
   ```
   デフォルトでは以下ファイルパスが使われます（環境変数で変更可）:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper Trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/
   - PID / flag: data/execution.pid, data/stop_requested.flag, data/kill.flag

4. .env の作成（対話式推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成/更新します。作成後に設定検証を実行します。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。

---

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（Paper Trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- PAPER_FILL_MODE（paper_trading の MockBroker 挙動、"instant"|"partial"|"never"|"reject"、デフォルト: "instant"）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）。デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか 0/1）

.env 作成は config_setup を利用すると簡単です。

---

## 使い方（起動例）
- ExecutionEngine を起動（通常）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を設定してペーパートレードモードで起動すると、MockBroker を使い data/paper_trading.db にログを残します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せずに終了します。

- Monitoring を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でループ間隔を変更可能（秒）。
  - 監視は常に本番向けの sqlite_path を使います（環境に関係なく同一監視 DB を参照）。

- Paper Trading 検証レポートを生成（例）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- .env の確認 / 更新
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- AI 機能を直接呼ぶ（ライブラリ的利用）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  いずれも OPENAI_API_KEY を環境変数に設定しておくことで api_key を省略できます。

---

## 停止・制御ファイル
- data/stop_requested.flag
  - run_execution/run_monitoring のループを安全に停止させるためのフラグファイル。存在を検知すると起動中のプロセスは終了処理を行います。
- data/execution.pid
  - ExecutionEngine 起動時に PID を書き込むためのファイルパス（Settings.pid_file_path）
- data/kill.flag
  - Monitoring の KillSwitch によって書き込まれると ExecutionEngine 側で検知し停止される（本番での緊急停止メカニズム）

---

## ログ
- 共通のログ設定ユーティリティ (kabusys.utils.logging_setup) を利用しています。
- デフォルトでは stdout と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。
- ログレベルは LOG_LEVEL 環境変数で調整可能。

---

## ディレクトリ構成（主要ファイル）
リポジトリ内の主要モジュール構成の抜粋：

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数読み込み・Settings 定義
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照されるがここに一覧)
  - execution/                # 発注・注文管理系（ファクトリ・エンジン等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/                     # スクリプトや DB ファイル（外部格納を想定）
  - config/                   # system_config.yaml 等（validate_config が参照）

（上記は主要ファイルのみ抜粋しています。詳細は src/kabusys 以下を参照してください。）

---

## 注意事項 / 運用上のヒント
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかにしてください。live は本番モードのため慎重に設定してください。
- Paper Trading モードでは実際の発注を行わず、MockBroker を利用してデータを paper_trading 用 DB に保存します。本番 DB と完全に分離されます。
- OpenAI を利用する機能はネットワーク／API エラーに対してリトライとフェイルセーフ（失敗時はスコア 0.0 等）を実装しています。ただし API キーの管理・コストには注意してください。
- Logging / PID / flag ファイルのパスは Settings を通してカスタマイズできます（環境変数で上書き可能）。
- monitor は監視 DB（sqlite_path）を参照するため、監視対象と実行エンジンの DB 関係を把握しておいてください（paper_trading 時の動作差異など）。

---

## さらに詳しいドキュメント
各パッケージ内の docstring に主要な設計意図やアルゴリズム注釈があります。特に以下のファイルは設計方針が詳述されています：
- portfolio/*（PortfolioConstruction.md に基づく実装注釈）
- research/*（StrategyModel.md に基づくファクター設計）
- ai/*（ニュース／レジームロジックの詳細）

---

不明点や README に追記してほしい項目があれば教えてください。必要に応じて起動例・環境変数一覧・トラブルシュート等を追記します。