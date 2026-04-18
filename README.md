# KabuSys

日本株向け自動売買システムのリポジトリ（モジュール群のみ）。  
この README はこのコードベースに含まれる主要機能、セットアップ、および基本的な使い方を説明します。

> 注意: 実行には各種外部サービスの認証情報（J-Quants、kabuステーション、OpenAI 等）が必要です。機密情報は `.env` に保存し、リポジトリにコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群を提供します。主な役割は次の通りです。

- 注文実行（ExecutionEngine）
- 監視（System / Trade / Risk の監視と Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量解析）
- AI 補助（ニュースの NLP によるセンチメント評価、レジーム判定）
- ツール類（ペーパー取引の検証レポート生成、設定ウィザード、設定検証 CLI）
- 共通ユーティリティ（ロギング設定、プロセス優先度設定等）

主要な永続化ストレージ:
- SQLite（監視ログ / 発注履歴 / paper_trading の場合の分離 DB 等）
  - デフォルト: `data/monitoring.db`
  - Paper trading 用データベース: `data/paper_trading.db`
- DuckDB（時系列データ / リサーチ向け）
  - デフォルト: `data/kabusys.duckdb`

---

## 機能一覧

- run_execution.py: ExecutionEngine 起動スクリプト
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使い、paper DB に記録して本番 DB と分離
  - 起動時に `data/stop_requested.flag` の存在をチェック。フラグで停止可能
- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視データは monitoring 用 sqlite（デフォルト `data/monitoring.db`）へ永続化
- monitoring パッケージ
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine などの監視ロジック
  - MonitoringDB: SQLite のテーブル定義と読み書きユーティリティ
- portfolio パッケージ
  - 銘柄選定、重み付け、ポジションサイズ計算、セクターキャップやレジーム乗数
- research パッケージ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）、将来リターン、IC 計算、統計要約
- ai パッケージ
  - news_nlp: OpenAI を用いたニュースセンチメント（ai_scores テーブル書き込み）
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- tools
  - paper_verification_report: ペーパートレードの検証レポート生成 CLI
