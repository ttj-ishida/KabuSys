# KabuSys

日本株自動売買システム KabuSys のリポジトリ向け README（日本語）。

この README はコードベースの主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）と運用監視（Monitoring）、およびリサーチ／ポートフォリオ構築や AI を用いたニュース解析機能を備えた統合システムです。  
主要コンポーネントは次の通りです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行コンポーネント。
- Monitoring：システム状態、注文・約定状況、リスク（ドローダウン・ポジション数）を定期的に監視し、必要時に Kill Switch を発動。
- Research / Portfolio：DuckDB 上の市場データを用いたファクター計算・ポートフォリオ構築ロジック。
- AI（news_nlp, regime_detector）：OpenAI を使ったニュースセンチメント評価や市場レジーム判定。
- Tools：ペーパートレードの検証用レポート生成等の補助スクリプト。

設計方針としては、実取引とペーパートレードの分離、フェイルセーフ（API失敗時のフォールバック）、ルックアヘッドバイアス防止を重視しています。

---

## 機能一覧

- 実行系（Execution）
  - ブローカークライアント切替（本番 / ペーパートレード）
  - 注文管理（OrderManager / OrderRepository）
  - リスク管理（RiskManager, Reconciler）
  - PID / stop フラグ連携による安全停止

- 監視系（Monitoring）
  - システムリソース（CPU / メモリ / ディスク）監視
  - データ鮮度チェック（DuckDB の prices データ）
  - トレードログ解析（滞留注文・異常約定など）
  - リスク監視（ドローダウン、ポジション上限）と Kill Switch
  - アラート通知（LINE 連携等を想定）

- リサーチ / ポートフォリオ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算 / IC 計算 / 統計サマリー
  - 候補選定、重み算出、ポジションサイジング（単元株丸め・資金配分制約考慮）
  - セクターキャップやレジーム乗数の適用

- AI（OpenAI）
  - ニュースの銘柄別センチメント評価（ai_scores への書き込み）
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）

- ツール
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証（validate_config）
  - Paper Trading 検証レポート出力（paper_verification_report）

---

## セットアップ手順

前提：
- Python 3.9+（ソースは型アノテーション等を使用）
- SQLite（標準ライブラリで対応）
- DuckDB を利用するため duckdb パッケージが必要
- OpenAI 連携を利用する場合は openai パッケージと API キー

手順（例）:

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) / .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - 必須（少なくとも）:
     - pip install duckdb psutil openai
   - オプション:
     - pip install PyYAML   # config の YAML 検証用（install されていない場合は警告を出す）
   - （実プロジェクトでは requirements.txt を用意して pip install -r で管理することを推奨）
4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります
6. データディレクトリの確認
   - デフォルトの DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - 必要に応じて .env で上書きしてください

注意:
- 本番（KABUSYS_ENV=live）時は特に LINE トークン等の通知設定や kill flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を十分に確認してください。

---

## 使い方（実行例）

主要なエントリポイントはモジュールとして実行できます（パッケージを Python path に置いた状態で）。

1. 環境ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict

3. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と完全分離）
     - 起動時に data/stop_requested.flag が存在すると起動せず終了
     - 実行中は data/execution.pid に PID を書き込み、停止は stop flag または Kill Switch により安全に行われます

4. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - 動作:
     - デフォルト poll 間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（1 秒以上）
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視 DB を共有）
     - 停止は data/stop_requested.flag を生成することで検出してループを終了

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は data/paper_trading.db。別パスを指定するには --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH を利用

6. AI 関連（プログラム API）
   - OpenAI を使う機能（ニューススコアリング / レジーム判定）は API キーが必要です（OPENAI_API_KEY 環境変数または関数引数で指定）
   - 例（Python 内で呼ぶ）:
     - from kabusys.ai import score_news
     - score_news(conn, target_date, api_key="...")

停止方法（運用上）:
- ExecutionEngine を停止させたい場合は kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を書き込むか、Monitoring の KillSwitch により作成される kill.flag を利用します。stop_requested.flag は主にプロセス自身を優雅に終了させるためのフラグです。

ログ:
- デフォルトで logs/ ディレクトリに日次ローテートのログを出力します（kab usys.utils.logging_setup.setup_logging を利用）。環境変数 LOG_DIR や引数で変更可能。

環境変数の主なキー:
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用:
  - KABUSYS_ENV: development | paper_trading | live
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL, LOG_DIR
  - PAPER_FILL_MODE: instant | partial | never | reject
  - MONITOR_POLL_INTERVAL: 監視ループの秒数（run_monitoring 用）

---

## ディレクトリ構成（主要ファイル・モジュール）

リポジトリ内の主要なパッケージ・モジュールを抜粋して説明します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数自動読み込み（.env / .env.local）、Settings クラスによる設定取得
  - config_setup.py
    - .env の対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（スレッド実行、PID/stop フラグ対応）
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート出力スクリプト
  - execution/ (発注関連 — 実装ファイルは本 README のサンプルには含まれませんが存在を想定)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...
  - monitoring/
    - monitoring_db.py
      - SQLite による監視ログ永続化（テーブル作成・マイグレーション）
    - system_monitor.py
      - リソース監視・データ鮮度チェック・PID チェック
    - trade_monitor.py (コード例では参照あり)
      - トレードログのチェック（滞留注文・約定異常等）
    - risk_monitor.py
      - ドローダウン / ポジション上限の監視（dashboard を参照）
    - kill_switch.py
      - kill.flag の書き込み・評価
    - monitoring_engine.py
      - 各モニタを統合してポーリングする実行クラス
    - alert_manager.py (アラート送信管理、コード参照あり)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
      - OpenAI を利用したニュースセンチメント評価（batch / retry / validation 実装）
    - regime_detector.py
      - ma200 と LLM を組み合わせた市場レジーム判定
    - __init__.py
  - data/ (ランタイムで生成される想定)
    - monitoring.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - paper_trading.db (ペーパートレード用 SQLite)
    - execution.pid, stop_requested.flag, kill.flag, ...
  - logs/
    - execution.log, monitoring.log など（TimedRotatingFileHandler により日次ローテート）

---

## 運用上の注意点・ベストプラクティス

- 本番実行前に必ず python -m kabusys.validate_config で設定チェックを実行してください（--strict を推奨）。
- KABUSYS_ENV=live の場合は kill flag の自動クリア（KILL_FLAG_CLEAR_ON_START）が危険なのでデフォルト 0 を推奨します。
- OpenAI を利用する機能は API 呼び出しに課金が発生します。テスト時はモック化または API キーの利用を制限してください。
- 監視は MONITOR_POLL_INTERVAL で調整できますが、過度に短くするとリソースを圧迫するので慎重に設定してください。
- データベースパス（DuckDB/SQLite）は .env で明示的に設定し、開発・本番で混同しないようにすること（特にペーパートレードは独立 DB を推奨）。

---

必要があれば、README に含めるコマンド例（systemd / supervisor 用の unit 例や docker-compose のサンプル）、より詳細な設定項目一覧、API リファレンス（関数一覧）などを追加で作成できます。どの情報を追加したいか教えてください。