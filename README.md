# KabuSys

日本株向け自動売買・リサーチ用ライブラリ兼起動スクリプト群です。  
ポートフォリオ構築・ポジションサイズ計算・監視・実行エンジン・AI を用いたニュース解析など、取引運用に必要な主要機能をモジュール化して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持ったコンポーネント群を含みます:

- 戦略リサーチ / ファクター計算（DuckDB を利用した時系列集計）
- ポートフォリオ構築（候補選定・重み付け・リスク調整・ポジションサイズ算出）
- 実行エンジン（kabuステーション / MockBroker を用いた発注処理）
- 監視（システム稼働状況・注文ログ・リスク監視・Kill Switch）
- AI 支援（ニュースセンチメント・市場レジーム判定） — OpenAI API を利用
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

設計方針として、実行系は本番・ペーパートレードで DB を分離し、DB（SQLite、DuckDB）やログ出力を中心に状態を永続化します。LLM 呼び出しはオプションで、失敗時は安全側フォールバックします。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証ツール（python -m kabusys.validate_config）
- ExecutionEngine 起動（運用・ペーパートレード対応）（python -m kabusys.run_execution）
- Monitoring 起動（SystemMonitor のポーリングループ）（python -m kabusys.run_monitoring）
- Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）
- ポートフォリオ構築ユーティリティ
  - 候補選定: select_candidates
  - 等金額 / スコア重み: calc_equal_weights / calc_score_weights
  - ポジションサイズ計算: calc_position_sizes
  - セクター上限 / レジーム乗数: apply_sector_cap / calc_regime_multiplier
- 研究用モジュール
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC・統計サマリー
- AI 関連
  - ニュースのセンチメントスコア化（OpenAI）
  - 市場レジーム判定（ETF MA + マクロニュース + LLM）

---

## 動作要件（推奨）

- Python 3.10+
- 必要な外部ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使用する場合)
  - PyYAML（config の YAML 検証を行う場合、任意）
- OS: Linux / macOS / Windows（ただし process priority や cpu affinity は OS により制限あり）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実際の運用では requirements.txt を用意して管理してください。）

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成して依存をインストール（上記を参照）
3. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 手動の場合はリポジトリの .env.example を参考に `.env` を作成してください。
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   `--strict` を付けると警告も失敗扱いにできます。
5. DuckDB / SQLite DB の準備:
   - デフォルトパス: `data/kabusys.duckdb`, `data/monitoring.db`
   - 必要に応じて環境変数で上書き:
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
6. ログ出力ディレクトリ: デフォルト `logs/`。`LOG_DIR` で変更可。

----

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（デフォルト値含む）:
- KABUSYS_ENV: execution モード（development | paper_trading | live） — default: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR: logs/
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0/1
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定動作）
- OPENAI_API_KEY: OpenAI を使う場合必須（AI 機能）

注意: .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効にできます。

---

## 使い方（主要スクリプト）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパー共通起動:
    ```
    python -m kabusys.run_execution
    ```
  - ペーパートレードにするには:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
    ペーパーの場合は MockBrokerClient を使用し、デフォルトで `data/paper_trading.db` に記録されます（本番 DB とは分離）。

  - 停止: プロセスは `data/stop_requested.flag` の存在を監視します。flag ファイルを作成すると安全に停止をトリガできます（実際の運用方法は運用手順に従ってください）。

- 監視ループ起動（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更する場合:
    ```
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - monitor は KABUSYS_ENV に関係なく production の sqlite_path（SQLITE_PATH）を使用します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  デフォルト DB は `data/paper_trading.db`。`--db` で指定可能、または環境変数 `PAPER_TRADING_SQLITE_PATH` を使用。

- AI / レジーム / ニューススコア
  - OpenAI API キーが必要です（OPENAI_API_KEY または引数経由）。
  - これらはライブラリ API（kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime）としてインポートして利用できます。

---

## 運用に関するメモ

- ログ: コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力します。ローテートは最大 30 日分。
- プロセス優先度: 起動スクリプトは最初にプロセス優先度を "high" に設定しようとします（失敗しても継続）。
- Kill Switch: RiskMonitor 等で条件を満たした場合に `data/kill.flag` を生成して ExecutionEngine に停止を促す仕組みがあります。Settings の `KILL_FLAG_CLEAR_ON_START` を確認してください（本番では 0 推奨）。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブル生成・簡易マイグレーションを行います（例: カラム追加）。
- ペーパートレードは本番 DB と完全分離されるよう設計されています。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下にパッケージ化されています。主要ファイル:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (実装参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装参照)
  - execution/
    - execution_engine.py (実装参照)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - research/ (上記)
  - data/ (ランタイムで生成する場所。デフォルト DB・flag・pid など)

注: 一部ファイル（execution 内の細部や alert_manager、trade_monitor 等）はここに抜粋していませんが、該当ディレクトリ内に実装があります。

---

## 開発者向けの補足

- DuckDB 接続を渡すことで、研究用関数群（ファクター計算等）を直接呼び出してユニットテスト可能な設計です。
- AI を利用する処理は外部 API 呼び出しをラップした関数を持ち、テスト時は _call_openai_api をモックして安定化させられます。
- 設定読み込みは .env を自動読み込みしますが、テストや CI で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視ループ・実行エンジン共に `data/stop_requested.flag` を参照して graceful shutdown を行います。運用時はこのフラグファイルの管理ルールを策定してください。

---

## よくある質問（FAQ）

Q: ペーパートレードと本番の DB は混ざりますか？  
A: いいえ。KABUSYS_ENV=paper_trading の場合、`PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）を使用し、本番 SQLite（SQLITE_PATH）は使用しません。ただし monitoring（run_monitoring）は本番の sqlite_path を使用する設計になっています（監視は環境にかかわらず一元管理）。

Q: ログレベルを変えたいです。  
A: 環境変数 `LOG_LEVEL` を設定するか、setup_logging の引数 `level` を使って変更できます。例: `export LOG_LEVEL=DEBUG`。

Q: OpenAI を使いたいが API キーはどこ？  
A: 環境変数 `OPENAI_API_KEY` に設定するか、ai 関数の引数で渡してください。

---

README はプロジェクトの導入・運用の最小限セットをカバーしています。実装の詳細や追加の運用手順（プロセス管理、監視アラート設定、CI/CD、バックアップ方針等）は運用ドキュメントとして別途整備することを推奨します。必要であれば、個別モジュール（例: ExecutionEngine、TradeMonitor、AlertManager）の詳細ドキュメントも作成しますので指示ください。