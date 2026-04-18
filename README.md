# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README。  
このドキュメントはリポジトリ内の主要スクリプト・モジュールと、セットアップ・実行方法をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。以下の主要機能を備え、運用・検証・研究の各フェーズに対応します。

- ExecutionEngine：発注／注文管理／リスク管理を行う実行基盤（本番・ペーパートレード対応）
- Monitoring：システム状態・注文・リスクを定期的に監視し、アラートや Kill Switch を管理
- Portfolio Construction：銘柄選定・重み付け・ポジションサイズ計算の純粋関数群
- Research：DuckDB を用いたファクター計算、特徴量解析
- AI（OpenAI 統合）：ニュースセンチメントや市場レジーム判定（OpenAI API 使用）
- ユーティリティ：ログ設定、プロセス優先度設定、設定ウィザード/検証スクリプト 等

設計方針の一部：
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV により切り替え）
- DuckDB は分析用（prices_daily / raw_financials 等を参照）
- LLM（OpenAI）呼び出しはリトライ/バックオフ・レスポンス検証を実装

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
  - PID ファイル管理、停止フラグ監視（data/stop_requested.flag）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL で間隔を上書き可能
  - Monitoring は環境にかかわらず本番 sqlite_path を参照
- config_setup.py
  - .env を対話式に作成・更新するウィザード
- validate_config.py
  - .env および config/*.yaml の基本検証（--strict で警告も FAIL）
- tools/paper_verification_report.py
  - ペーパートレード結果の検証レポート生成（稼働率・注文成功率・レイテンシ等）
- ai.news_nlp / ai.regime_detector
  - OpenAI を用いたニュースセンチメント算出・市場レジーム判定
- portfolio.*
  - 候補選定、重み算出、セクターキャップ適用、ポジションサイズ計算
- research.*
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）、IC 計算、統計サマリ
- monitoring.*
  - MonitoringDB（SQLite）、System/Trade/Risk Monitor、KillSwitch、Alert 管理

---

## セットアップ手順

前提
- Python 3.10+（typing 表記やライブラリに依存）
- 必要な外部ライブラリ（例: duckdb, psutil, openai, PyYAML（任意））をインストール

1. リポジトリをクローンして仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール（requirements.txt がある場合はそれを使用）
   ```bash
   pip install duckdb psutil openai
   # PyYAML を入れると validate_config で YAML を検証できます
   pip install PyYAML
   ```

3. 環境変数設定（.env を用意）
   - 対話式ウィザードで簡単に作成できます:
     ```bash
     python -m kabusys.config_setup
     ```
   - 主要な環境変数（デフォルト値はコード内に記載）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - OPENAI_API_KEY — OpenAI を利用する場合必須
     - LOG_LEVEL — デフォルト: INFO
     - LOG_DIR — デフォルト: logs/
     - PAPER_FILL_MODE — ペーパートレードの執行モード（instant|partial|never|reject）

4. 設定検証（任意）
   ```bash
   python -m kabusys.validate_config
   # 警告を厳格扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

---

## 使い方

- 実行エンジン（ExecutionEngine）起動
  - デフォルト（.env の KABUSYS_ENV によって本番/ペーパー分岐）
  ```bash
  python -m kabusys.run_execution
  ```
  - 停止方法
    - data/stop_requested.flag を作成するとループが検知して安全終了します
    - Kill Switch（監視が criteria により書き込む）: data/kill.flag が作成されると ExecutionEngine は停止対象となる

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定（デフォルト 60 秒）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- .env 作成（対話ウィザード）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```bash
  # デフォルト DB を使用
  python -m kabusys.tools.paper_verification_report
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（プログラム的に呼び出す例）
  - news_nlp.score_news(conn, target_date, api_key=...) — raw_news を解析して ai_scores に書き込み
  - ai.regime_detector.score_regime(conn, target_date, api_key=...) — market_regime に書き込み
  - いずれも OPENAI_API_KEY が必要（api_key を直接渡すことも可能）

ログ
- ログ出力は kabusys.utils.logging_setup.setup_logging により統一管理
- デフォルトは stdout と logs/<app_name>.log（日次ローテート、30日保持）

停止・PID
- 実行用 PID ファイル: data/execution.pid（Settings.pid_file_path で参照）
- 停止フラグ: data/stop_requested.flag
- Kill Switch フラグ: data/kill.flag

---

## 環境変数（主要）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用 DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用 DB）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）（デフォルト 60）
- PAPER_FILL_MODE: instant|partial|never|reject（ペーパートレードの約定挙動）

---

## ディレクトリ構成（抜粋）

以下はこの README 作成時点での主なファイル構成の抜粋です。

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ config_setup.py
   ├─ validate_config.py
   ├─ run_execution.py
   ├─ run_monitoring.py
   ├─ utils/
   │   ├─ __init__.py
   │   ├─ logging_setup.py
   │   └─ process_priority.py
   ├─ monitoring/
   │   ├─ monitoring_db.py
   │   ├─ system_monitor.py
   │   ├─ trade_monitor.py          # (存在を想定するモジュール)
   │   ├─ risk_monitor.py
   │   ├─ monitoring_engine.py
   │   └─ kill_switch.py
   ├─ execution/
   │   ├─ execution_engine.py      # (存在を想定するモジュール)
   │   ├─ order_manager.py
   │   ├─ order_repository.py
   │   └─ broker_factory.py
   ├─ portfolio/
   │   ├─ __init__.py
   │   ├─ portfolio_builder.py
   │   ├─ position_sizing.py
   │   └─ risk_adjustment.py
   ├─ research/
   │   ├─ __init__.py
   │   ├─ factor_research.py
   │   └─ feature_exploration.py
   ├─ ai/
   │   ├─ __init__.py
   │   ├─ news_nlp.py
   │   └─ regime_detector.py
   └─ tools/
       ├─ __init__.py
       └─ paper_verification_report.py
```

（注）上記は主要ファイルの抜粋です。実行エンジンやブローカークライアントなどのモジュールはさらに細分化されています。

---

## 運用上の注意

- 本番運用時は KABUSYS_ENV=live を設定し、環境変数や鍵情報の管理に注意してください。validate_config によりいくつかの安全チェックが可能です。
- Kill Switch（data/kill.flag）の自動クリアは危険です。本番では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- OpenAI API を利用する機能は API キー管理とコストに注意してください。API 呼び出しはリトライ／バックオフのロジックを備えていますが、失敗時はフェイルセーフ（スコア 0 等）で継続します。
- DuckDB / SQLite のファイルは適切なバックアップ・権限設定を行ってください。
- ログディレクトリへの書き込み権限がない場合、ファイルハンドラは無効化されコンソール出力のみになります（警告が出ます）。

---

もし README に追記してほしい項目（例: デプロイ手順、ユニットテスト実行方法、より詳細な設定例など）があれば教えてください。