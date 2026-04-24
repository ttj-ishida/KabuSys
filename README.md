# KabuSys

日本株の自動売買システムのモジュール群（ライブラリ + 起動スクリプト群）の README。  
この README はリポジトリ内のソースコードを元に作成しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム基盤です。  
主な役割は以下のとおりです。

- 注文実行（ExecutionEngine）
  - 実際のブローカークライアントまたはペーパートレード用モックを用いた発注管理
  - 注文管理、リスク管理、注文の再整合（reconciler）等
- 監視（Monitoring）
  - システムの稼働・リソース・データ鮮度・注文状況・リスク指標の定期チェック
  - Kill Switch（条件を満たした場合に ExecutionEngine を停止するためのフラグ）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数等
- 研究・リサーチ（research）
  - DuckDB 上の価格・財務データからファクターや将来リターンを計算
- AI（ai）
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（銘柄ごとの ai_score）や市場レジーム判定
- ユーティリティ
  - 設定読み込み（.env 対応）、ログ設定、プロセス優先度設定など
- ツール
  - Paper Trading の検証レポート生成など

---

## 主な機能一覧

- 設定関連
  - .env 自動ロード（プロジェクトルートに基づく）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証ツール（kabusys.validate_config）
- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動
- 監視（monitoring）
  - システム状態 / データ鮮度監視（SystemMonitor）
  - 注文状態監視（TradeMonitor）
  - リスク監視（RiskMonitor）と Kill Switch
  - 永続化層（SQLite）: monitoring_db.py
- ポートフォリオ構築
  - 候補選定、等重・スコア加重、ポジションサイズ算出、セクターキャップ、レジーム補正
- 研究・分析
  - ファクター計算（momentum, volatility, value）
  - 将来リターン・IC・統計要約
- AI 統合
  - ニュースの銘柄別センチメントスコア付与（OpenAI 使用）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- ツール
  - Paper Trading の検証レポート出力（期間指定可能）

---

## 要件（推奨）

