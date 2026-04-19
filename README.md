# KabuSys

日本株向け自動売買システム（ライブラリ/実行スクリプト群）

このリポジトリは、戦略のリサーチ・ポートフォリオ構築・実行エンジン・監視・AI を組み合わせた自動売買システムのコンポーネント群を含みます。モジュール設計で各層が分離されており、ローカル開発／ペーパートレード／本番運用を想定した設定切替が可能です。

## 主な機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの `.env`, `.env.local`）
  - 対話式ウィザードによる `.env` 生成: `config_setup`
  - 設定検証 CLI: `validate_config`（`--strict` オプション）

- 実行エンジン（ExecutionEngine）
  - ブローカークライアント抽象化（本番／ペーパートレード切替）
  - 注文管理・オーダーリポジトリ・リコンシリエーション・リスク管理
  - PID / 停止フラグ連携（data/execution.pid, data/stop_requested.flag）

- 監視（Monitoring）
  - システム（CPU/メモリ/ディスク）、データ鮮度、トレード状況、リスク（ドローダウン・ポジション数）監視
  - Kill Switch（閾値超過時に `data/kill.flag` を書き込み、ExecutionEngine を停止）
  - monitoring DB（SQLite）による履歴保存

- ポートフォリオ構築（純粋関数群）
  - 候補選定、等金額/スコア加重の重み計算
  - セクター上限適用、レジーム乗数、ポジションサイズ計算（単元株丸め・コストバッファ対応）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 特徴量探索：将来リターン、IC（Information Coefficient）、統計サマリ

- AI
  - ニュース NLP（OpenAI）を用いた銘柄センチメントスコアの算出と保存（`ai.score_news`）
  - マクロ＋価格指標を合成した市場レジーム判定（`ai.regime_detector.score_regime`）

- ツール
  - Paper Trading 検証レポート生成スクリプト（`tools/paper_verification_report.py`）

## 必要な外部依存（主なもの）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使用する場合）
- optional: PyYAML（設定検証時の YAML パースが有効になる）

（プロジェクトの pyproject.toml / requirements.txt があればそちらを参照してください）

## セットアップ手順

1. リポジトリをクローン／取得して、Python 仮想環境を作成し有効化します。

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

2. 依存パッケージをインストールします（例）:

   ```bash
   pip install duckdb psutil openai
   ```

   - PyYAML を入れると `validate_config` が config/*.yaml をパースして検証します:
     ```bash
     pip install pyyaml
     ```

3. 初期環境変数（.env）を作成します（対話式ウィザード推奨）:

   ```bash
   python -m kabusys.config_setup
   ```

   ウィザード実行後、`.env` がプロジェクトルートに生成されます。

4. 設定を検証します:

   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ等を確認／作成します。デフォルトパスは `.env` で指定しますが、デフォルト値は以下です:
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - LOG_DIR: logs/
   - PID ファイル: data/execution.pid
   - Kill フラグ: data/kill.flag
   - Stop フラグ: data/stop_requested.flag

   必要に応じて `data/` と `logs/` を作成して権限を確認してください。

## 環境変数（代表）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

便利／推奨:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を使う場合
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH — DB ファイルパス
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先ディレクトリ
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

注意点:
- run_monitoring は KABUSYS_ENV にかかわらず production の sqlite_path（SQLITE_PATH）を使用します。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離します。

## 使い方（代表的な実行コマンド）

- 環境ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- 監視プロセス起動（デーモン等で実行）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更したい場合:
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 実行エンジン起動（ExecutionEngine）
  ```bash
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV に応じてペーパートレード／本番動作が切り替わります。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（Python API）
  - ニュース NLP（銘柄ごとのスコアを書き込む）:
    ```python
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key optional
    score_news(conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")
    ```

## 停止・Kill Switch の扱い

- 停止フラグ（監視または手動停止用）:
  - data/stop_requested.flag — run_monitoring / run_execution の外側で使用され、存在するとループが終了します（起動時に既に存在すると ExecutionEngine を起動しない設計あり）。
  - data/kill.flag — Kill Switch が発動したときに書き込まれるファイル。ExecutionEngine はこのファイルを検知して停止します。`KILL_FLAG_CLEAR_ON_START` を使うと起動時に自動クリアできますが、本番では無効（0）を推奨します。

## ロギング

- 共通ロギングユーティリティ: `kabusys.utils.logging_setup.setup_logging`
  - コンソール（stdout）出力と日次ローテーションファイル出力（logs/<app_name>.log）を設定します。
  - `LOG_DIR` または引数 `log_dir` で出力先を指定できます。
  - ログファイルは日次ローテートで 30 日分保持されます。

## 主要モジュールとディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 操作用ラッパー
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション数監視
    - trade_monitor.py — （trade 関連監視。該当ファイルがあれば）
    - monitoring_engine.py — 監視コンポーネント統合
    - kill_switch.py — Kill Switch ロジック
    - alert_manager.py — （通知送信管理: LINE など）
  - execution/
    - execution_engine.py — ExecutionEngine（セッション管理）
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py — 注文管理
    - order_repository.py — 注文 DB 操作
    - reconciler.py — 注文整合処理
    - risk_manager.py — 実行時リスク管理
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に保存
    - regime_detector.py — マクロ＋価格でレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート

※ 実際のリポジトリには上記以外にも補助モジュール（data パイプライン、strategy 等）が存在します。必要に応じて参照してください。

## 開発者向けメモ / トラブルシューティング

- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を持つディレクトリ）を起点に `.env` / `.env.local` を自動読み込みします。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等に動作します。必要なカラムが無い場合はランタイムで ALTER を行います。

- 権限エラー:
  - ログディレクトリや data ディレクトリへの書き込み権限を確認してください。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

- psutil のアクセス拒否:
  - プロセス優先度や CPU affinity の設定は権限により失敗することがあります（ログに警告が出ますが処理は継続します）。

- OpenAI / 外部 API:
  - AI 関連処理を行う際は `OPENAI_API_KEY` の設定が必要です。API 呼び出しはリトライやフェイルセーフを備えていますが、レート制限や料金に注意してください。

## 参考コマンドまとめ

- 対話式 .env 作成:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- 監視起動:
  ```bash
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```

- 実行エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```

- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

問題や追加ドキュメントが必要であれば、どの部分を詳しく説明するか教えてください（例: ExecutionEngine の構成や AI モジュールのテスト方法など）。