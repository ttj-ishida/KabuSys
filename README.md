# KabuSys

日本株向けの自動売買 / リサーチ基盤コンポーネント群です。  
本リポジトリはトレーディングエンジン、モニタリング、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント）連携などのユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株自動売買システムのバックエンド的なライブラリ／スクリプト群です。主な目的は以下です。

- シグナル → 注文実行のフロー（ExecutionEngine）
- システム稼働状況・注文状況・リスク監視（Monitoring）
- ポートフォリオ構築・ポジションサイジング（Portfolio）
- ファクター計算・リサーチ（Research） — DuckDB を利用
- ニュースを LLM（OpenAI）で解析してセンチメントを付与（AI）
- ペーパートレード検証レポート生成ツール

設計上の要点:
- 実行スクリプトは .env を利用して設定を読み込む（自動読み込み機能あり）
- PaperTrading モードは本番 DB と分離（`data/paper_trading.db`）
- ログはコンソール + 日次ローテートファイル（`logs/`）へ出力
- OpenAI 連携部分は API キーを要求（障害時はフォールバックする実装あり）

---

## 機能一覧

- run_execution: ExecutionEngine の起動スクリプト（本番 / paper_trading 切替）
  - Paper Trading 時は MockBrokerClient を使用し DB を分離
  - 起動時にプロセス優先度を設定し、PID ファイルを書き込む
  - 停止フラグ（data/stop_requested.flag / data/kill.flag）の検出に対応

- run_monitoring: SystemMonitor のポーリングループ起動スクリプト
  - 環境変数 `MONITOR_POLL_INTERVAL` で間隔を上書き（デフォルト 60s）
  - monitoring 用 SQLite DB を初期化し記録

- monitoring モジュール:
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存 / データ鮮度をチェック
  - TradeMonitor: 発注滞留・約定異常検出（trade_logs 等を参照）
  - RiskMonitor: ドローダウン / ポジション上限監視、dashboard 更新
  - KillSwitch: 条件に合致した場合に `data/kill.flag` を書き込む
  - MonitoringDB: SQLite に対する永続化レイヤ（テーブル作成・マイグレーション含む）

- portfolio モジュール:
  - 候補選定（スコア順）、等重・スコア重み、セクター制限、ポジションサイズ計算（lot 単位・aggregate cap）

- research モジュール:
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（Information Coefficient）、統計サマリ等

- ai モジュール:
  - news_nlp: OpenAI によるニュースのセンチメント付与（ai_scores テーブルへ書込）
  - regime_detector: ETF + マクロニュースを組み合わせて市場レジーム判定して書き込み

- tools:
  - paper_verification_report: ペーパートレード DB を解析して Pass/Fail レポートを標準出力に出力

