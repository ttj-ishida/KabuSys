# KabuSys

日本株自動売買システムの一部（ライブラリ／ランナー群）の README。  
この README はリポジトリ内の主要スクリプトとモジュール（実行エンジン、監視、ポートフォリオ構築、リサーチ、AI 補助など）の使い方とセットアップ手順をまとめたものです。

重要: 本プロジェクトは実際に発注を行う機能を含みます。KABUSYS_ENV=live を設定すると実際の売買が行われます。実行前に設定とテストを十分に行ってください。

---

## 概要

KabuSys は日本株の自動売買・運用支援用モジュール群です。主な役割は以下です。

- ExecutionEngine（発注エンジン）を起動して発注処理を実行
- Monitoring（監視）サブシステムでプロセス／データ鮮度／リスク監視、Kill Switch 発動
- Portfolio construction（候補選定、重み付け、ポジションサイズ計算）
- Research（ファクター計算・特徴量探索）
- AI 補助（ニュースのセンチメント評価、レジーム判定）
- CLI ツール（.env ウィザード、設定検証、Paper Trading の検証レポート）

設計方針として、できる限りフェイルセーフ（API失敗時はスキップ／デフォルト値）、ルックアヘッドバイアス回避（date.today() を直接参照しない）、環境分離（Paper Trading 用 DB）などが適用されています。

---

## 主な機能一覧

- 実行（run_execution）
  - 環境により本番 / ペーパートレードを切り替え
  - ブローカークライアントを生成し ExecutionEngine を起動
  - プロセス優先度を「high」にセット（可能な場合）
  - 停止フラグ（data/stop_requested.flag）で安全停止
- 監視（run_monitoring / MonitoringEngine）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MonitoringDB（SQLite）へログ永続化
  - KillSwitch による停止判定（kill.flag 書き込み）
  - アラート通知（LINE 等の設定を利用）
- 環境設定ウィザード（config_setup）
  - 対話式で .env を生成・更新
