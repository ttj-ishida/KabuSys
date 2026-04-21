# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・研究用ユーティリティを含む日本株自動売買システムのコードベースです。DuckDB / SQLite をデータ層に使用し、必要に応じて OpenAI（ニュースNLP / レジーム判定）を呼び出します。

## プロジェクト概要
- 戦略（ファクター計算、特徴量解析）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算）
- 発注実行（ExecutionEngine。paper_trading 時はモックブローカーで完全分離）
- 監視（システム状態・注文ログ・リスクなどの定期チェック、Kill Switch）
- 研究ツール（ファクター計算、IC・統計、Paper Trading 検証レポート）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）

主要な設計方針（抜粋）:
- Paper Trading と本番は DB を分離（paper_trading 用に data/paper_trading.db）
- 監視（monitoring）は KABUSYS_ENV に関わらず本番の sqlite_path を参照して監視ログを保管
- OpenAI の呼び出しはフェイルセーフ（失敗時はスキップやフォールバック）
- ルックアヘッドバイアスを避ける設計（date.today() 等の非依存）

## 機能一覧
- run_execution: ExecutionEngine を起動（KABUSYS_ENV に応じて実ブローカー / MockBroker を選択）
- run_monitoring: SystemMonitor を定期ポーリングして system_status 等を記録
- 設定ウィザード (.env 作成) — config_setup.py
- 設定検証 CLI — validate_config.py（--strict が利用可能）
- Paper Trading 検証レポート生成ツール — tools/paper_verification_report.py
- ニュース NLP による銘柄センチメント計算（OpenAI を利用） — ai/news_nlp.py
- 市場レジーム判定（ma200 とマクロセンチメントの合成） — ai/regime_detector.py
- ポートフォリオ構築（選定、重み付け、リスク調整、ポジションサイズ算出） — portfolio/*
- 研究用ファクター計算・特徴量解析 — research/*
- 監視用 DB レイヤ・各種 Monitor（System/Trade/Risk）と KillSwitch / Alert 管理 — monitoring/*
- 共通ユーティリティ（ログ設定、プロセス優先度、etc.） — utils/*

## セットアップ手順（ローカル開発）
1. Python 環境（推奨: 3.10+）を用意
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（プロジェクトに requirements.txt があればそれを利用）
   - pip install duckdb psutil openai
   - 研究・YAML 検証に PyYAML が必要なら: pip install PyYAML
   - 追加で必要なパッケージがあればプロジェクトの requirements.txt/ドキュメントを参照してください
4. データディレクトリを作成（任意だが推奨）
   - mkdir -p data logs
5. .env を準備
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（下記の主要環境変数参照）

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要な任意 / 設定可能環境変数（一部）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）※ monitoring は常に本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- LOG_DIR: ログファイル保存先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う場合に必要（ai モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0" 推奨）

注意点
- .env の自動読み込み機能があり（config.py）、プロジェクトルートにある .env / .env.local を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- validate_config.py は .env と config/*.yaml の整合性チェックを行います。PyYAML がない場合は YAML の内容検証をスキップします。

## 使い方（起動・検証・ツール）
基本的な CLI 実行例（プロジェクトルートで実行）:

- ExecutionEngine の起動（本番 / paper_trading に応じて振る舞いが変わる）
  - python -m kabusys.run_execution

  特記事項:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_sqlite_path（デフォルト data/paper_trading.db）に発注ログ等を記録します。
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
  - エンジンは data/execution.pid を作成します。

- Monitoring の起動（定期ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を変更可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録します。
  - data/stop_requested.flag が検出されるとループを終了します。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告を FAIL 扱い）: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 簡易チェック: 稼働率 / 成功率 / 送信率 / P95 レイテンシ等を計算して PASS/FAIL を出力します

- AI 関連（ニューススコアリング / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY が必要。関数呼び出し時に api_key を渡すことも可能。

停止・Kill Switch
- システムが指定条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止を促します（Execution 側は起動時やループ内で flag を検査）。
- Kill flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1（ただし本番では 0 を推奨）。

ログ
- 共通のログ設定ユーティリティを用意しています（kabusys.utils.logging_setup.setup_logging）。
- デフォルトで stdout と日次ローテート（logs/<app_name>.log）を併用します。

開発用ユーティリティ
- config/*.yaml の生成スクリプト等がプロジェクトに含まれる場合があります（validate_config は config ディレクトリの YAML をチェックします）。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下）

- __init__.py
- config.py — 環境変数読み込み / Settings
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前チェック CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
  - __init__.py

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算（リスクベース等）
  - risk_adjustment.py — セクター制限・レジーム乗数
  - __init__.py

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリー
  - __init__.py

- monitoring/
  - monitoring_db.py — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — （注文滞留・約定異常等の監視）※実装ファイルは存在（省略）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書込ロジック
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — 通知管理（LINE 等への通知を想定）※実装ファイルは存在（省略）

- execution/
  - execution_engine.py — ExecutionEngine 本体（EngineConfig 等）
  - broker_factory.py — ブローカークライアント生成（Mock / Live 切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...（発注・リスク制御等）

- data/ （リポジトリルートの想定ディレクトリ）
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（paper_trading 用デフォルト）
  - kill.flag, stop_requested.flag, execution.pid など

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール

- utils/
  - logging_setup.py — 共通ログ初期化
  - process_priority.py — プロセス優先度 / CPU affinity 設定
  - その他ユーティリティ

（上記は主要ファイルの抜粋です。詳細はソースコードを参照してください）

## 運用上の注意
- 本番（KABUSYS_ENV=live）では .env の内容を慎重に管理し、LINE 通知や KILL スイッチの設定を確認してください。
- kill.flag を誤ってクリアすると意図しない稼働継続につながるため、KILL_FLAG_CLEAR_ON_START の設定は運用方針に合わせて設定してください。
- OpenAI を用いる機能は API コストとレスポンスの可用性に注意してください。API 失敗はフォールバックされますが、期待する結果が得られない場合があります。
- データ保管（DuckDB / SQLite）のバックアップ戦略を定めてください（特に本番分析用 DuckDB は重要データを含む可能性があります）。

---

詳細な API ドキュメント（各関数の引数・戻り値・挙動）や実運用手順はソース内の docstring を参照してください。追加で README に記載したい項目（例: デプロイ手順、systemd / Supervisor 用のユニット例、CI 設定など）があれば教えてください。