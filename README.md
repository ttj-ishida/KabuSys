# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコア実装です。  
監視（Monitoring）、実行（Execution）、ポートフォリオ構築、リサーチ、AI ベースのニュース解析などのコンポーネントを含みます。

- パッケージルート: `src/kabusys`
- バージョン: `0.1.0`（`kabusys.__version__`）

---

## 概要

KabuSys は以下を目的とするモジュール群で構成されています。

- ExecutionEngine：発注ロジック、注文管理、リスク管理、決済などを実行
- Monitoring：システム状態・取引状態・リスク（ドローダウン等）を継続監視し、必要なら Kill Switch を起動
- Portfolio：銘柄選定、重み付け、株数決定、セクター制約などの純関数群
- Research：ファクター計算、将来リターンやIC計算、統計サマリー
- AI：ニュースのセンチメント解析（OpenAI）や市場レジーム判定
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト
- 設定管理：`.env`の読み込み・ウィザード・検証ツール

設計方針の一部：
- DuckDB / SQLite を用いたローカル DB ベースのデータ処理
- 本番（live）／ペーパー（paper_trading）／開発（development）を環境変数で切替
- LLM 呼び出しは外部 API（OpenAI）を使用（APIキー必須）
- フェイルセーフ設計：API失敗時は安全側にフォールバックする箇所が多数

---

## 主な機能一覧

- 監視（monitoring）
  - CPU / メモリ / ディスク使用率の記録
  - Execution プロセスの生存チェック（PID ファイル）
  - データ鮮度チェック（DuckDB 上の価格データ）
  - 滞留注文・約定異常・ドローダウン等の検出とログ化
  - Kill Switch（`data/kill.flag`）発行による実行エンジン停止トリガ
  - アラート送信基盤（LINE 等への通知は設定次第）

- 実行（execution）
  - ブローカークライアント抽象化（実装に応じて実取引 or モック）
  - OrderManager / Reconciler / RiskManager を組み合わせた実行エンジン
  - Paper Trading モードでは MockBrokerClient を利用し `data/paper_trading.db` に分離記録

- ポートフォリオ構築（portfolio）
  - 候補選定、等加重・スコア加重の重み算出
  - セクター上限適用、レジーム乗数、ポジションサイジング（ロット丸め・aggregate cap）

- リサーチ（research）
  - Momentum / Volatility / Value 等のファクター算出（DuckDB を直接参照）
  - 将来リターン、IC（スピアマン）や統計サマリー

- AI（ai）
  - ニュースを LLM（gpt-4o-mini 等）でスコア化して `ai_scores` に書き込み
  - マクロニュース + ETF MA200 の組合せで市場レジーム（bull/neutral/bear）判定

- ツール
  - `.env` 対話式ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - Paper Trading 検証レポート生成（`tools/paper_verification_report.py`）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンしてパッケージをインストール
   - 推奨: 仮想環境（venv / conda）を使用
   - 例:
     ```bash
     git clone <repo-url>
     cd <repo-root>
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     pip install -e ".[dev]"  # ※requirements ファイルがない場合は個別にインストール
     ```
   - 必要パッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML の検証に使用、オプション）
     - その他テスト用に pytest 等

2. .env の作成
   - 対話式ウィザードで生成:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参考に手動で `.`env` を作成
   - 自動ロードはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）

3. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

4. DB 初期化
   - スクリプト起動時に必要テーブルは自動作成されます（`monitoring_db.init_monitoring_db` が冪等に実行）

---

## 主要な環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト `development`
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（AI 機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト `INFO`）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト `60`）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject、デフォルト `instant`）
- KILL_FLAG_CLEAR_ON_START: 起動時に `data/kill.flag` を自動クリア（`1` で有効、開発用）

---

## 使い方（起動・主要コマンド）

- 監視ループを起動
  - 環境変数でポーリング間隔をオーバーライドできます（秒）。
  - 例:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 補足:
    - 監視プロセスは Settings を読み、SQLite（`SQLITE_PATH`）と DuckDB に接続します。
    - 監視は `data/stop_requested.flag` が作られると終了します（開発用の停止フラグ）。

- 実行エンジンを起動
  - Paper Trading モードでは `KABUSYS_ENV=paper_trading` をセットすると MockBrokerClient と分離 DB（`data/paper_trading.db`）を使用します。
  - 例:
    ```bash
    # ペーパートレード
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution

    # 本番（注意して使用）
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - 補足:
    - 起動時に `data/stop_requested.flag` が既に存在する場合は起動せず終了します。
    - 実行中は `data/execution.pid`（PIDファイル）を使用します。
    - `data/kill.flag` が書き込まれると ExecutionEngine 側で停止処理が走ります（Kill Switch）。

