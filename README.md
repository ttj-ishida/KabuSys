# KabuSys

日本株自動売買システムの一部を実装した Python パッケージです。  
このリポジトリには、監視・実行・リサーチ・ポートフォリオ構築・AI（ニュースセンチメント）などの主要コンポーネントが含まれます。

---

## 概要

KabuSys は次のような責務を持つモジュール群で構成されています（抜粋）:

- ExecutionEngine（発注エンジン）: ブローカークライアント経由で注文を実行・管理します。  
  KABUSYS_ENV=`paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の DB に分離して記録します。
- Monitoring（監視）: システム稼働状況、データ鮮度、取引ログの監視、Kill Switch（停止フラグ）判定を行います。
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースセンチメント評価・市場レジーム判定のユーティリティを提供します。
- Research: DuckDB 上の株価・財務データからファクター計算や統計解析を行うモジュール群。
- Portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター上限などのポートフォリオ構築ロジック。
- Tools: ペーパートレードの検証レポート生成などのユーティリティスクリプト。
- Utils: ロギング設定、プロセス優先度設定など実行環境向けユーティリティ。

パッケージルート: `src/kabusys`（モジュールはこの下に配置）

---

## 主な機能一覧

- 環境設定ウィザード（.env の生成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml の事前チェック）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`（KABUSYS_ENV に応じて本番 / ペーパー分離）
- Monitoring 起動スクリプト（ポーリング監視）: `kabusys.run_monitoring`
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能（デフォルト 60 秒）
- Kill Switch: しきい値超過時に `data/kill.flag` を生成して ExecutionEngine に停止シグナルを送出
- Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`
- AI モジュール:
  - `kabusys.ai.news_nlp.score_news` — raw_news を集約して OpenAI でセンチメント評価し `ai_scores` に保存
  - `kabusys.ai.regime_detector.score_regime` — ETF とマクロニュースを組合せて市場レジーム判定
- Research / Factor 計算（DuckDB ベースの純関数群）: momentum, volatility, value 等
- Portfolio 構築（候補選定・重み付け・position sizing・リスク調整）: 等重み / スコア重み / リスクベース等
- ロギング設定: 日次ローテートのファイル出力・コンソール出力を統一するユーティリティ
- プロセス優先度／CPU affinity 設定（psutil を利用）

---

## セットアップ手順（開発 / ローカル実行向け）

以下は一般的なセットアップ手順です。実際の依存関係ファイル（requirements.txt 等）がある場合はそちらを優先してください。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows (PowerShell 等)
   ```

3. 必要なパッケージをインストール  
   推奨パッケージ（コードから参照される主なライブラリ）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config ファイル検証を行う場合）
   - そのほか、独自のブローカークライアントや DB ライブラリ等

   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数 / .env の準備  
   対話式ウィザードで .env を生成できます:
   ```
   python -m kabusys.config_setup
   ```
   もしくは `.env` を手動作成してください。主に必要な環境変数は下記参照。

5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告も厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```

6. DB 初期化  
   実行スクリプトは起動時に必要テーブルを作成します（例: sqlite に対する `init_monitoring_db` が呼ばれます）。DuckDB / SQLite のファイルパスは .env の設定に従います（デフォルトを使用する場合は自動で `data/` 以下に生成されます）。

---

## 環境変数（主なもの）

多くは `.env` で設定します。主なキーとデフォルト / 有効値:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

任意 / デフォルトあり
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードのフィルモード（instant | partial | never | reject） デフォルト: instant
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に既存 kill.flag を自動クリアするか（0/1、デフォルト: 0）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- PID_FILE_PATH — ExecutionEngine が書き込む PID ファイルのパス（デフォルト: data/execution.pid）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）

注意: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動的な .env 読み込みを抑制できます（テスト等で利用）。

---

## 使い方（主要スクリプト・コマンド）

- 環境設定ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 通常:
    ```
    python -m kabusys.run_execution
    ```
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して `data/paper_trading.db` に記録（本番 DB と分離）
    - 起動時に `data/stop_requested.flag` が存在すると起動しない
    - 実行中に `data/stop_requested.flag` を作成するとエンジンが停止する仕組み

- Monitoring 起動（監視ループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` でオーバーライド可能（秒、デフォルト 60）
  - 停止フラグ: プロジェクトルート `data/stop_requested.flag` を検知するとループを終了する
  - 監視は常に本番用の sqlite_path（`Settings.sqlite_path`）を使います

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `PAPER_TRADING_SQLITE_PATH` 又は `--db` オプションで指定

