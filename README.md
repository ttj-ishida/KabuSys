# KabuSys

日本株向けの自動売買システムのコアライブラリ群（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助など）。  
このリポジトリは実運用を意識した設計になっており、実行時のプロセス優先度設定、ログローテーション、監視・Kill Switch、ペーパートレード用の DB 分離などの機能を備えています。

バージョン: 0.1.0

---

## 概要

主な役割

- ExecutionEngine: 発注・注文管理・リスク管理を行う実行エンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働状況・注文状況・リスクを定期的にチェックしてログ・アラート・Kill Switch を管理
- Portfolio: 候補選定、重み付け、ポジションサイジング等のポートフォリオ構築ロジック（純粋関数）
- Research: ファクター計算・将来リターン・IC等の解析ユーティリティ（DuckDB ベース）
- AI: ニュース NLP によるセンチメントスコアや市場レジーム判定（OpenAI API を利用）
- Tools: 解析・運用ユーティリティ（Paper Trading 検証レポート等）
- Utils: ロギング設定、プロセス優先度設定など運用向けユーティリティ

設計方針のポイント

- 環境変数 / .env による設定管理（Settings クラス）
- Paper trading と Live を DB レベルで分離（PAPER_TRADING_SQLITE_PATH）
- ルックアヘッドバイアスを避ける設計（target_date 明示など）
- フェイルセーフ（API 失敗時はスキップ / デフォルト値で継続）
- ログは stdout と日次ローテーションファイルへ出力

---

## 機能一覧

- 実行（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカー抽象化（MockBroker をペーパートレードで使用）
  - リスク管理（max position、max utilization、drawdown 等）
  - PID ファイル管理・停止フラグ検出（data/stop_requested.flag）

- 監視（run_monitoring.py, monitoring/*）
  - CPU / メモリ / ディスク / プロセス稼働の定期ログ化
  - データ鮮度チェック（DuckDB の prices_daily 参照）
  - TradeMonitor / RiskMonitor による注文滞留・約定異常・ドローダウン監視
  - KillSwitch による停止シグナル生成（data/kill.flag）
  - MONITOR_POLL_INTERVAL によるポーリング間隔制御

- ポートフォリオ（portfolio/*）
  - 候補選定、等重・スコア重み、セクターキャップ、レジーム乗数、ポジションサイジング（単元株丸め、aggregate cap）

- リサーチ（research/*）
  - Momentum, Volatility, Value ファクター計算（DuckDB）
  - forward returns, IC（スピアマンランク相関）、統計サマリー

- AI（ai/*）
  - ニュースを OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書き込む（news_nlp.score_news）
  - マクロニュース + ETF MA200 を合成した市場レジーム判定（regime_detector.score_regime）
  - OpenAI API のリトライ / バリデーション・クリップ処理を実装

- ツール
  - 環境設定ウィザード（kabusys.config_setup）：.env の対話式生成
  - 設定検証 CLI（kabusys.validate_config）：必須 env / config YAML / DB パス 等のチェック
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

- ユーティリティ
  - 統一的なログ設定（logs/<app>.log、日次ローテーション）
  - プロセス優先度と CPU affinity 設定（psutil 利用）

---

## 必要条件

- Python 3.10+
- SQLite (Python 標準ライブラリ)
- 推奨インストールパッケージ（主要なもの）
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML （validate_config の YAML 検証を利用する場合）

例（最小）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実運用では requirements.txt を用意して pip install -r で管理してください。

---

## セットアップ手順（開発 / 運用）

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境作成・依存パッケージインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb psutil openai PyYAML
   ```

3. ディレクトリ作成（必要なら）
   ```
   mkdir -p data logs
   ```

4. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは手動で .env を作成（重要なキー）
     - 必須:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     - よく使う設定（デフォルトあり）
       - KABUSYS_ENV (development | paper_trading | live) — default: development
       - DUCKDB_PATH — default: data/kabusys.duckdb
       - SQLITE_PATH — default: data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
       - LOG_LEVEL — default: INFO
       - OPENAI_API_KEY — AI 機能利用時に必須
       - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアする場合は 1

   ※ .env は決して Git にコミットしないでください。

5. 設定検証（必須項目やパス等のチェック）
   ```
   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. （ペーパートレードを使う場合）KABUSYS_ENV を paper_trading に設定してください。ペーパートレードは mock ブローカーを使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に保存されます。

---

## 基本的な使い方

- 実行エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  動作:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid を生成します。停止は data/stop_requested.flag を作成するか ExecutionEngine 側から停止されます。

- 監視ループ（SystemMonitor）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  動作:
  - デフォルト 60 秒間隔でポーリング（環境変数 MONITOR_POLL_INTERVAL で秒数を変更可能）
  - 監視結果は Settings.sqlite_path（監視用 SQLite）に永続化されます（monitoring は環境に関わらず本番 sqlite_path を使用）。
  - 監視プロセスは data/stop_requested.flag の存在をチェックして終了します。

  例: 30 秒間隔に変更して起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / リサーチ機能の呼び出し（プログラム的に）
  - ニュースセンチメントをスコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  - DuckDB 接続は Settings.duckdb_path を使って接続してください。

---

## 主要環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用 / 動作制御
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
  - LOG_DIR: ログの保存ディレクトリ（デフォルト: logs/）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（1/0）

---

## 運用上の注意 / ベストプラクティス

- .env は決してリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）では validate_config を事前実行して設定を確認してください。
- KILL フラグ（data/kill.flag）は本番停止に直結します。KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に自動クリアされますが、本番では 0 を推奨します。
- 監視は monitoring.db に記録しますが、ExecutionEngine は paper_trading 時に別 DB（paper_trading.db）に分離して利用します。これにより本番 DB を壊さないように設計されています。
- OpenAI API を使う機能は API コストとレイテンシを考慮して運用してください。API キーは安全に管理してください。
- ログは stdout と logs/<app>.log（日次ローテーション）に出力されます。運用時はログローテーションとディスク容量管理を確認してください。
- プロセス優先度設定は psutil の権限が必要な場合があります（特に Windows/Linux の nice 値設定）。アクセス権限がない場合は警告ログを確認してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
  - config_setup.py              — 対話式 .env ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート CLI
  - ai/
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI 連携）
    - regime_detector.py         — 市場レジーム判定（MA + マクロ NLP）
    - __init__.py
  - monitoring/
    - monitoring_db.py           — 監視用 SQLite 永続化層
    - system_monitor.py          — システム・データ鮮度監視
    - trade_monitor.py           — 注文関連監視（滞留・異常）
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag の生成 / 管理
    - monitoring_engine.py       — 各 Monitor を束ねるエンジン
    - alert_manager.py           — （アラート送信ロジック）
  - execution/
    - execution_engine.py        — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - broker_factory.py
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
  - utils/
    - logging_setup.py           — ログ設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity 設定
    - __init__.py

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## よく使うコマンドまとめ

- .env の対話式作成:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```

- 監視起動（ポーリング）:
  ```
  python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はプロジェクトの主要点をまとめたサマリです。個々のモジュールや関数には詳細な docstring が含まれているため、実装や使い方の詳細はソースコードの docstring を参照してください。必要であれば、サンプル設定ファイル（.env.example）や運用手順書を別途作成することを推奨します。