- .env ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（SQLite を参照）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- ログ
  - ログは `kabusys.utils.logging_setup.setup_logging` により標準出力とファイル出力（`logs/<app_name>.log`、日次ローテーション）に送られます。

---

## Kill Switch / 停止フラグ

- Kill Switch：
  - `KillSwitch` は `data/kill.flag` を書き込むことで ExecutionEngine に停止命令を出します。
  - 書き込みは冪等（既にファイルがある場合は上書きしません）。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると ExecutionEngine 起動時に kill.flag を自動クリアします（本番では推奨しません）。

- 停止フラグ（開発用）：
  - `data/stop_requested.flag` が存在すると `run_monitoring.py` や `run_execution.py` のループが安全に停止します。

---

## ディレクトリ構成（主要ファイル・説明）

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン定義
  - config.py — 環境変数 / 設定読み込みロジック（`.env` 自動読み込み、Settings クラス）
  - config_setup.py — .env 対話型ウィザード
  - validate_config.py — 起動前の設定チェック CLI
  - run_monitoring.py — SystemMonitor のポーリングループ開始スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — 統一的なログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite テーブル初期化 / 永続化ヘルパ
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py —（取引監視ロジック、ファイル内にある想定）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag を書き込む Kill Switch 実装
    - monitoring_engine.py — 各 Monitor を結合してポーリングするエンジン
    - alert_manager.py —（アラート送信ロジック、ファイル内にある想定）
  - execution/
    - execution_engine.py — ExecutionEngine 本体（スレッド実行、run_session 等）
    - broker_factory.py — ブローカークライアント生成ファクトリ
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注管理関連
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数決定・集約キャップ
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュースを LLM でスコア化して ai_scores に書き込み
    - regime_detector.py — 簡易マクロ + ETF 指標でレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

（注）一部ファイルはここに抜粋されていない補助モジュールや実装が想定されます。実際のリポジトリ全体を参照してください。

---

## 開発者向けメモ / 注意点

- `.env` は絶対にリポジトリにコミットしないでください（機密情報含む）。
- 自動で `.env` を読み込む処理が `config.py` にあります。テスト等で自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading モードは本番 DB と完全分離する設計になっています（`PAPER_TRADING_SQLITE_PATH`）。
- OpenAI を使う機能（news_nlp/regime_detector）は API キーが必須です。API 呼び出しは耐障害性（リトライ・フォールバック）を組み込んでありますが、コストやレート制限に注意してください。
- ログディレクトリ作成や PID 書き込みなど OS 権限に依存する操作があります。権限不足時はファイル出力が抑制されることがあります（ログは stdout にフォールバック）。

---

## よくある操作例

- 監視をデーモン的に起動してログをファイルに残す（systemd / supervisor 推奨）
- ExecutionEngine を単発で起動してデバッグする（`KABUSYS_ENV=development`）
- Paper Trading の履歴で検証レポートを作成
- `.env` を更新したら `python -m kabusys.validate_config` で問題ないか確認

---

必要であれば、起動スクリプトの systemd ユニット例、開発用 docker-compose、テストの書き方（mock を使った OpenAI・ブローカーの差替え）などの追加ドキュメントを作成します。どの情報を優先して追加しますか？