# KabuSys

日本株自動売買システムの簡易実装コアライブラリ群と起動スクリプト群です。  
このリポジトリには、実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算）、AI 補助モジュール（ニュース NLP / レジーム判定）、および運用支援ツールが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成する主要コンポーネントをモジュール化した実装です。主な機能は次のとおりです。

- ExecutionEngine（発注実行、ブローカークライアントを抽象化）
- Monitoring（システム稼働監視、取引ログ監視、リスク監視、Kill Switch）
- Portfolio construction（候補選定・重み計算・ポジションサイジング・セクター制限）
- Research（DuckDB を用いたファクター計算・特徴量解析）
- AI モジュール（OpenAI を用いたニュースセンチメント / マーケットレジーム判定）
- ユーティリティ（logging の統一設定、プロセス優先度設定）
- 運用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

設計方針の一部：
- DB は DuckDB（分析用）と SQLite（監視 / 発注ログ）を使い分け
- Paper Trading は本番 DB と分離して専用 SQLite に記録
- LLM 呼び出しに対してはリトライやバリデーションを盛り、失敗時はフェイルセーフで続行

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて Mock/Live ブローカー切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
- 環境設定 / 検証
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の事前検証 CLI
- 運用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成
- ポートフォリオ構築
  - portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ
  - research: ファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事を LLM でセンチメント付与し ai_scores に格納
  - ai/regime_detector.py: MA とマクロニュースで市場レジーム判定（market_regime に書き込み）
- 監視
  - monitoring: system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db
  - MonitoringDB: SQLite ベースの永続化層（テーブル初期化・マイグレーション含む）
- ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定（コンソール + 日次ローテートファイル）
  - utils/process_priority.py: プラットフォーム透過の優先度設定 / CPU affinity

---

## セットアップ手順（ローカル実行向け）

前提: Python 3.9+ を想定しています（実際の互換性は環境に依存します）。

1. リポジトリをクローン／ワークツリーへ移動

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 推奨パッケージ（最低限）:
     - duckdb
     - psutil
     - openai
   - 開発・追加機能:
     - PyYAML（config YAML 検証時）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt はこのリポジトリに含まれていない想定のため、上記をプロジェクトに合わせて調整してください。

4. ログ / データ ディレクトリを作成
   - mkdir -p data logs

5. .env の初期作成（推奨）
   - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参考に）

6. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題があれば警告/エラーに従って修正

7. DB 初期化
   - run_execution / run_monitoring を起動すると必要なテーブルが自動的に作成されます（monitoring_db.init_monitoring_db）

注意:
- OpenAI を使う機能を利用する場合は環境変数 OPENAI_API_KEY を設定してください。
- 本番環境（KABUSYS_ENV=live）では敏感な操作が行われるため .env の管理に注意してください（.env は Git にコミットしないこと）。

---

## 主要な環境変数一覧

必須
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

主要（デフォルトあり）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: SQLite（監視用）パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）。デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant | partial | never | reject）。デフォルト: instant
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。デフォルト: 60
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアする (0/1)。デフォルト: 0

運用用フラグファイル
- data/kill.flag: Kill Switch によって作成されるフラグ（ExecutionEngine 停止トリガー）
- data/stop_requested.flag: run_monitoring/run_execution の外部停止トリガ（手動による安全停止）

---

## 使い方（代表的なコマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 本番稼働前は --strict オプションを推奨（警告も失敗扱い）
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB に記録します（本番 DB と分離）。

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます。例:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

運用上の停止・再起動
- run_execution / run_monitoring はプロセス優先度を高く設定して起動します（utils.process_priority）。
- 安全停止:
  - 外部から data/stop_requested.flag ファイルを作成すると run_monitoring / run_execution は検知して終了します。
  - Kill Switch により data/kill.flag が作成されると ExecutionEngine は停止される設計です（KillSwitch により冪等にフラグを書き込み）。

ログ
- ログは標準出力（console）および logs/<app_name>.log に日次ローテーションで出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

---

## ディレクトリ構成（主要ファイル説明）

リポジトリの主要なパスと説明:

- src/kabusys/
  - __init__.py
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - config.py — Settings クラス（.env 自動読み込み / 各種設定プロパティ）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート出力
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算（等配分・スコア加重）
    - position_sizing.py — 株数計算・キャップ・単元丸め
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — モメンタム / ボラ / バリュー等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコア化して ai_scores に登録
    - regime_detector.py — マーケットレジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB の初期化と簡易ラッパー
    - system_monitor.py — システム指標・データ鮮度・プロセス監視（psutil, DuckDB 参照）
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - trade_monitor.py — （存在するはずの）取引監視ロジック（抜粋コード基に存在）
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - kill_switch.py — kill.flag 書込みロジック
    - alert_manager.py — （アラート送信の抽象化：LINE 等）
  - execution/
    - execution_engine.py — メイン ExecutionEngine（起動 / セッション実行）
    - broker_factory.py — BrokerClient の切替（実ブローカー / Mock）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注管理・DB・整合機能
  - utils/
    - logging_setup.py — ルートロガー設定（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring_db / その他 — SQLite テーブル定義・Migration 処理など

---

## 運用上の注意・トラブルシュート

- .env に機密情報（API キー等）を格納する場合は Git にコミットしないこと。
- OpenAI 呼び出しはネットワークやレート制限で失敗する可能性があるため、該当処理ではリトライ / フォールバックを実装していますが、API キーやネットワーク状態の確認を行ってください。
- DuckDB / SQLite ファイルはパスの親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、権限エラーには注意してください。
- run_execution は pid ファイル（デフォルト data/execution.pid）を用います。プロセス制御やデプロイ時はこれを考慮してください。
- KABUSYS_ENV=paper_trading による分離：
  - ペーパートレードでは MockBrokerClient を用い、data/paper_trading.db に記録します。本番 DB と完全分離されています。
- kill.flag / stop_requested.flag の存在は、誤って残しているとプロセスが起動しない・即停止する原因になるため、運用時は状態を確認してください。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します。

---

## 貢献・拡張ポイント（高速ヒント）

- ブローカー実装（実ブローカ接続）のプラグイン化を進めると、他の証券 API への拡張が容易になります。
- portfolio の lot_size を銘柄別に切替える機能を追加することで現実の単元株ルールに対応可能です（TODO コメントあり）。
- AI 関連は、モデルやプロンプトの改良、JSON パース耐性の向上、ロギング強化が効果的です。
- config/*.yaml を利用して動的な戦略パラメータを読み込む仕組みを整えると柔軟性が上がります。

---

必要であれば、README の英語版、systemd / supervisor 用のサービス定義、example .env.example、requirements.txt、あるいは主要 CLI の詳細マニュアル（引数説明・出力例）も作成できます。どれを優先しますか？