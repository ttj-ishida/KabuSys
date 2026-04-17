# KabuSys

日本株向け自動売買システムの Python コードベース用 README（日本語）。

以下はリポジトリ内の主要モジュールを基に作成した概要・セットアップ・使い方の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。主な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）による発注処理（paper_trading / live 対応）
- 監視（Monitoring）: プロセス状態・データ鮮度・注文滞留・リスク（ドローダウン・ポジション上限）の監視とアラート
- ポートフォリオ構築ユーティリティ（候補選定・重み算出・サイズ計算・セクター制限）
- リサーチ（ファクター計算・特徴量探索・IC計算 等）
- AI（LLM）を使ったニュース NLP によるセンチメント集計と市場レジーム判定
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール

設計思想のポイント：
- DuckDB / SQLite を用いたデータ分析・監視ログ永続化
- 環境変数（.env）での設定管理（対話ウィザードと検証ツールあり）
- 本番とペーパートレードの DB 分離（paper_trading は専用 SQLite）
- LLM 呼び出しはキー明示または環境変数経由、失敗はフェイルセーフで継続

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV に応じて実ブローカまたは MockBroker を選択
  - paper_trading モードでは data/paper_trading.db を使用して本番 DB と分離
  - 停止用フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）管理

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）
  - 監視ログは sqlite（デフォルト: data/monitoring.db）へ記録

- monitoring モジュール
  - system_monitor: CPU/メモリ/disk、プロセス生存確認、データ鮮度チェック
  - trade_monitor: 注文滞留・約定価格異常検出
  - risk_monitor: ドローダウン・ポジション上限の監視（dashboard を参照）
  - monitoring_db: SQLite のテーブル定義・永続化 API
  - kill_switch: 条件に応じて data/kill.flag を書いて Execution を停止させる（冪等）

- portfolio モジュール
  - 候補選定、等重 / スコア重み計算、ポジションサイズ計算、セクター制限、レジーム乗数

- research モジュール
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（スピアマン）算出、統計サマリー

- ai モジュール
  - news_nlp: OpenAI を使った銘柄ごとのニュースセンチメント評価（ai_scores テーブルへ書き込み）
  - regime_detector: ETF 指標とマクロニュースの LLM 評価を合成して market_regime を算出・永続化

- tools
  - paper_verification_report: ペーパートレード用 SQLite を読み、稼働率・注文成功率・レイテンシ等の検証レポートを生成

- 設定関連
  - config_setup.py: 対話式ウィザードで .env を生成・更新
  - validate_config.py: 環境変数・config/*.yaml 等の事前検証 CLI

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール
   - コードベースでは次のライブラリを利用しています（バージョンは適宜指定してください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証に任意）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
   ※ requirements.txt が提供されていれば `pip install -r requirements.txt` を使用してください。

4. 環境変数ファイル (.env) の初期作成
   - 対話ウィザードを使って .env を生成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` (もし存在すれば) をコピーして手で編集してください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告も失敗扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

注意:
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- AI 機能を使う場合: OPENAI_API_KEY を .env に設定してください。
- DB パスのデフォルト:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper-trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

---

## 使い方（主要コマンド）

- 実行エンジン起動（ExecutionEngine）
  - 本番 or paper_trading は KABUSYS_ENV に依存
  ```
  python -m kabusys.run_execution
  ```
  - 実行中の停止:
    - run_execution は定期的に data/stop_requested.flag を監視しています。ファイルを作成すると安全に停止します。
    - 例: `touch data/stop_requested.flag`（Unix 系）

- 監視プロセス起動（SystemMonitor）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔の変更:
    - 環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）
    - 例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスを明示する場合:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- AI / レジーム関係（プログラム内 API）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OPENAI_API_KEY が必要（api_key 引数で上書き可）

ログ出力:
- 標準 Python logging を使用します。`LOG_LEVEL` 環境変数でレベル制御（デフォルト INFO）。

停止 / キルフラグの取り扱い:
- run_execution/run_monitoring は data/stop_requested.flag を監視して終了します。
- monitoring の KillSwitch は条件を満たすと data/kill.flag を書き、ExecutionEngine に停止を促します。
- kill.flag を手動でクリアするには削除してください（例: `rm data/kill.flag`）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- OPENAI_API_KEY (AI 機能利用時)
- MONITOR_POLL_INTERVAL (run_monitoring 用、秒、デフォルト 60)
- PAPER_FILL_MODE (paper_trading の MockBroker の fill モード: "instant"|"partial"|"never"|"reject")
- KILL_FLAG_CLEAR_ON_START (ExecutionEngine 起動時に kill.flag を自動クリアするか: "0"/"1"、本番では 0 推奨)

詳しくは `kabusys.config.Settings` を参照してください（コード中ドキュメントあり）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル・ディレクトリ構成（src/kabusys 配下を中心に示します）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / .env 自動読み込みロジック、Settings クラス
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py        — （未表示コード: アラート送信ロジック）
    - execution/                — 実行エンジン・ブローカ関連（多数のファイルが想定）
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - order_record.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - monitoring/               — 監視関連（上に記載）
    - utils/
      - process_priority.py     — プロセス優先度/CPU affinity ユーティリティ

data/ 以下（実行時に作成されることが多い）
- data/execution.pid
- data/stop_requested.flag
- data/kill.flag
- data/monitoring.db
- data/paper_trading.db
- data/kabusys.duckdb

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では環境変数と .env の管理に十分注意してください。.env をリポジトリにコミットしないでください。
- `validate_config.py` のチェックを起動前に必ず実行し、特に LINE 通知・Kill Switch 設定などのガードを確認してください。
- AI（OpenAI）を使用する機能は API コストが発生します。API キーや呼び出し頻度に注意してください。
- run_monitoring は監視ログを production sqlite_path に書きます（環境にかかわらず同じ sqlite_path を使用する実装になっています）。paper_trading の検証系は paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
- Process priority / CPU affinity 設定は OS により権限が必要な場合があります。`kabusys.utils.process_priority` がエラーを捕捉してログに出力します。

---

## 参考（開発者向け）

- 各モジュールには docstring・コメントで設計や制約が記載されています。実装変更時は docstring を参照して副作用や前提条件（例: 時刻は UTC で扱う、ルックアヘッドバイアスを避ける等）に注意してください。
- DuckDB を使った分析系関数は SQL を直接埋め込んでおり、パフォーマンス上の前提（スキャン範囲の制限やウィンドウ幅の説明など）がコメントに記載されています。
- ニュース NLP / レジーム判定は外部 API 呼び出しを行いますが、API 呼出し箇所は独立しておりテスト時に差し替え可能です（ユニットテスト用の patch が記載されています）。

---

必要であれば、README をベースに運用手順書（systemd ユニット定義例、Dockerfile、CI 設定、より詳細な環境変数一覧など）を追加で作成します。どの情報を優先して追加したいか教えてください。