- 設定検証（validate_config）
  - .env と config/*.yaml の妥当性チェック（--strict オプションあり）
- Paper Trading 検証レポート（tools/paper_verification_report）
  - ペーパートレード DB から稼働率、注文成功率、レイテンシなどを集計してレポート出力
- AI 補助
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores への書き込み）
  - regime_detector: MA200 とマクロセンチメントを組み合わせて市場レジーム判定
- ポートフォリオ構築（portfolio）
  - 候補選定、等比率/スコア重み、セクター制限、リスクベースのポジションサイズ計算
- リサーチ（research）
  - ファクター計算（Momentum/Value/Volatility 等）、将来リターン / IC 計算
- 汎用ユーティリティ（utils）
  - ロギングセットアップ（console + 日次ローテートファイル）
  - プロセス優先度 / CPU Affinity 設定ユーティリティ

---

## 必要条件 / 依存パッケージ

- Python 3.10+
  - （型注釈で `X | Y` を使用しているため 3.10 以降を推奨）
- ランタイム依存（主要）:
  - duckdb
  - psutil
  - openai
  - pyyaml（設定検証の YAML パース用、無くても警告となる）
- SQLite は標準ライブラリで利用

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使ってください）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. .env の作成（対話式ウィザード）
   - 推奨: 対話式で初期設定を生成
   - 実行:
     ```bash
     python -m kabusys.config_setup
     ```
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 注意: KABUSYS_ENV を `live` にすると実際に発注されます。運用時は慎重に。
5. 設定検証
   - 実行:
     ```bash
     python -m kabusys.validate_config
     ```
   - --strict を付けると警告も失敗扱いになります:
     ```bash
     python -m kabusys.validate_config --strict
     ```
6. ログディレクトリ等の確認
   - デフォルトログディレクトリ: logs/
   - ログレベルは LOG_LEVEL 環境変数で制御（デフォルト: INFO）

---

## 実行方法（使い方）

- 実行エンジン（ExecutionEngine）起動
  - デフォルト:
    ```bash
    python -m kabusys.run_execution
    ```
  - 特記事項:
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時にプロセス優先度を high に設定し、PID を data/execution.pid に出力します。
    - data/stop_requested.flag が存在すると起動を行わず終了します。実行中に stop flag が作成されると安全に停止します。

- 監視ループ起動（SystemMonitor ポーリング）
  - デフォルト:
    ```bash
    python -m kabusys.run_monitoring
    ```
  - 環境変数でポーリング間隔を変更:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
    デフォルトは 60 秒。0 以下の値はデフォルトへフォールバックします。
  - 監視は Settings の sqlite_path（data/monitoring.db がデフォルト）を使用します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意。

- Paper Trading 検証レポート生成
  - CLI:
    ```bash
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DB パスを指定する場合:
    ```bash
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
    ```
  - 環境変数 PAPER_TRADING_SQLITE_PATH でデフォルト DB を上書き可（default: data/paper_trading.db）

- AI モジュール（ライブラリ関数）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニューススコアを ai_scores テーブルに書き込む関数（ライブラリ API）。
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを算出して market_regime テーブルへ書き込む（ライブラリ API）。
  - これらはライブラリ関数のため、スクリプトやジョブで DuckDB 接続を用意して呼び出します。

- .env 注意点
  - .env 生成後、`python -m kabusys.validate_config` で検証してください。
  - 本番運用時は KILL_FLAG_CLEAR_ON_START=0（デフォルト推奨）にすることを推奨します。

- Kill / Stop
  - Execution 停止シグナル: data/kill.flag（KillSwitch が作成）
  - 監視・実行の外部停止リクエスト: data/stop_requested.flag（存在するとループを抜ける）
  - 手動でクリアするにはファイルを削除してください（例: rm data/kill.flag）

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB データベースファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject、デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

---

## 注意点・運用上の安全対策

- KABUSYS_ENV=live を設定すると実際に発注されます。必ず設定と ACL を確認してください。
- Monitoring は常に本番 sqlite_path を参照します（監視対象の DB とペーパートレード DB は分離されます）。
- KillSwitch により重大リスク（例: ドローダウン閾値超過）で kill.flag が書き込まれると ExecutionEngine を停止する設計です。kill.flag の自動クリア設定は慎重に行ってください。
- OpenAI API 呼び出しはレート制限や一時障害を考慮してリトライ実装がありますが、APIキーの漏洩やコストには注意してください。
- ログディレクトリが作成できない場合はコンソールログのみとなります。ディレクトリ作成権限を確認してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の src/kabusys 以下を抜粋:

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - config.py                  — Settings / .env 自動ロード / 設定取得ユーティリティ
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロ NLP）
    - __init__.py
  - portfolio/
    - portfolio_builder.py     — 候補選定・等重/スコア重み
    - position_sizing.py       — 株数計算・aggregate cap
    - risk_adjustment.py       — セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — forward returns / IC / summary
    - __init__.py
  - monitoring/
    - monitoring_db.py         — MonitoringDB（SQLite スキーマ・読み書き）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （trade 関連の監視ロジック）
    - risk_monitor.py          — ドローダウン/ポジション上限監視
    - kill_switch.py           — kill.flag 制御ロジック
    - monitoring_engine.py     — Monitor を束ねるポーリングエンジン
    - alert_manager.py         — （アラート送信管理ロジック）
  - utils/
    - logging_setup.py         — ロギングの統一セットアップ
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

（上記は主要ファイルの抜粋です。実装ファイルはさらに細かく分かれています。）

---

## 開発者向けメモ

- モジュールはできるだけ純粋関数や副作用の少ない設計を意識しています（例: portfolio モジュールは DB を参照しない）。
- DuckDB 接続を受け取る研究 / AI モジュールは CLI ではなくライブラリ関数として提供されており、バッチジョブや Airflow / cron 等から呼び出して利用する想定です。
- 監視ログは SQLite（monitoring.db）に永続化されます。schema は monitoring_db.init_monitoring_db で冪等に作成されます。
- ログは stdout と日次ローテートファイル（logs/<app_name>.log）に出力されます。ログ保持は 30 日。

---

必要に応じて README をプロジェクト固有のセットアップ手順や運用チェックリスト（デプロイ手順、監視の閾値、LINE 通知設定方法など）で拡張します。追加で記載したい運用手順やサンプル .env のテンプレートがあれば教えてください。