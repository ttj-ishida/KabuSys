# KabuSys

日本株向け自動売買システムのコアライブラリ群と起動スクリプト群。  
このリポジトリには、シグナル／ポートフォリオ構築、ポジションサイズ計算、監視・アラート、ペーパートレード検証、AI（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれます。

## プロジェクト概要
- 戦略ロジック（ファクター計算、特徴量探索、ポートフォリオ構築、ポジションサイズ決定）を純粋関数として提供。
- 実行（ExecutionEngine）と監視（MonitoringEngine）を別プロセスで起動する運用設計。
- DuckDB／SQLite をデータ層として利用（分析用に DuckDB、監視・注文ログに SQLite）。
- OpenAI を使ったニュースのセンチメント評価やマクロセンチメント集約（要 API キー）。
- ペーパートレード用 DB を用意し、本番 DB と完全に分離可能。
- ログはコンソールと日次ローテートファイルに出力（logs/*.log）。

---

## 主な機能一覧
- Portfolio
  - 候補選定（スコア順）、等金額・スコア加重の重み算出
  - セクター上限適用、レジーム乗数計算
  - ポジションサイズ計算（単元株丸め・リスクベース・集約キャップ）
- Research
  - Momentum / Volatility / Value ファクターの DuckDB ベース計算
  - 将来リターン計算、IC（Information Coefficient）やファクター統計
- AI
  - news_nlp: ニュース記事を LLM (gpt-4o-mini) でセンチメント化して ai_scores に書込
  - regime_detector: ETF（1321）MA とマクロニュースを LLM で合成して日次レジーム判定
- Monitoring
  - SystemMonitor: CPU/MEM/DISK、Execution プロセス生存、データ鮮度チェック
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限監視
  - KillSwitch: しきい値超過で data/kill.flag を書き込み ExecutionEngine を停止
  - Monitoring DB (SQLite): system_status / trade_logs / positions / risk_logs / dashboard
- Utilities
  - .env 対話式ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）
  - ログ設定 / プロセス優先度設定ユーティリティ

---

## セットアップ手順（開発環境向け）
※プロダクション配備は OS パッケージやデーモン管理を考慮してください。

1. リポジトリをチェックアウトし、Python 仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（推定）
   - 必須ライブラリ（コードから読み取れるもの）:
     - duckdb, psutil, openai
   - 開発時あるいはオプション:
     - PyYAML（config/*.yaml の検証に使用、必須ではない）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください:
   pip install -r requirements.txt）

3. 初期設定ファイル（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（ルートに配置）。許容値の例は `.env.example` を参照してください（存在する場合）。

4. 必須環境変数を設定（代表例）
   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD （必須）
   - その他（任意も含む）:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
   - .env 自動読み込みはデフォルトで有効。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. data ディレクトリなど必要なフォルダを作成（多くは起動時に自動作成されますが事前作成すると安心）
   - mkdir -p data logs

6. （任意）設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

---

## 使い方（起動・操作）
以下は代表的な起動方法です。各モジュールはパッケージモジュールとして実行できます。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading の場合: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します（本番 DB と分離）
  - 起動前に data/kill.flag があると起動をスキップします
  - ExecutionEngine は data/execution.pid に PID を書きます（pid ファイルの場所は Settings.pid_file_path で変更可能）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60 秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 確認指標: 稼働率、注文成功率、送信率、P95 レイテンシ など

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要: OPENAI_API_KEY 環境変数または関数呼び出し時に渡す
  - 失敗時はフェイルセーフ（多くの場所で 0.0 やスキップで継続）

- Kill Switch
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 を推奨）

---

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の fill モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

---

## ディレクトリ構成
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
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
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/
    - execution_engine.py (参照あり)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記はコードベースに含まれる主要コンポーネントを示します。実際のファイル構成はリポジトリ内のディレクトリを参照してください。）

---

## 運用上の注意 / トラブルシューティング
- .env は機密情報を含むため、決して VCS にコミットしないでください。
- ログ出力先ディレクトリ（LOG_DIR）の作成に失敗するとファイルハンドラは無効化され、コンソール出力のみになります。権限を確認してください。
- OpenAI 関連は API 料金が発生します。大量バッチや頻繁な呼び出しに注意してください。
- psutil を使ってプロセス優先度や CPU affinity を設定しています。パーミッションによっては設定に失敗する場合があり、その場合は警告ログが出ます。
- DuckDB / SQLite への接続は起動時に行われ、必要なテーブル（monitoring DB 等）は起動時に自動作成／マイグレーションされます（init_monitoring_db）。
- MONITOR_POLL_INTERVAL に 0 以下や非整数を設定するとデフォルト（60 秒）にフォールバックします。

---

## 参考コマンドまとめ
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- （開発）DuckDB SQL を直接叩いて調査やデバッグを行ってください。

---

以上。README の内容で補足や追記したい部分（例: 実際の依存関係リスト、デーモン化手順、CI 設定など）があれば教えてください。必要に応じて README を拡張します。