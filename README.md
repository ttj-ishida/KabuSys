# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ README。  
この README はコードベースの説明・セットアップ・簡単な使い方を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群および起動スクリプト群です。  
主な責務は以下の通りです。

- シグナル／ポートフォリオ構築（研究・ポートフォリオモジュール）
- 発注エンジン（ExecutionEngine）とその監視（Monitoring）
- Paper Trading（模擬発注）を本番 DB と分離して運用
- ニュースの NLP スコアリング（OpenAI）を用いた AI モジュール
- 運用に必要なユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード等）

設計上の特徴：
- DuckDB を用いたリサーチ用データ処理
- SQLite を監視ログ / 発注ログに使用（paper_trading は別 DB）
- OpenAI API と連携する箇所（ニュース NLP、レジーム判定）は API キーが必要
- .env による環境設定、対話式ウィザードと設定検証 CLI を提供

---

## 機能一覧

- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading の分離実行（PAPER_TRADING_SQLITE_PATH）
  - ブローカークライアントファクトリ（MockBroker をサポート）
- monitoring
  - System / Trade / Risk の各種モニタ
  - MonitoringEngine による定期ポーリング
  - Kill Switch: リスク条件により `data/kill.flag` を書き込み、Execution を停止
  - monitoring DB 初期化・永続化（SQLite）
- portfolio
  - 候補選定、重み計算（等分・スコア加重）
  - 単元丸め・ポジションサイズ計算
  - セクター上限・レジーム乗数の適用
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）等の探索ツール
- ai
  - ニュース NLP による銘柄別センチメントスコアの算出（OpenAI）
  - マーケットレジーム判定（ma200 + macro sentiment の重み付け）
- tools
  - Paper Trading の検証レポート生成スクリプト
- utils
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- 設定関連
  - 対話式 .env 作成ツール（config_setup.py）
  - 設定検証 CLI（validate_config.py）

---

## 前提条件

- Python 3.9 以上（型ヒントに union | を使用しているため）
- 推奨パッケージ（実行に必要な代表例）
  - duckdb
  - psutil
  - openai
  - pyyaml（config ファイル検証のみ）
- OS: Linux / macOS / Windows（プロセス優先度や CPU affinity の挙動は OS に依存）

依存関係はプロジェクトの requirements.txt を参照してください（無ければ上記パッケージをインストールしてください）。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repository-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   (requirements.txt があれば)
   ```bash
   pip install -r requirements.txt
   ```
   無ければ最低限:
   ```bash
   pip install duckdb psutil openai pyyaml
   ```

4. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   生成後、実行前に設定を検証:
   ```bash
   python -m kabusys.validate_config
   # strict モード: 警告もエラー扱いにする
   python -m kabusys.validate_config --strict
   ```

5. data / logs ディレクトリは多くの箇所で自動生成されますが、必要に応じて作成してください。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - ログ: logs/<app_name>.log（日次ローテート）

---

## 使い方（主要コマンド）

- 実行エンジンを起動（本番 or paper_trading は KABUSYS_ENV に依存）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は data/paper_trading.db（分離）に記録されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - 実行中は PID ファイル（デフォルト data/execution.pid）を出力します。

- 監視プロセスを起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で秒数を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path（デフォルト data/monitoring.db）を使用します。
  - 停止は `data/stop_requested.flag` を作ることで検知します。

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB は `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI モジュール（ニューススコア / レジーム判定）は内部 API を通じて呼び出します。直接呼び出す場合は OPENAI_API_KEY を設定してください。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DB パス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログディレクトリ（デフォルト logs/）
- Paper Trading 動作
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- 監視
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアする (0/1)
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で必須）

注意: .env は Git にコミットしないでください（config_setup は警告を出します）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数読み込み / Settings
  - config_setup.py           # 対話式 .env ウィザード
  - validate_config.py        # 設定検証 CLI
  - run_execution.py          # ExecutionEngine 起動スクリプト
  - run_monitoring.py         # SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - execution/                 # 発注関連コンポーネント（OrderManager, ExecutionEngine 等）
  - data/                      # データ関連（パイプライン / マスタ） — 実装により存在
- config/                      # YAML 設定テンプレート（system_config.yaml 等）
- data/                        # 実行時に生成される SQLite/DuckDB や flag ファイル
- logs/                        # ログファイル（自動生成）

---

## 運用上の注意・トラブルシューティング

- .env の自動ロード
  - .env の自動読み込みはプロジェクトルートの特定に .git または pyproject.toml を使います。CWD に依存しないため、パッケージ化後も動作します。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Kill Switch / stop フラグ
  - `data/kill.flag` は ExecutionEngine に安全停止を指示するために使用します（監視側が書き込みます）。
  - `data/stop_requested.flag` は run_execution / run_monitoring の起動・ループ停止に使われます。

- OpenAI API
  - AI モジュールは OpenAI にアクセスするため `OPENAI_API_KEY` が必要です。キー未設定時は ValueError を投げます。
  - レート制限や一時的なエラーに対してはリトライロジックを持っていますが、ログで失敗を必ず確認してください。

- ログ
  - setup_logging は stdout と日次ローテーションファイル（logs/<app>.log）を設定します。ログディレクトリ作成に失敗するとファイル出力は無効化されます。

- Paper Trading
  - `KABUSYS_ENV=paper_trading` のときは発注はモック実行となり、本番 DB と完全に分離した `PAPER_TRADING_SQLITE_PATH` を使用するようになっています。検証やレポート作成は paper_trading DB を使ってください。

- 依存関係不足
  - validate_config は PyYAML がない場合、config/*.yaml の検証をスキップして警告を出します。
  - DuckDB・psutil 等がないと関連モジュールが動作しません。実行前に必須パッケージを入れてください。

---

## 参考コマンド一覧（まとめ）

- .env 作成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Execution 起動
  ```
  python -m kabusys.run_execution
  ```

- Monitoring 起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

問題報告や改善案の提案がある場合はリポジトリの Issue を作成してください。README の内容は今後の実装拡張に合わせて更新されます。