# KabuSys

KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- ポートフォリオ構築・ポジションサイズ計算（等比重・スコア加重・リスクベース）
- リサーチ（ファクター計算、特徴量探索）
- AI モジュール（ニュースセンチメント / 市場レジーム判定） — OpenAI API を利用
- 各種ユーティリティ（プロセス優先度設定、設定ウィザード、設定検証、ペーパートレード検証レポート）

以下はこのコードベースの使い方、セットアップ手順、ディレクトリ構成などの概要です。

---

## 主な機能一覧

- 設定管理
  - .env（自動ロード）・Settings クラスで環境変数を統一管理
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証ツール（python -m kabusys.validate_config）

- 実行 / 発注
  - ExecutionEngine（run_execution.py）: 本番 / ペーパー環境を切り替えて起動
  - BrokerClientFactory により実ブローカー or MockBroker を選択

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - MonitoringEngine によるポーリングループ
  - Kill Switch（data/kill.flag）で外部から安全に ExecutionEngine を停止可能
  - 監視ログの永続化（SQLite）: monitoring_db モジュール

- ポートフォリオ構築
  - 候補選定・スコア正規化・重み計算（等配分 / スコア加重）
  - セクター制約、レジーム乗数、ポジションサイズ計算（lot 単位切上げ・集約制御）

- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算・IC（Information Coefficient）や統計サマリー

- AI（オプション）
  - ニュースのセンチメントを OpenAI（gpt-4o-mini 等）で評価し ai_scores に保存
  - マクロニュースと ETF の MA 乖離を合成して市場レジーム判定

- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 前提・依存関係

- Python 3.10+
- 必須（利用する機能により必要なもの）
  - duckdb
  - psutil
  - openai（AI 関連機能を使う場合）
- オプション
  - PyYAML（設定検証時に config/*.yaml の中身検証を行う場合）
- DB
  - DuckDB（分析用）
  - SQLite（監視ログ / ペーパートレード DB）

例（最低限の依存をインストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールします（上記参照）。

2. .env の作成
   - 対話式ウィザードを使う:
     ```
     python -m kabusys.config_setup
     ```
     これにより .env を生成・更新できます。
   - または手動で作成（.env.example を参考に）。必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: .env は Git にコミットしないでください。

3. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

4. データディレクトリの確認
   - デフォルトで使用されるパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更

5. AI 機能を使う場合は OPENAI_API_KEY を環境変数に設定するか、関数呼び出し時にキーを渡す。

---

## 実行方法（使い方）

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン（ExecutionEngine）を起動:
  - 本番/開発/ペーパーは KABUSYS_ENV で切り替え
  - 例（ペーパートレード）:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、データは data/paper_trading.db に記録され本番 DB とは分離されます。

- 監視ループ（SystemMonitor 単体起動）:
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - run_monitoring は監視用 DB に対して常に本番 sqlite_path を使用します（KABUSYS_ENV に依存せず）。

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- その他注意点:
  - 実行中の ExecutionEngine を停止したい場合は data/kill.flag を書き込む（KillSwitch が検知して停止指示）。
  - 管理用の stop フラグ: data/stop_requested.flag — run_execution/run_monitoring はこのファイルの存在を見てシャットダウンします。
  - PID 管理: data/execution.pid に PID を書き、SystemMonitor はこのファイルを見てプロセス生存チェックを行います。

---

## 環境変数（主なもの）

- 必須 / 重要
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル（デフォルト: INFO）
- DB パス
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — 監視 DB デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（paper_trading 時に使用）
- AI
  - OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定で使用）
- ペーパートレード挙動
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
- 監視関連
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒（デフォルト 60）
  - KILL_FLAG_PATH — Kill Switch のフラグパス（デフォルト data/kill.flag）
  - PID_FILE_PATH — 実行エンジンの PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。production では 0 推奨）

詳細は kabusys.config.Settings と config_setup.py の定義を参照してください。

---

## 安全上の注意（運用時の留意点）

- 本番環境 (KABUSYS_ENV=live) では特に LINE 通知や KILL_FLAG_CLEAR_ON_START の設定に注意してください。validate_config は live 用のガードを出します。
- .env (シークレットを含む) を Git 等にコミットしないでください。
- OpenAI やブローカーの API キーは適切に管理してください。
- 実運用では MONITOR_POLL_INTERVAL の設定や process priority の扱い（run_* は起動直後に優先度を high に設定）を確認してください（set_process_priority 関数）。

---

## ディレクトリ構成（概要）

以下は主要なファイル・モジュールのツリー（src/kabusys 以下）です。実際のリポジトリ全体構成にあわせて参照してください。

- src/kabusys/
  - __init__.py
  - config.py                — 設定読み込み / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）
    - regime_detector.py      — レジーム判定（OpenAI）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算
    - feature_exploration.py  — 将来リターン・IC 等
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信管理：LINE 等へ通知する想定）
  - execution/                — 発注関連（OrderRepository / Engine 等）
    - (order_repository.py, execution_engine.py, broker_factory.py, ...)
  - data/                     — データ処理 / pipeline / stats（DuckDB 関連）

（上の list は実装ファイルの抜粋です。実際のファイルを確認してください）

---

## よく使うコマンド例

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレードでエンジン起動:
  ```
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- 監視ループ起動（ポーリング間隔を 30 秒にする例）:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 参考（実装上の補足）

- run_execution.py:
  - KABUSYS_ENV=paper_trading の場合は paper_sqlite_path に接続し、MockBroker を使用して本番 DB と完全に分離します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行は別スレッドで行い、stop flag を監視して graceful shutdown します。

- run_monitoring.py:
  - MONITOR_POLL_INTERVAL によりポーリング間隔を制御できます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を利用します（環境に関わらず本番監視 DB に記録する設計）。

- AI モジュール:
  - OpenAI API を利用。API 呼び出しはリトライやエラーハンドリングを含む安全設計になっていますが、API キーの設定は必須です（使用しない場合は無効化してください）。

---

README は以上です。実際に運用する場合は config/*.yaml（Strategy / Risk / Execution 等）やデータ更新パイプライン（prices_daily 等のテーブル生成）を整備してから起動してください。必要であれば README を拡張してデプロイ手順・CI 設定・運用 Runbook を追加できます。