- Python 3.10 以上（型注釈に `X | Y` 形式を使用）
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - (任意) PyYAML（config/*.yaml のパース検証に使用）
- SQLite（Python 標準ライブラリ経由で利用）
- ネットワーク接続（OpenAI API 利用時）

パッケージはプロジェクト側に requirements.txt があればそれを利用します。なければ最低限次をインストールしてください:

```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／展開

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   ```
   pip install -r requirements.txt   # もし requirements.txt がある場合
   # または最低限:
   pip install duckdb psutil openai PyYAML
   ```

4. .env の準備
   - 対話式ウィザードで .env を生成するのが簡単です:

     ```
     python -m kabusys.config_setup
     ```

   - もしくはリポジトリの .env.example を参考に `.env` を作成してください。主な環境変数:

     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（任意）

   - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

5. 設定検証（起動前チェック）

   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにしたい場合
   python -m kabusys.validate_config --strict
   ```

6. 必要ディレクトリ作成（data, logs 等）

   ```
   mkdir -p data logs
   ```

---

## 使い方

- ExecutionEngine（注文実行）起動

  - 実行スクリプト:

    ```
    python -m kabusys.run_execution
    ```

  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中、停止を要求するには data/stop_requested.flag を作成します（既存フラグの検知で安全に停止）。
    - PID ファイルは data/execution.pid（デフォルト）に書き込まれます（Settings.pid_file_path を参照）。

- Monitoring（監視）起動

  - 実行スクリプト:

    ```
    python -m kabusys.run_monitoring
    ```

  - 挙動:
    - SystemMonitor のポーリングループを開始します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に変更可能（デフォルト: 60 秒）。
    - 監視は Settings.sqlite_path（デフォルト: data/monitoring.db）を使用して永続化します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意してください。
    - 停止フラグ (data/stop_requested.flag) を検知するとループを終了します。

- Paper Trading 検証レポート生成

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  - `--db` でデータベースパス指定可能。環境変数 PAPER_TRADING_SQLITE_PATH が既定のパスより優先されます。
  - 出力はコンソールにレポート（稼働率、注文成功率、レイテンシなど）を表示します。

- AI 関連（ニューススコアリング・レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY または関数引数）。
  - プログラム API（例）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 大規模な API 呼び出しはレート制限やエラーに対してリトライやフォールバック実装が組み込まれています。

- 設定ウィザード / 検証

  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

---

## 実行時に利用するフラグ / パス

- data/stop_requested.flag
  - 起動中のスクリプト（execution / monitoring）はこのファイルの存在をチェックして安全に終了します。
- data/kill.flag
  - KillSwitch（リスク条件トリガ）で ExecutionEngine を停止するために作成されるフラグ。
- PID ファイル
  - data/execution.pid（デフォルト）: ExecutionEngine が PID を書き込みます。
- ログ
  - logs/<app_name>.log に日次ローテーションで出力されます（kabusys.utils.logging_setup を使用）。

---

## ディレクトリ構成

以下はリポジトリ内の主なファイル・ディレクトリ（src/kabusys 以下）の一覧と簡単な説明です。

- src/kabusys/
  - __init__.py
    - パッケージメタ（__version__ など）
  - config.py
    - .env 自動ロード、Settings クラス（アプリ設定取得）
  - config_setup.py
    - 対話式 .env 作成ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / paper_trading 切替）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 対応）
  - tools/
    - paper_verification_report.py
      - Paper Trading 検証レポート生成スクリプト
  - execution/
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
    - 注文実行に関連する主要コンポーネント（実装ファイル群）
  - monitoring/
    - monitoring_db.py
      - SQLite を用いた監視データ永続化（テーブル作成・マイグレーション含む）
    - system_monitor.py
      - CPU / メモリ / ディスク / データ鮮度 / プロセス生存監視
    - trade_monitor.py
      - 注文の滞留検出・約定異常検出（実装参照）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視（RiskCheckResult）
    - kill_switch.py
      - Kill Switch の評価・フラグ書き込み
    - monitoring_engine.py
      - 各 Monitor を束ねる実行エンジン（run / run_once）
    - alert_manager.py
      - LINE 等への通知を取りまとめる（実装ファイルが存在する前提）
  - portfolio/
    - portfolio_builder.py
      - 候補選定、等重・スコア加重
    - position_sizing.py
      - 株数決定、集約キャップ、単元丸め
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
  - research/
    - factor_research.py
      - momentum / volatility / value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py
      - 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py
      - ニュースを集約して OpenAI で銘柄ごとセンチメント評価 → ai_scores に書き込み
    - regime_detector.py
      - ETF MA200 とマクロニュースから市場レジームを判定
  - utils/
    - logging_setup.py
      - 一貫したログ設定（console + TimedRotatingFileHandler）
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ラッパー
    - その他ユーティリティモジュール

---

## 注意点 / 運用メモ

- KABUSYS_ENV の値
  - 有効値: `development`, `paper_trading`, `live`
  - `paper_trading` は実際の発注を行わずモックを使い、独立した SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。
- Monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使用します。テスト時の DB 取り扱いに注意してください。
- Kill Switch（kill.flag）は本番環境で注意深く扱ってください。validate_config は KABUSYS_ENV=live 時に警告を出します。
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒）。0以下や非数は無視され、デフォルト 60 秒にフォールバックします。
- OpenAI 利用
  - API キー（OPENAI_API_KEY）が必須。レスポンスのバリデーションやリトライは組み込まれているが、API 利用料やレート制限に注意してください。
- ログディレクトリ作成に失敗した場合、コンソール出力のみで継続します（logging_setup の挙動）。

---

## 例: 最小起動フロー

1. 仮想環境・依存インストール
2. .env を作成（config_setup）
3. 設定検証（validate_config）
4. data/ と logs/ を作成
5. 実行
   - 監視を起動:
     ```
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     ```
   - 実行エンジンを起動:
     ```
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     ```

---

この README はコードベース（src/kabusys 以下）から機能や利用法を抽出して記述しています。実運用に際しては環境変数の設定、DB のバックアップ、LINE 等の通知設定、OpenAI の API キー管理とコスト管理を必ず確認してください。必要であれば README にさらに詳しい運用手順（デプロイ、systemd / supervisor 用ユニット例、ログローテーション方針など）を追加できます。