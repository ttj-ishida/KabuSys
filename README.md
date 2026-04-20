# KabuSys

日本株向け自動売買システムの一部コードベースです。  
この README はソースツリー（src/kabusys 以下）の主要コンポーネント、設定方法、起動手順、ディレクトリ構成などを日本語でまとめたものです。

注意: 本リポジトリは実運用も想定したコードが含まれています。実機で稼働させる際は十分に内容を確認し、認証情報や .env を絶対に Git にコミットしないでください。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコンポーネント群を含む Python パッケージです。主な責務は以下の通りです。

- 注文実行エンジン（ExecutionEngine）とその周辺（ブローカークライアント、オーダーマネージャ、リスク管理など）
- 監視（Monitoring）：システム状態、注文状況、リスク監視、Kill Switch（停止フラグ）管理、アラート発行
- ポートフォリオ構築ロジック（候補選定、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ用モジュール（ファクター計算、特徴量探索）
- AI 支援（ニュースの NLP によるセンチメント、レジーム検出）
- 付帯ツール（環境設定ウィザード、設定検証、ペーパートレード検証レポート生成など）

設計上、データベースは DuckDB（分析用）と SQLite（監視・発注履歴）を利用します。OpenAI 等の外部 API はオプションです。

---

## 機能一覧

- 実行エンジン起動スクリプト（run_execution）
  - 環境: `KABUSYS_ENV` が `paper_trading` のときは MockBrokerClient を使用し、paper 専用 DB に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視

- 監視ポーリング（run_monitoring）
  - システム状態の定期記録（CPU / メモリ / ディスク / プロセス生存確認）
  - トレード監視、リスク監視、Kill Switch 判定、アラートトリガー
  - ポーリング間隔を環境変数で上書き可能

- 環境設定ウィザード（config_setup）
  - 対話式に `.env` を生成・更新