- AI / リサーチなどはパッケージの API をインポートして利用します（例: `kabusys.ai.news_nlp.score_news`、`kabusys.research.calc_momentum` など）。OpenAI を使う機能は `OPENAI_API_KEY` の設定が必要です。

---

## ログ・ファイル

- ログ:
  - デフォルトで `logs/<app_name>.log` に日次ローテートで出力されます（保管日数 30 日）。
  - コンソール出力は stdout（stderr ではない）に流れます。
- フラグ / PID:
  - 停止フラグ: data/stop_requested.flag （run_monitoring / run_execution がチェック）
  - Kill Switch: data/kill.flag（KillSwitch が作成）
  - Execution PID: data/execution.pid（ExecutionEngine が使用）

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なファイル・モジュールの一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動ロード機能を含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動
  - utils/
    - logging_setup.py — 統一ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 抽象（テーブル初期化 / ログ保存）
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 取引ログ監視（滞留注文・約定異常等）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の評価 / 書き込み
    - monitoring_engine.py — モニター群を束ねるエンジン
    - alert_manager.py —（アラート送信機能、コード内で参照）
  - execution/ (発注系コンポーネント、OrderManager など)
  - data/ (データパイプライン周り、DuckDB API 参照)
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・キャップ処理
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し・バッチ処理・バリデーション）
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポートジェネレータ

（実際のリポジトリには上記以外の補助モジュールや詳細実装が含まれます）

---

## 運用上の注意 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では .env の設定、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）などを慎重に確認してください。validate_config は本番ガードを含みます。
- Kill Switch（data/kill.flag）は本番での緊急停止手段です。KILL_FLAG_CLEAR_ON_START=1 を本番で設定することは推奨されません。
- Paper Trading は完全に本番 DB と分離されます（`PAPER_TRADING_SQLITE_PATH` を使用）。テスト目的の際は paper_trading 環境で動かしてください。
- OpenAI API を使う機能は API レート・コストに注意してください。`OPENAI_API_KEY` は安全に管理してください。
- ログディレクトリ（デフォルト `logs/`）や `data/` ディレクトリは実行ユーザーで書き込み可能であることを確認してください。ログディレクトリ作成に失敗した場合はコンソール出力のみで動作します。

---

## サンプルワークフロー（初回起動例）

1. 仮想環境作成・依存インストール
2. `.env` を対話式で作成
   ```
   python -m kabusys.config_setup
   ```
3. 設定検証
   ```
   python -m kabusys.validate_config
   ```
4. 監視ループ起動（モニタリング）
   ```
   python -m kabusys.run_monitoring
   ```
5. 別プロセスで Execution 起動
   ```
   python -m kabusys.run_execution
   ```

停止: `data/stop_requested.flag` を作成すると両プロセスは検知して終了します（または Kill Switch が `data/kill.flag` を作成して ExecutionEngine を停止させます）。

---

README に書かれている情報はコードのコメント・実装に基づいてまとめています。実運用やデプロイ時は本リポジトリのその他ドキュメント（config/*.yaml や運用手順書）が存在する場合、それらも併せて参照してください。もし README に追加したい箇所（例: API スキーマ、より詳細な設定例、依存関係一覧等）があれば教えてください。