# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ＋起動スクリプト群）です。  
この README はリポジトリに含まれる主要な機能・起動方法・設定方法・ディレクトリ構成を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の要素から構成される自動売買システムのコアライブラリです：

- データ解析 / リサーチ（DuckDB を用いたファクター計算、forward returns、IC 等）
- ポートフォリオ構築（候補選定、重み付け、リスク調整、株数決定）
- Execution エンジン（ブローカークライアント、注文管理、リスク管理、約定・ログ保存）
- Monitoring（システム状態・注文・リスク監視、Kill Switch）
- AI 支援機能（ニュースを LLM でスコアリング、レジーム判定）
- ユーティリティ（設定ウィザード、設定検証、ログ設定 等）
- 開発用ツール（Paper Trading 検証レポート生成など）

設計方針として、ルックアヘッドバイアス防止、フェイルセーフ（API失敗時にゼロフォールバック）、実行環境の分離（paper_trading 用 DB）などが組み込まれています。

---

## 主な機能一覧

- 環境設定管理（Settings クラス）
  - .env / .env.local から自動読み込み（プロジェクトルートを基準）
  - 必須/オプション変数の取得ラッパー
- 設定ウィザード（kabusys.config_setup）
  - 対話式で .env を生成・更新
- 設定検証 CLI（kabusys.validate_config）
  - .env や config/*.yaml の存在・形式チェック
- Execution 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading DB に記録
  - 停止フラグ（data/stop_requested.flag）で安全に停止
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - SystemMonitor を定期ポーリング（MONITOR_POLL_INTERVAL で間隔変更可能）
  - 監視ログは sqlite（monitoring.db）へ保存
- Monitoring コンポーネント
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、PIDファイル監視
  - TradeMonitor：注文滞留・約定異常などの検出（ログ蓄積）
  - RiskMonitor：ドローダウン・ポジション上限監視とダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み Execution を停止
  - MonitoringDB：SQLite テーブルの初期化・読み書き（マイグレーション対応）
- Portfolio モジュール（選定・重み・株数決定・セクター制限）
- Research（DuckDB を使ったファクター計算、特徴量解析、IC 計算）
- AI モジュール
  - news_nlp: OpenAI を用いたニュースセンチメント計算と ai_scores 書き込み
  - regime_detector: MA + マクロセンチメントの合成で market_regime 書き込み
- 開発/運用ツール
  - paper_verification_report: ペーパートレード結果の検証レポート生成

---

## セットアップ手順

1. リポジトリをチェックアウト／クローン

2. Python 必須依存パッケージをインストール
   - 推奨: 仮想環境を作成してからインストール
   - 代表的な依存（requirements.txt が無ければ明示的に）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定 YAML 検証に必要だが必須ではない）
   例:
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb psutil openai PyYAML

3. .env を作成
   - 対話式ウィザードを推奨:
     python -m kabusys.config_setup
   - 生成された .env を編集して必要な値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）を設定してください。
   - 自動読み込み:
     - デフォルトではプロジェクトルートの .env/.env.local を自動読み込みします。
     - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 初期ディレクトリ（data / logs）を作成（多くのスクリプトが自動作成しますが手動で用意しておくと安心）
   mkdir -p data logs

5. DB の初期化は各起動スクリプトが起動時に行います（init_monitoring_db によるテーブル作成・マイグレーション）

---

## 主要な環境変数（代表例）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（任意、デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能を使う場合必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔 秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に既存 kill.flag を自動クリアするか。開発用）

注意: .env.example を参照して .env を作成してください。

---

## 使い方（代表的コマンド）

- 設定ウィザード（.env の作成・更新）
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も失敗扱い

- Execution エンジンを起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB を使い MockBrokerClient を利用
  - 停止方法: data/stop_requested.flag を作成すると安全停止します（run は flag を監視）

- Monitoring を起動（SystemMonitor のポーリング）
  python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path を使用（環境に関わらず）

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール例（ライブラリ関数を Python から呼ぶ）
  from kabusys.ai import score_news
  score_news(duckdb_conn, target_date, api_key="...")

- ログ
  - デフォルトのログ出力先: logs/<app_name>.log（setup_logging で設定）
  - stdout にも出力されます

---

## 注意点 / 運用上のポイント

- DB 分離
  - ペーパートレード時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB と完全分離します。
  - Monitoring は常に sqlite_path（デフォルト data/monitoring.db）を使用します。

- Kill Switch / Stop フラグ
  - KillSwitch は監視結果に応じて data/kill.flag を作成し、実行中の ExecutionEngine に停止シグナルを送ります。
  - run_execution / run_monitoring は data/stop_requested.flag の存在を監視して安全停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（本番では 0 推奨）。

- OpenAI
  - news_nlp や regime_detector は OPENAI_API_KEY を必要とします。API 呼び出しはリトライやフォールバックを備えていますが、料金・レート制限に注意してください。

- プロセス優先度
  - 起動スクリプトでは set_process_priority("high") を呼び出します。権限のない環境では設定に失敗することがあります（警告が出ますが処理は継続します）。

- .env の自動読み込み
  - プロジェクトルート（.git もしくは pyproject.toml を基準）から .env を自動ロードします。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要構成（抜粋）です。実際のツリーではさらに細かなモジュールが含まれます。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（Settings）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 / 永続化層
    - system_monitor.py
    - trade_monitor.py        — （コード中に存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/                # 上述の監視関連
  - tools/
    - paper_verification_report.py

（※上の一覧は README 用に要点を抜粋しています。コードベース全体を参照してください。）

---

## 開発時のヒント

- DuckDB を用いる解析系関数は DuckDB 接続を受け取り SQL と Python を組み合わせて処理します。データは prices_daily や raw_financials 等のテーブルを想定しています。
- テスト時は OpenAI 呼び出し部分（_call_openai_api）をモック化して外部依存を切ることができます。
- run_execution/run_monitoring は module-runner（python -m ...）で起動できます。Daemon 化や systemd / supervisor での管理を想定しています。
- logging_setup.setup_logging を各起動スクリプト最初で呼ぶことで一貫したログ出力・ファイルローテーションが得られます。

---

## よくある問題と対処法

- .env の値が読み込まれない
  - プロジェクトルート（.git または pyproject.toml）が正しく検出できない場合、自動ロードがスキップされます。手動で環境変数を export するか KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI 呼び出しで失敗する
  - OPENAI_API_KEY が設定されているか、レート制限・ネットワーク障害ではないか確認してください。news_nlp/regime_detector はリトライを実装していますが、完全に成功するとは限りません。
- ファイルアクセス権限エラー（logs/ や data/ の作成）
  - 実行ユーザに書き込み権限があることを確認してください。logging_setup はディレクトリ作成に失敗した場合、コンソールログのみで継続します。

---

必要があれば、README に追加で以下を追記できます：
- CI/CD のセットアップ例
- systemd / Docker / コンテナ化の起動例
- よく使う DuckDB / SQLite の SQL スニペット
- config/*.yaml の各項目説明（system_config.yaml 等）

ほかに追記してほしいセクションがあれば教えてください。