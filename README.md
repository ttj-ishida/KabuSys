# KabuSys

日本株向けの自動売買／研究基盤ライブラリ群（プロトタイプ）

このリポジトリは、アルゴリズム取引の実行エンジン、監視、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI を利用したセンチメント評価）などを含むモジュール群を提供します。実行スクリプトは軽量な SQLite / DuckDB を用いてログ・分析データを保持し、環境に応じてペーパー取引（完全分離DB）と本番取引を切り替えられる設計です。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動コマンド／ユーティリティ）
- 環境変数（主要項目とデフォルト）
- 注意点 / 運用メモ
- ディレクトリ構成

---

プロジェクト概要
- 自動売買の実行（ExecutionEngine）と監視（Monitoring）を分離して実装。
- DuckDB を分析用に、SQLite を監視・発注ログ用に使用。
- Paper Trading モードは本番 DB と分離して data/paper_trading.db を使用。
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント／レジーム判定モジュールを含む（APIキー必須）。
- ロギングは統一ユーティリティで管理（コンソール + 日次ローテートファイル）。

主な機能一覧
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV による paper_trading / live / development 切替
  - ブローカークライアント抽象化（Mock を含む）
  - リスク管理・オーダーマネージャ・再照合など
- 監視ループ起動スクリプト（run_monitoring）
  - CPU/メモリ/Disk、プロセス生存、データ鮮度の監視
  - Kill Switch（data/kill.flag）で外部から ExecutionEngine を停止可能
  - ポーリング間隔は環境変数で上書き可能
- 監視 DB 層（monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化
  - マイグレーション（カラム追加）対応
- ポートフォリオ構築（portfolio）
  - 候補選定、等配分・スコア重み、ポジションサイズ計算（単元株考慮）
  - セクター上限やレジーム乗数適用
- 研究モジュール（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI モジュール（ai）
  - news_nlp: ニュース記事の銘柄別センチメントを OpenAI へ問い合わせ、ai_scores に保存
  - regime_detector: MA200 乖離 + マクロニュースで日次の市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 起動前チェック（validate_config）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度 / CPU affinity ユーティリティ（utils.process_priority）
- ツール
  - paper_verification_report: Paper Trading の検証レポート出力

セットアップ手順（簡易）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は最低限以下をインストール）
     - duckdb, psutil, openai
     - PyYAML は validate_config の YAML 検証で任意
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - ウィザードは .env を生成/更新します。生成後に設定検証を推奨:
     - python -m kabusys.validate_config

5. データディレクトリの確認
   - デフォルト DB / PID / フラグは data/ 以下に置かれます。起動前にディレクトリを作成するか、自動作成に任せてください。

使い方（主要コマンド）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱いで exit(1)
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（既定 60）
  - 停止方法: data/stop_requested.flag を作成するとループが終了します
- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、data/paper_trading.db を使用します
  - 実行中は data/execution.pid に PID が書き込まれます。停止は data/stop_requested.flag または Kill Switch による停止
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
- AI（ニュース / レジーム）
  - OpenAI API キー（OPENAI_API_KEY）を .env に設定する必要があります
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用

主要な環境変数（抜粋・デフォルト）
- 必須
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
- 動作モード / ログ / DB
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs/）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視用 DB のパス）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
  - PID_FILE_PATH: data/execution.pid（デフォルト）
- AI
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時必須）
- Paper Trading 挙動
  - PAPER_FILL_MODE: instant|partial|never|reject（デフォルト: instant）
- 監視 / Kill Switch
  - KILL_FLAG_PATH: data/kill.flag（Kill Switch のフラグファイル）
  - KILL_FLAG_CLEAR_ON_START: 0|1（デフォルト 0。1 だと起動時に kill.flag を自動クリア）
  - MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、run_monitoring で参照）
- しきい値（監視）
  - CPU_THRESHOLD_PCT（デフォルト 90.0）
  - MEMORY_THRESHOLD_PCT（デフォルト 85.0）
  - DISK_THRESHOLD_PCT（デフォルト 90.0）

注意点 / 運用メモ
- .env は決して Git にコミットしないでください（シークレット情報が含まれます）。
- KABUSYS_ENV=live の場合は特に注意。validate_config は本番用の注意喚起を出します。
- Kill Switch（data/kill.flag）は ExecutionEngine の強制停止トリガです。自動クリア設定は本番での使用を慎重に検討してください。
- run_execution は paper_trading モードで専用 DB を使用し、本番 DB とは完全に分離されます。
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで残ります。ログディレクトリ作成に失敗した場合、ファイル出力はスキップして stdout のみで継続します。
- process priority は起動時に high に設定されますが、OS・権限によって設定に失敗することがあります（警告ログのみ）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理（自動 .env ロードと Settings クラス）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_monitoring.py          — 監視ループ起動スクリプト
  - run_execution.py           — 実行エンジン起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py              — ニュースセンチメント評価（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロNLP）
  - monitoring/
    - monitoring_db.py         — SQLite の永続化層
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py         — 発注ログ監視（滞留注文・異常約定など）※参照実装あり
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag の書き込み・管理
    - monitoring_engine.py     — 各モニタを束ねるポーリングエンジン
    - alert_manager.py         — アラート送信（LINE 等、実装参照）
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算・制限調整
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
  - utils/
    - logging_setup.py         — ロギング設定ユーティリティ
    - process_priority.py      — プロセス優先度・CPU affinity

補足（開発者向け）
- DuckDB 接続を研究・AI 関連モジュールに渡して SQL と Python を組み合わせて計算します。prices_daily / raw_financials / raw_news 等のテーブル構成に依存します。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを無効化できます。
- OpenAI など外部 API 呼び出しはリトライとフェイルセーフが組み込まれていますが、APIキーやレート制限に注意してください。

問い合わせ / 貢献
- プロジェクトに関する質問やバグ報告、改善提案は Issue を立ててください。
- 大きな変更を加える際は設計意図（リスク挙動・DB スキーマ）を考慮してください。

以上。必要であれば README の英語版や systemd 起動例、Docker 化手順、詳細な運用チェックリスト（運用 Runbook）も作成できます。どのドキュメントが欲しいか教えてください。