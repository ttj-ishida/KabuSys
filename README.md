# KabuSys

日本株自動売買システムのコアライブラリ群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AIユーティリティなど）。

このリポジトリは、発注エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネント、研究/ファクター計算、AI を用いたニューススコアリング等を含みます。設計方針として「本番 DB と開発 / ペーパートレードを明確に分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に制御」などが取られています。

---

## 主な機能

- 環境設定管理
  - .env の自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式 env ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行エンジン（Execution）
  - 本番 / ペーパートレードモード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBroker を用いたペーパートレード）
  - リスク管理、注文管理、再整合（Reconciler）等の組み込み

- 監視（Monitoring）
  - システム状態（CPU/メモリ/ディスク）やデータ鮮度のポーリング
  - 取引ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を停止）
  - 監視ループ起動スクリプト（MONITOR_POLL_INTERVAL によるポーリング間隔設定）

- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap によるスケーリング）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）統合（任意）
  - ニュースのセンチメント解析（news_nlp）
  - 市場レジーム判定（regime_detector）
  - OpenAI API 使用時は OPENAI_API_KEY を指定

- ユーティリティ
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定（psutil 利用）
  - Paper Trading 検証レポート生成ツール

---

## 前提 / 依存関係

最低限以下が必要になります（環境によって追加で必要になることがあります）:

- Python 3.9+
- pip パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config の厳密検証を使う場合、任意）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt がある場合はそれを使ってください）

---

## セットアップ手順

1. レポジトリをクローン・チェックアウト

2. 仮想環境を作成・アクティベート（任意）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他主要変数:
     - KABUSYS_ENV (development / paper_trading / live)
     - DUCKDB_PATH, SQLITE_PATH
     - OPENAI_API_KEY（AI を使用する場合）
   - 注意: .env を Git にコミットしないでください（機密情報を含むため）。

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 追加で厳格モード: python -m kabusys.validate_config --strict

6. データ / ログディレクトリ
   - デフォルトで SQLite は data/monitoring.db（実際は Settings で上書き可）、DuckDB は data/kabusys.duckdb を使用
   - ログは logs/<app_name>.log に日次ローテート（デフォルト 30 日保持）
   - 必要なディレクトリは起動時に自動作成される場合あり

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に書き込む（本番 DB と完全分離）
    - プロセス優先度を high に設定し、ExecutionEngine をスレッドで起動
    - data/stop_requested.flag が存在すると起動せず終了、または起動中に検知すれば停止する
    - PID ファイル path は Settings.pid_file_path（デフォルト data/execution.pid）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を設定（デフォルト 60）
    - 監視は本番 sqlite_path を使用（KABUSYS_ENV に関わらず）
    - 停止フラグファイル data/stop_requested.flag を検知するとループを終了

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース・レジーム）
  - kabusys.ai.score_news（duckdb コネクション & target_date を渡す）
  - kabusys.ai.regime_detector.score_regime（同様）
  - いずれも OPENAI_API_KEY or api_key 引数が必要

停止 / Kill Switch 関連:
- KillSwitch はリスク基準（ドローダウンやポジション上限）を満たした場合に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る設計です。
- 手動停止フラグ（起動/監視スクリプトが参照する）:
  - data/stop_requested.flag を作成すると run_* スクリプトが検知してシャットダウンします。

ログ:
- デフォルト logs/<app_name>.log に出力されます（コンソールにも同時出力）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（開発用。0/1）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）

.env 生成や設定項目の説明は python -m kabusys.config_setup を参照してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を示します）

- kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings クラス
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py     — ロギング初期化ユーティリティ
    - process_priority.py  — プロセス優先度 / affinity ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py     — システム・データ鮮度チェック
    - trade_monitor.py      — （取引監視。実装参照）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 書き込みロジック
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - alert_manager.py      — （アラート送信管理。実装参照）
  - execution/
    - execution_engine.py  — 実行エンジン本体（EngineConfig 等）
    - broker_factory.py    — ブローカクライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py          — ニュース NLP スコアリング（OpenAI 統合）
    - regime_detector.py   — マーケットレジーム判定（AI + MA200 合成）
    - __init__.py
  - data/                 — 既定の DB / フラグファイル保存先（プロジェクトルートの data/）
  - logs/                 — デフォルトログ出力先

（実際のファイル構成はリポジトリのルートを参照してください）

---

## 開発・運用上の注意

- .env（機密情報）は決してリポジトリにコミットしないこと。
- KABUSYS_ENV=live の場合は特に注意して設定を確認してください（validate_config の警告を参照）。
- AI 機能は外部 API（OpenAI）を呼び出すため、API 使用料・レートリミットに注意してください。ネットワークエラーや 5xx は内部でリトライを行いますが、完全に失敗した場合はフェイルセーフで代替動作（スコア 0.0 等）となります。
- ペーパートレードは本番 DB と分離されます。KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）が使用されます。
- 監視コンポーネントは MONITOR_POLL_INTERVAL により調整可能（秒）。不正な値はデフォルト（60秒）にフォールバックします。
- ログディレクトリの作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります。

---

もし README に追加したいセクション（API リファレンス、設定ファイルの例、運用手順の詳細など）があれば教えてください。必要に応じてサンプル .env のテンプレートや具体的な起動例を追記します。