# KabuSys

KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリはトレード実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI 統合）などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

主な目的は「安全に」「再現性を持って」「本番／ペーパートレードを分離して」自動売買を行うことです。  
設計上のポイント：

- 本番（live）／ペーパートレード（paper_trading）／開発（development）モードを環境変数で切替可能
- 監視（Monitoring）コンポーネントでシステム状態・注文状態・リスクを定期チェック
- Kill Switch（フラグファイル）で遠隔停止を安全に実現
- DuckDB を用いたリサーチ（ファクター計算、特徴量探索）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価 / レジーム判定（オプション）
- ペーパートレードは本番 DB と完全分離（デフォルトで data/paper_trading.db）

---

## 機能一覧

- ExecutionEngine（発注エンジン）
  - ブローカー抽象化（paper_trading では MockBrokerClient）
  - 注文管理、リスク制御、リコンシリエーション
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常などの検出
  - RiskMonitor：ドローダウンやポジション上限の監視、アラート保存
  - KillSwitch：条件に応じて data/kill.flag を作成して ExecutionEngine を停止
  - MonitoringEngine：上のモニタ群を束ねたポーリング実行
- ポートフォリオ構築（pure functions）
  - 候補選定、等比重/スコア重み、ポジションサイズ決定、セクター制限、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン・IC・統計サマリ
- AI
  - news_nlp：ニュース記事を OpenAI でセンチメント化し ai_scores に書き込み
  - regime_detector：ETF とマクロニュースを組み合わせて市場レジーム判定
- ユーティリティ
  - 設定ウィザード（.env 対話生成）
  - 設定検証 CLI（validate_config）
  - ログ設定ユーティリティ（ログローテート・コンソール出力統一）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- ツール
  - paper_verification_report：ペーパートレード DB から検証レポート生成

---

## 必要条件

- Python 3.10+
- 必須ライブラリ（概要）
  - duckdb
  - psutil
  - openai（AI 機能を利用する場合）
- オプション
  - PyYAML（`python -m kabusys.validate_config` が YAML の中身検証をする場合に必要）
- DB
  - SQLite（標準ライブラリで利用）
  - DuckDB（分析用）

（実際のバージョンや追加依存はプロジェクトの requirements.txt を参照してください）

---

## セットアップ手順（ローカル）

1. リポジトリをクローンして移動
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 検証を使うなら）pip install pyyaml

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も fail にしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの確保（通常は自動作成されますが念のため）
   - mkdir -p data logs

---

## 主要な環境変数（抜粋）

重要なもの（Settings 参照）：

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY（AI 機能を使う場合に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔を秒で上書き、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0/1）

ログ関連:
- LOG_DIR（ログ保存ディレクトリ、デフォルト: logs/）

---

## 使い方（起動コマンド）

基本的にモジュールとして起動します。プロジェクトルートで実行してください。

- ExecutionEngine（トレード実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、デフォルトで data/paper_trading.db に記録されます。
  - 実行中、プロセス PID は data/execution.pid に書き込まれます。
  - 停止要求は data/stop_requested.flag を作成することで検知します（監視スクリプトも同様のフラグを使用）。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - デフォルトポーリング間隔: 60 秒。環境変数 MONITOR_POLL_INTERVAL で変更可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings に定義された sqlite_path（監視 DB）を常に使用します。
  - 同様に data/stop_requested.flag を検知するとループを終了します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として扱います

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム検出）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定
  - ニューススコア算出は kabusys.ai.score_news / regime_detector.score_regime をプログラムから呼び出して利用できます

停止・強制停止関連:

- Kill Switch（自動）
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります
- マニュアル停止
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のメインループが検知して終了します
- 起動時に kill.flag を自動で消したい場合は KILL_FLAG_CLEAR_ON_START=1（ただし本番では推奨されません）

ログ:

- デフォルトは logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
- コンソール出力は stdout（StreamHandler）にも出力されます

---

## 開発者向けメモ

- 設定自動ロード:
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml があるディレクトリ）から読み込まれます
  - テスト等で自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等にテーブルを作成し、いくつかのカラム追加マイグレーションを内包しています
- ロギング:
  - setup_logging(app_name=...) を各スクリプトの起動時に呼んで統一的なログ設定を適用しています
- プロセス優先度:
  - set_process_priority("high") を起動時に行い、Windows / POSIX の差分を吸収します

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py                  — 環境変数 / Settings 管理、自動 .env ロード
- config_setup.py            — 対話式 .env ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — Monitoring ポーリングループ起動スクリプト

- execution/                 — 発注関連（Engine, OrderManager, BrokerFactory 等）※サブ実装ファイルは省略
- monitoring/
  - monitoring_db.py         — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py         —（滞留注文検出等）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py         —（アラート送信ロジック）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py              — OpenAI を使ったニュースセンチメント
  - regime_detector.py       — レジーム判定（MA + マクロニュース）
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

ルート（プロジェクト）:

- config/                    — system_config.yaml 等のテンプレ（validate_config が参照）
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/                      — デフォルトの DB / PID / フラグファイル 保存先（.git にコミットしないこと）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/                      — ログファイル出力先

---

## 備考 / 注意点

- 本番（KABUSYS_ENV=live）では kill.flag やデフォルト設定を慎重に扱ってください。validate_config の live ガードを参照してください。
- OpenAI を利用する機能は API キーとコストが発生します。失敗時にフェイルセーフ（デフォルト値）を用いる設計になっていますが、利用前に十分な検証を行ってください。
- .env は機密情報を含むため絶対にバージョン管理にコミットしないでください（config_setup でも注記あり）。
- Python の型記法（|）を多用しているため Python 3.10 以上を推奨します。

---

README に書かれている内容はコードベースの主要機能と起動方法の概要です。より詳しい実装や運用手順は該当モジュールの docstring を参照してください。必要であれば、起動スクリプトの具体的な systemd / supervisor のユニット例や Dockerfile、CI 設定の例なども追加します。ご希望があれば教えてください。