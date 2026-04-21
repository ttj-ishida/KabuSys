# KabuSys

日本株自動売買システムのリポジトリ（簡易 README、日本語）。

この README はコードベース（src/kabusys 以下）を参照して作成しています。実行前に必ず .env を作成し（`python -m kabusys.config_setup` 推奨）、`python -m kabusys.validate_config` で検証してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。主な機能は次のとおりです。

- 実行エンジン（ExecutionEngine）：ブローカークライアント経由での発注管理、リスク制御、注文再整合（reconciler）など。
- 監視（Monitoring）：システム状態、注文ログ、リスク（ドローダウン、保有数上限）を定期チェックし、必要に応じてアラート／Kill Switch を発動。
- ポートフォリオ構築：候補選定、重み付け、ポジションサイズ計算、セクター制限やレジーム乗数の適用。
- リサーチ／ファクター計算：モメンタム、ボラティリティ、バリュー等のファクターを DuckDB 上で計算。
- AI モジュール：ニュースセンチメント（OpenAI）に基づくスコアリング、マクロニュースを用いた市場レジーム判定。
- 付帯ツール：ペーパートレード向け検証レポート出力など。

設計上のポイント：
- .env / 環境変数で挙動を切り替え（KABUSYS_ENV: development / paper_trading / live）。
- Paper Trading は本番 DB と分離（デフォルト: data/paper_trading.db）。
- 監視（monitoring）は環境に関わらず本番用 sqlite_path を参照してログを記録。
- OpenAI を利用する機能は API キーが必要（環境変数 OPENAI_API_KEY）。

---

## 機能一覧（抜粋）

- 起動スクリプト
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用）
  - run_monitoring.py: SystemMonitor を中心とした監視ループの起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 設定関連
  - config_setup.py: .env の対話式作成ウィザード
  - validate_config.py: 環境変数や config/*.yaml の整合性チェック CLI
  - config.Settings: 環境変数のラッパー（デフォルトや検証を提供）
- 監視
  - monitoring/monitoring_db.py: SQLite ベースの永続化層（テーブル作成・マイグレーション含む）
  - monitoring/system_monitor.py: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py, monitoring/monitoring_engine.py
- ポートフォリオ構築
  - portfolio/portfolio_builder.py, position_sizing.py, risk_adjustment.py
- リサーチ
  - research/factor_research.py: momentum / volatility / value 等
  - research/feature_exploration.py: 将来リターン算出・IC 計算・統計サマリ
- AI
  - ai/news_nlp.py: raw_news を LLM に渡して銘柄別センチメントを ai_scores に書込む
  - ai/regime_detector.py: マクロ記事 + ETF MA200 を合成して市場レジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成（SQLite から集計）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を準備
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存ライブラリをインストール
   - 必須（コードで import されているもの）:
     - duckdb, psutil, openai
   - 任意（YAML 検証を使う場合）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 重要な環境変数（最低限必要）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
   - .env を作成後、設定検証:
     - python -m kabusys.validate_config
     - 問題があれば修正してください

4. データディレクトリの作成（自動生成される場面もありますが手動で作ると安全）
   - mkdir -p data logs

---

## 使い方（起動・操作例）

- ExecutionEngine を起動
  - デフォルト（実行は current ディレクトリで .env を参照）:
    - python -m kabusys.run_execution
  - Paper Trading（KABUSYS_ENV=paper_trading）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority を呼ぶ）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で変更:
    - export MONITOR_POLL_INTERVAL=30  # 秒（正の整数）
  - 監視は MONITOR_POLL_INTERVAL 秒毎に SystemMonitor.check_once() を呼び出します

- 設定の検証（必須項目・YAML ファイル等）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い:
    - python -m kabusys.validate_config --strict

- .env を対話的に作る
  - python -m kabusys.config_setup

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベースを指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- 停止・Kill スイッチ
  - ExecutionEngine / Monitoring の起動中に停止させたい場合:
    - ハード停止（run_monitoring/run_execution によって使用されるプロジェクトルート/data/stop_requested.flag）を作成するとループが終了します
      - touch data/stop_requested.flag
    - 実運用の Kill Switch（自動で ExecutionEngine を停止させる）は monitoring.kill_switch が data/kill.flag を書き込みます
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動で削除します（本番では 0 推奨）

- ログ
  - デフォルトログディレクトリ: logs/
  - ログファイル: logs/<app_name>.log（例: logs/execution.log、logs/monitoring.log）
  - 環境変数 LOG_DIR で出力先を変更可能
  - ログローテーション: 日次、30日分保持

---

## 主要な環境変数（抜粋）

- 必須 / 主要
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
  - KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
  - KABUSYS_ENV — execution 環境（development / paper_trading / live）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- データベース / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか
- ログ・運用
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

詳細はコード内の `kabusys.config.Settings`、`config_setup.py`、`validate_config.py` を参照してください。

---

## 注意点 / 運用メモ

- Paper Trading は本番 DB と分離されます（settings.is_paper による切替）。Paper Trading を行う際は PAPER_TRADING_SQLITE_PATH を確認してください。
- 監視（Monitoring）は本番用の sqlite_path を参照します（環境にかかわらず監視ログは production sqlite を使用する設計）。
- OpenAI を使う機能（news_nlp, regime_detector）は API 呼び出し失敗時にフェイルセーフ動作をするよう設計されていますが、API キーと料金に注意してください。
- process priority と CPU affinity の設定はプラットフォームに依存します。psutil による操作が許可されていない環境では警告が出てスキップされます。
- .env は決して VCS にコミットしないでください（config_setup.py のヘッダにも注意喚起あり）。

---

## ディレクトリ構成

（重要なファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - data/ (データ関連モジュールは別パッケージ想定)
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルの一覧です。実際のファイル群はさらに細分化されています。）

---

## 開発・拡張のヒント

- DuckDB を使って履歴データ・ファクター計算を行う設計になっているため、データ投入パイプラインを整備するとリサーチ／AI モジュールが有効に働きます。
- AI 部分（news_nlp, regime_detector）は外部 API 呼び出しに依存するため、ユニットテストでは呼び出しをモックすることを推奨します（コード内で _call_openai_api を切り替え可能な設計）。
- ポートフォリオ構築・リスク制御は純粋関数化されているため、単体テストが書きやすい設計です。

---

必要であれば、README に加えて:
- 具体的な起動手順（systemd / cron / Supervisor 用のユニットファイル例）
- 開発者向けのテスト実行方法（pytest など）
- 依存関係 pin（requirements.txt のサンプル）
を追記します。どれを追加しましょうか？