- 設定検証 CLI（validate_config）
  - .env と config/*.yaml の存在・基本妥当性をチェック（--strict で警告を失敗扱い）

- リサーチ / ファクター計算（research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン・IC・統計サマリ等

- ポートフォリオ構築（portfolio）
  - 候補選出、等金額 / スコア加重、ポジションサイズ計算、セクターキャップ、レジーム倍率

- AI モジュール（ai）
  - ニュースを OpenAI に問い合わせて銘柄別センチメントを算出・保存
  - マクロ記事 + ETF MA を組み合わせて市場レジームを判定

- ツール（tools）
  - ペーパートレード検証レポート生成スクリプト（paper_verification_report）

- 共通ユーティリティ
  - ログ設定（logs への日次ローテーション + stdout）
  - プロセス優先度 / CPU affinity 設定
  - 環境変数読み込み（.env/.env.local）と Settings クラス

---

## セットアップ手順（開発環境）

以下はローカルで動かすための推奨手順です。プロジェクトに requirements.txt が同梱されている場合はそちらを優先してください。

1. リポジトリをクローン
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（最低限の想定依存）
   ```
   pip install duckdb psutil openai
   ```
   - 追加で推奨: PyYAML（config.yaml の検証用）
     ```
     pip install pyyaml
     ```
   - 実運用でブローカー接続等を使う場合はさらに依存が増える可能性があります。

4. .env を作成
   - 対話式で作成する（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - 手動で作成する場合はリポジトリの `.env.example` を参照してください（存在する場合）。
   - 自動で .env を読み込む挙動はデフォルトで有効です（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

5. データディレクトリの準備（任意）
   ```
   mkdir -p data logs
   ```

---

## 環境変数（主なもの）

以下はコード内で参照される主要な環境変数とデフォルト値の一覧（重要なもの）。

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - OPENAI_API_KEY (AI 機能を使う場合必須)

- システム / 実行
  - KABUSYS_ENV: execution 環境 (development / paper_trading / live)（デフォルト: development）
    - paper_trading: 実売買を行わず MockBrokerClient を使用し paper DB を使う
    - live: 本番（要注意）
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)

- データベース / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)

- 監視関連
  - MONITOR_POLL_INTERVAL (run_monitoring が参照、秒。デフォルト: 60)

- Paper Trading 動作
  - PAPER_FILL_MODE (instant|partial|never|reject、デフォルト: instant)

その他、細かな閾値（CPU_THRESHOLD_PCT 等）は Settings クラス経由で環境変数から取得できます。`.env` で必要な値を設定してください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  動作概要:
  - KABUSYS_ENV が `paper_trading` の場合は paper DB に書き込み（PAPER_TRADING_SQLITE_PATH）
  - プロセス優先度を "high" に設定
  - data/stop_requested.flag を検知するとエンジン停止
  - 実行中は data/execution.pid に PID を書き込む（設定により変更可能）

- 監視プロセス起動（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  # ポーリング間隔を上書きする例（30秒ごと）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  動作概要:
  - デフォルト 60 秒間隔で SystemMonitor.check_once() を繰り返す
  - 停止フラグ: <project_root>/data/stop_requested.flag を検知するとループを抜ける
  - Monitoring は環境に関わらず本番の sqlite_path を使用（監視ログは共通に保持）

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示的に指定する
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（プログラム的に呼ぶ）
  - ニュース NLP（銘柄別スコアを ai_scores テーブルに保存）
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - レジーム判定
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止 / Kill Switch / フラグファイル

- stop_requested.flag
  - run_execution / run_monitoring ではプロジェクトの data/stop_requested.flag 存在を監視しているため、このファイルを作成すると起動中のプロセスは優雅に停止します。

- kill.flag
  - モニタリング側の KillSwitch により重大なリスク（ドローダウンやポジション上限超過）を検出した場合に作成されます。
  - ExecutionEngine は起動時に kill.flag の有無をチェックし、存在する場合は起動しない設計です。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 を使うと ExecutionEngine 起動時に自動クリアしますが、本番では推奨されません。

- PID ファイル
  - 実行エンジンは PID を data/execution.pid（デフォルト）に書きます。手動でプロセス操作する際の目安に。

---

## ログ

- ログ出力は共通ユーティリティで設定されます（kabusys.utils.logging_setup.setup_logging）。
- 標準出力（stdout）への出力と、日次ローテートされるファイルログ（logs/<app_name>.log）を両方行います。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定できます。

---

## 注意点 / 実運用上のガイド

- 環境変数や機密情報（APIキー等）は `.env` に保存しても良いですが、絶対に Git 等で公開しないでください。
- `KABUSYS_ENV=live` を設定する場合は、LINE 通知や kill_switch 設定などを十分に確認してください。validate_config は live 時に追加警告を出します。
- OpenAI API を利用する部分はリクエスト数・コストがかかります。API キー管理・請求・レート制御に注意してください。
- DuckDB / SQLite のパスやログディレクトリは権限やバックアップポリシーを確認してください。
- process priority / cpu affinity の設定は OS によって制限される場合があります（psutil が必要、権限不足で警告のみでスキップされます）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイルと役割の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数と Settings クラス（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 経由のセンチメント）
    - regime_detector.py     — 市場レジーム判定（ETF MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（テーブル作成 / CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （トレード監視関連）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch（flag 書き込み）
    - monitoring_engine.py   — 各モニタを束ねるエンジン
    - alert_manager.py       — （アラート送信用の管理）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

- data/
  - （デフォルト DB、flag、PID、ログ出力先などを置く想定ディレクトリ）

---

## よくあるコマンド例

- .env を対話式で作る
  ```
  python -m kabusys.config_setup
  ```

- 設定をチェック
  ```
  python -m kabusys.validate_config
  ```

- 監視プロセスをデバッグ的に一回だけ実行（MonitoringEngine を使うコードを直接テストする場合）
  - 監視用単体テストやスクリプトから MonitoringEngine.run_once() を呼ぶ等

- ペーパートレード検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 追加情報 / 貢献

- 新しい設定キーを追加する場合は `src/kabusys/config.py` と `config/*.yaml`（必要があれば）を更新してください。
- DB スキーマ変更は monitoring_db.init_monitoring_db のマイグレーションロジックに追記してください（既存 DB を壊さないよう注意）。
- テストや CI を導入する場合は、環境依存部分（OpenAI / ブローカー接続 / psutil による設定など）をモック化してください。各モジュールはテスト向けに外部呼び出しを差し替え可能な設計になっています。

---

この README はコードベースの主要点をカバーしています。より詳細な仕様（PortfolioConstruction.md, StrategyModel.md 等）がプロジェクト内にある想定ですので、運用・改修時はそれらの設計ドキュメントも参照してください。質問や補足が必要であればお知らせください。