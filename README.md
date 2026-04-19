# KabuSys

日本株向け自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、シグナル生成 → ポートフォリオ構築 → 発注実行、並びに運用監視・レポート生成までを含む自動売買基盤の一部実装です。研究用のファクター計算や AI を使ったニュースセンチメント評価のコンポーネントも含みます。

---

## プロジェクト概要

- 名前: KabuSys
- 目的: 日本株の自動売買を行うためのモジュール群（戦略・発注・監視・レポート・研究ツール等）
- 設計方針:
  - モジュール化（monitoring / execution / portfolio / research / ai / utils / tools 等）
  - 本番データベースとペーパートレードデータを分離
  - ロギング・監視・Kill Switch による安全運用
  - DuckDB を用いた分析、SQLite を用いた監視とトランザクションログ
  - OpenAI を利用したニュース NLP（オプション）

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine（run_execution.py）: 発注処理の実行ループ（paper_trading モードでは MockBroker を使用）
  - Order 管理、リスク管理、リコンシリエーション等のコンポーネント群（execution パッケージ）

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine（run_monitoring.py）
  - 監視結果は SQLite に永続化（monitoring/monitoring_db.py）
  - Kill Switch（data/kill.flag）と停止フラグ（data/stop_requested.flag）による安全停止

- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算、ポジションサイジング、セクター制限等の純関数群（portfolio パッケージ）

- 研究（Research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ（research パッケージ）
  - DuckDB 上の prices_daily / raw_financials を参照して計算

- AI（任意）
  - ニュースの NLP によるセンチメントスコアリング（ai/news_nlp.py）
  - マクロ + ETF MA を組み合わせた市場レジーム判定（ai/regime_detector.py）
  - OpenAI API（gpt-4o-mini 等）を利用（API キー必須）

- ユーティリティ
  - ロギング設定（utils/logging_setup.py）
  - プロセス優先度設定 / CPU affinity（utils/process_priority.py）
  - .env ウィザード（config_setup.py）、設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

---

## 前提条件 / 推奨環境

- Python 3.10 以上（ソース内での型注釈や union 型 `X | Y` を使用）
- 動作に必要な主要パッケージ（例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config.py の YAML 検証を有効にする場合）

例: 必要なパッケージをインストールする（環境に合わせて適宜調整してください）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成してアクティベート（任意）

3. 必要パッケージをインストール（上記参照）

4. 環境変数（.env）を作成
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env を生成・更新します。生成後は必ず `python -m kabusys.validate_config` で検証してください。

   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能利用時に必須）
   - その他の設定（例）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL, LOG_DIR, etc.

5. データディレクトリ（data/）や logs/ は起動スクリプトで自動作成されますが、権限に注意してください。

6. 設定検証
   ```
   python -m kabusys.validate_config
   # strict モード（警告も失敗扱い）
   python -m kabusys.validate_config --strict
   ```

---

## 使い方（主要コマンド）

- 監視プロセスを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
  - run_monitoring は KABUSYS_ENV に関わらず production の sqlite_path（Settings.sqlite_path）を使用します。
  - 停止要求はリポジトリルートの data/stop_requested.flag ファイルを作成すると検知して終了します。

- 実行エンジン（Execution）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録します（本番 DB と分離）。
  - 停止は data/stop_requested.flag を作成するか、Kill Switch（data/kill.flag）で停止します。
  - 実行時に PID ファイル（デフォルト data/execution.pid）が書き出されます。

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB パスは env PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。
  - 出力は標準出力にテキスト形式のレポート。

- AI / ツール用関数
  - AI 系の関数（kabusys.ai.score_news, score_regime 等）は Python API として提供。使用時は OPENAI_API_KEY が必要。

---

## 重要ファイル・フラグ

- data/kill.flag
  - KillSwitch が書き込むファイル。存在すると ExecutionEngine に停止シグナルを与えます。
- data/stop_requested.flag
  - 手動で作成すると run_monitoring/run_execution が検知して停止します。
- data/execution.pid
  - run_execution が PID を書き込むファイル。
- logs/<app>.log
  - 日次ローテートで保存（utils/logging_setup.py による）。

---

## ディレクトリ構成（主要箇所）

- src/kabusys/
  - __init__.py (パッケージ初期化)
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロードロジック含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — 監視ループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores テーブルへ書き込み
    - regime_detector.py — マクロ + ETF MA を使ったレジーム判定

  - monitoring/
    - monitoring_db.py — SQLite ベースの監視データ層（テーブル作成・CRUD）
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス監視
    - trade_monitor.py — （注文系監視、実装あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch ロジック
    - monitoring_engine.py — 複数 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信の管理、実装あり）

  - execution/
    - execution_engine.py — ExecutionEngine 本体（発注ループ）
    - broker_factory.py — ブローカークライアント生成（実ブローカ／Mock）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注周りの実装

  - portfolio/
    - portfolio_builder.py — 候補選定・スコア整列
    - position_sizing.py — 株数計算・資金配分ロジック
    - risk_adjustment.py — セクター制限・レジーム乗数

  - research/
    - factor_research.py — momentum / volatility / value ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリーなど

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

  - utils/
    - logging_setup.py — 統一ログ設定（console + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用関連 / 任意:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - OPENAI_API_KEY — AI 機能で必須
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト data/paper_trading.db
  - LOG_LEVEL — デフォルト INFO
  - LOG_DIR — デフォルト logs/
  - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring）
  - PAPER_FILL_MODE — paper_trading 時の約定挙動（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

詳細は `src/kabusys/config.py` の Settings クラスを参照してください。

---

## 運用上の注意 / トラブルシューティング

- validate_config で起動前に設定ミスを検出してください（本番では --strict 推奨）。
- OpenAI 関連機能は API キーとネットワークに依存し、API の失敗はフェイルセーフでスキップする実装になっていますが、キー未設定だと例外になります。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（警告が出ます）。
- run_execution / run_monitoring は停止フラグ（data/stop_requested.flag）をチェックします。長時間テスト時はこのファイルを活用してください。
- ペーパートレード時は DB を完全分離しておくことで本番資金への影響を避けます（PAPER_TRADING_SQLITE_PATH を利用）。

---

## 参考コマンドまとめ

- .env 生成（ウィザード）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視開始
  ```
  python -m kabusys.run_monitoring
  # 例: ポーリング間隔を 30 秒にする
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 実行エンジン開始
  ```
  python -m kabusys.run_execution
  # ペーパートレードで起動
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

もし README に追記したい項目（例: requirements.txt、CI 設定、より詳細なデプロイ手順、Dockerfile 例など）があれば教えてください。必要に応じてサンプル .env テンプレートや systemd / supervisor 用のサービス定義例も作成できます。