- 設定・補助ツール:
  - config_setup: 対話式で .env を生成/更新
  - validate_config: .env と config/*.yaml の検証 CLI

---

## セットアップ手順

※ 以下は一般的な手順例です。実行環境（OS, Python バージョン）に応じて調整してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   (requirements.txt があればそれを使う。なければ代表的な依存を個別に)
   ```
   # 例:
   pip install duckdb psutil openai PyYAML
   # 開発で type-check 等あれば追加でインストール
   ```

4. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - 生成される `.env` は決して Git にコミットしないでください（秘密情報を含む）。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. ディレクトリの準備（自動で作られる場合あり）
   - data/ （SQLite や PID / flag ファイル）
   - logs/ （ログファイル）
   必要に応じて手動で作成しても構いません。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 任意 / デフォルト
  - KABUSYS_ENV — 実行環境: development | paper_trading | live (default: development)
  - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（default: data/paper_trading.db）
  - LOG_LEVEL — ログレベル（default: INFO）
  - LOG_DIR — ログ保存ディレクトリ（default: logs/）
  - OPENAI_API_KEY — OpenAI を利用する機能（AI モジュール）に必要
  - PAPER_FILL_MODE — paper_trading の約定動作（instant/partial/never/reject）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、default: 60）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, など

重要: .env の例は `.env.example` を参照して作成してください（存在する場合）。本番環境で `KABUSYS_ENV=live` を使用する際は設定を慎重に確認してください。

---

## 使い方（起動例）

- ExecutionEngine を起動（通常モード）
  ```
  python -m kabusys.run_execution
  ```

- Paper Trading モードで起動（MockBrokerClient を使用）
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- SystemMonitor（ポーリング）を起動
  ```
  # ポーリング間隔を 30 秒にする例
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 設定検証（既述）
  ```
  python -m kabusys.validate_config
  ```

- .env 対話式生成（既述）
  ```
  python -m kabusys.config_setup
  ```

- Paper Trading 検証レポート生成
  ```
  # DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

停止・フラグ操作:
- 実行中のプロセスに対して強制停止させたい場合は、kill switch 用のファイルを書き込みます（例: `data/kill.flag`）。KillSwitch は条件で自動的に書き込むこともあります。
- run_* スクリプトは `data/stop_requested.flag` の存在を検知するとループを抜けて安全に終了します。停止させたい場合はこのファイルを作成してください。

ログ:
- ログは stdout に出力され、かつ `logs/<app_name>.log` に日次ローテーションで保存されます。

注意点（運用上の警告）:
- 本番環境（KABUSYS_ENV=live）で実行する前に validate_config で設定ミスがないか必ず確認してください。
- OpenAI API を使用するモジュールは API キーとコスト管理に注意してください。API 呼び出しでエラーが発生してもフェイルセーフで処理を続ける設計ですが、結果の品質とコストは運用者の責任です。

---

## ディレクトリ構成（主要ファイル説明）

リポジトリの主要なソースツリー（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理、自動 .env 読込
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                  — ニュースを OpenAI でスコアリング、ai_scores に書込み
    - regime_detector.py           — ETF + マクロニュース → レジーム判定
  - monitoring/
    - monitoring_db.py             — SQLite テーブル定義・永続化 API
    - system_monitor.py            — システム状態・データ鮮度チェック
    - trade_monitor.py             — 注文滞留・約定異常チェック（実装参照）
    - risk_monitor.py              — ドローダウン / position-limit チェック
    - kill_switch.py               — Kill Switch（kill.flag 書き込み）
    - monitoring_engine.py         — 各 Monitor を束ねるループ
    - alert_manager.py             — 通知（LINE 等）管理（実装参照）
  - execution/                      — ExecutionEngine / Broker 抽象 / Order 管理（実装参照）
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数計算・aggregate cap 処理
    - risk_adjustment.py           — セクター制限・レジーム乗数
  - research/
    - factor_research.py           — momentum/value/volatility 等の計算（DuckDB）
    - feature_exploration.py       — IC / 統計・将来リターン計算
  - utils/
    - logging_setup.py             — 共通ロギング設定
    - process_priority.py          — プロセス優先度 / CPU affinity 設定
  - data/                           — 実行時生成 / DB / pid / flag を置くことを想定
  - logs/                           — ログファイル（runtime）

（各モジュール内に詳細な docstring があるため、実装/挙動の詳細はソースを参照してください。）

---

## 運用メモ / トラブルシューティング

- SQLite / DuckDB のパスは Settings（環境変数）で変更可能。PaperTrading はデフォルトで `data/paper_trading.db` を使い本番 DB と分離します。
- run_monitoring は monitoring 用 DB（SQLITE_PATH）を環境に関わらず使用します（監視は本番 DB を参照）。
- OpenAI 周りは一部リトライ・バックオフ実装あり。API のレートや料金に注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（ログ設定は堅牢化されています）。
- process_priority の設定は OS に依存し、権限不足で失敗する可能性があります（警告ログを出します）。

---

## 参考コマンドまとめ

- 仮想環境作成・依存インストール
  ```
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML
  ```

- .env 作成
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- 実行（例）
  ```
  python -m kabusys.run_execution
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

この README はコード内の docstring と実装に基づいて作成しています。詳細な挙動や追加オプションは各モジュールの docstring / ソースコードを参照してください。必要であれば、README に含めるコマンド例や環境変数の表をさらに追記できます。