- 設定関連
  - config_setup.py: `.env` の対話的生成ウィザード
  - validate_config.py: 起動前の設定検証 CLI（必須環境変数チェック、config/*.yaml の存在確認等）
- utils
  - logging_setup.py: 標準化されたロギング設定（stdout + 日次ローテーションファイル）
  - process_priority.py: プラットフォーム非依存のプロセス優先度 / CPU affinity 設定

---

## 前提 / 必要環境

- Python 3.10+
  - （ソース内で 3.10 で導入された型表記や union 演算子 `|` を使用）
- 推奨インストールパッケージ（最低限）:
  - duckdb
  - psutil
  - openai
  - PyYAML（オプション: `validate_config.py` の YAML 検証に使用）
- SQLite は標準ライブラリで利用可能

例（仮のインストールコマンド）:
```bash
python -m pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt がない場合は上記を参考にしてください）

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. Python 仮想環境を作成して依存パッケージをインストール
3. .env を作成
   - 対話式ウィザードで作成する:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参照して手動で `.env` を作成（このリポジトリには example がない場合があります）
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）
4. 設定検証（起動前チェック）
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合（厳格モード）
   python -m kabusys.validate_config --strict
   ```
5. 必要ディレクトリの作成（通常はログ/データ作成処理が自動作成しますが念のため）
   ```bash
   mkdir -p data logs
   ```

---

## 使い方（起動・運用）

- ExecutionEngine を起動（本番 / ペーパートレード）
  ```bash
  # 通常（デフォルト KABUSYS_ENV に依存）
  python -m kabusys.run_execution

  # 環境を明示（ペーパートレード）
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - `paper_trading` の場合は MockBrokerClient を使用し、paper 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）へデータを書きます。実運用時は `KABUSYS_ENV=live` を使用してください。
  - 実行中、`data/stop_requested.flag` を作成すると起動ループが検知して優雅に停止します。

- 監視ループを起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - デフォルトのポーリング間隔は 60 秒。環境変数で上書き:
    ```bash
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 監視は monitoring DB（`SQLITE_PATH`）へログを保存します。

- Kill Switch（自動停止）の仕組み
  - RiskMonitor や KillSwitch により `data/kill.flag` が書き込まれると ExecutionEngine に停止指示を出すことができます（実行エンジンは起動時や定期チェックでこのフラグを参照します）。
  - Execution 側は起動時に `KILL_FLAG_CLEAR_ON_START` の設定を参照してフラグを自動クリアするか決めます（本番ではクリアしないことを推奨）。

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB を使う
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB を明示
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キー（`OPENAI_API_KEY`）が必要です。
  - モジュール API 例:
    - ニューススコア付与: `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - これらは DuckDB 接続を受け取り、結果をデータベースへ書き込みます。

---

## 停止・制御

- 即時停止（監視・実行どちらも共通）
  - ループ型スクリプトはプロジェクトルート `data/stop_requested.flag` の存在を監視しています。ファイルを作成すると優雅に停止します。
  - Kill Switch により `data/kill.flag` が書かれると ExecutionEngine 側でそれを検知して停止するフローがあります。

---

## .env の自動ロードについて

- デフォルトでルートの `.env` / `.env.local` が自動で読み込まれます（OS 環境変数を上書きしない挙動）。  
- 自動ロードを無効にする場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成（主要ファイル・説明）

（この README は src/kabusys 配下の主要モジュールを対象にしています）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / 設定読み込みロジック（Settings クラス）
  - config_setup.py
    - .env を対話的に作成するウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py: 共通ログ設定（stdout + 日次ローテートファイル）
    - process_priority.py: プラットフォーム非依存の優先度設定 / CPU affinity
  - monitoring/
    - monitoring_db.py: SQLite テーブル作成・読み書きユーティリティ
    - system_monitor.py: システム状態・データ鮮度監視
    - trade_monitor.py: 発注状態監視（滞留注文などの検出）
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - kill_switch.py: kill.flag の管理
    - monitoring_engine.py: 各 Monitor を束ねる実行エンジン
    - alert_manager.py: （アラート送信抽象化）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - （エンジン本体・注文管理・ブローカー抽象）
  - portfolio/
    - portfolio_builder.py: 候補選定、重み計算
    - position_sizing.py: 株数計算、資金配分ロジック
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: ファクター計算（momentum/value/volatility）
    - feature_exploration.py: 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py: ニュースを OpenAI でスコア化して ai_scores に書き込む
    - regime_detector.py: ETF + マクロニュースで市場レジーム判定
  - tools/
    - paper_verification_report.py: ペーパートレードレポート生成スクリプト

---

## 実運用上の注意・設計上のポイント

- 環境分離:
  - `paper_trading` モードは実口座と完全に分離された SQLite を使用する設計です（`PAPER_TRADING_SQLITE_PATH`）。
- ログ:
  - logging_setup により stdout と日次ローテートファイルへ出力されます（デフォルト保存先: `logs/`）。
- Kill Switch / Stop フラグ:
  - 監視・実行はフラグファイルベースで停止制御や通知を行います。運用者はファイルの扱いに注意してください。
- AI 呼び出し:
  - OpenAI API を使用する部分は冪等性やリトライ、応答バリデーションが考慮されていますが、API キーの漏洩・課金に注意してください。
- 設定検証:
  - `python -m kabusys.validate_config` で起動前に必須変数の有無や config/*.yaml の有効性をチェックできます（PyYAML 未インストール時は YAML 検証をスキップします）。

---

## よく使うコマンドまとめ

- .env 作成（対話式）
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```
- 実行エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```
- 監視ループ起動
  ```bash
  python -m kabusys.run_monitoring
  ```
- ペーパートレード検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要なら README にサンプル `.env` のテンプレート、運用チェックリスト（監視するログや cron/systemd ユニット例）、あるいは各モジュールの API リファレンスを追加します。どの情報を優先して追加しますか？