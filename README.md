# KabuSys — README

このリポジトリは日本株向けの自動売買システムのコアライブラリ群です。戦略の研究・ファクター計算、ポートフォリオ構築、発注実行エンジン、監視・アラート、そして一部 AI（ニュースセンチメント）連携などの機能を含みます。

以下は本コードベースの要約ドキュメントです。

## プロジェクト概要
- KabuSys は日本株自動売買に必要なコンポーネントをモジュール化した Python パッケージです。
- 主な関心領域：
  - リサーチ（ファクター計算、特徴量解析）
  - ポートフォリオ構築（候補選定、重み付け、株数算出）
  - 実行（ExecutionEngine、OrderManager、RiskManager など）
  - 監視（SystemMonitor / TradeMonitor / RiskMonitor、Kill Switch）
  - AI 支援（ニュース NLP によるセンチメント、レジーム判定）
  - ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- アーキテクチャは DB（DuckDB, SQLite）を中心に設計され、実行・監視・研究モジュールが分離されています。

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution）
  - 本番 / ペーパートレード切替（KABUSYS_ENV に依存）
  - paper_trading 時は MockBrokerClient を使い、paper DB に記録して本番 DB と完全分離
  - プロセス優先度の設定、PID ファイル管理、停止フラグによる安全停止
- 監視ループ起動スクリプト（run_monitoring）
  - システムリソース監視（CPU/メモリ/ディスク）、データ鮮度チェック、プロセス生存監視
  - RiskMonitor によるドローダウン／ポジション上限監視、KillSwitch 判定、アラート連携
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）
  - 監視ログは SQLite に永続化（monitoring.db）
- ポートフォリオ構成モジュール
  - 候補選定、等金額／スコア重み、リスクベースのポジションサイズ算出、セクターキャップ適用、レジーム乗数
- リサーチ（research）
  - ファクター（モメンタム、バリュー、ボラティリティ）計算
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
  - DuckDB を用いた高速 SQL ベース処理
- AI モジュール
  - news_nlp: raw_news を集約し OpenAI（gpt-4o-mini 等）でセンチメントを算出、ai_scores に書込
  - regime_detector: ETF の MA とマクロニュースセンチメントを合成して日次レジーム判定を行う
  - API 呼び出しはフェイルセーフ設計（リトライ、失敗時フォールバック）
- 管理ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: .env と config/*.yaml の存在・簡易検証 CLI
  - tools.paper_verification_report: ペーパートレード履歴からの検証レポート生成（稼働率・成功率・レイテンシ等）

## 環境・前提
- 推奨 Python バージョン: 3.10+
  - 型注釈（| 演算子）を多用しているため 3.10 以上推奨
- 主要依存（一例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML 検証を行う場合）
- DB/ファイルデフォルト（各種環境変数で上書き可）
  - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH)
  - SQLite (monitoring): data/monitoring.db (環境変数 SQLITE_PATH)
  - Paper trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - PID ファイル: data/execution.pid (PID_FILE_PATH)
  - Kill フラグ: data/kill.flag (KILL_FLAG_PATH)
  - stop_requested フラグ（run_*.py での起動停止確認）: data/stop_requested.flag（プロジェクト直下 data）
  - ログディレクトリ: logs/（環境変数 LOG_DIR で変更可）

## 必須環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- その他（省略可 / 推奨）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - LOG_LEVEL（DEBUG/INFO/...）
  - OPENAI_API_KEY（AI 機能を利用する場合）
  - PAPER_FILL_MODE（paper_trading の約定モード: instant/partial/never/reject）

## セットアップ手順（ローカル／開発向け）
1. レポジトリをクローン
   - git clone ... && cd <repo>
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai  # 必要に応じて pyyaml などを追加
   - （パッケージ一覧は requirements.txt があればそちらを使用）
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - あるいは .env を手動で作成（.env.example を参考）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict
6. 必要ディレクトリの作成（通常は起動スクリプトが自動作成）
   - mkdir -p data logs
7.（AI 機能を使用する場合）OPENAI_API_KEY を .env に設定

## 使い方（起動／ツール）
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時にプロセス優先度を High に設定します。
    - data/stop_requested.flag を作成すると起動中のエンジンは安全に停止します。
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します
    - stop flag（data/stop_requested.flag）で停止
- .env の対話式作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
- AI モジュール（ライブラリ関数として利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 停止・保護メカニズム
- Kill Switch: RiskMonitor の判定（ドローダウン超過、ポジション数上限等）で data/kill.flag を書き込み、ExecutionEngine に停止指示を送ります。
- 手動停止: data/stop_requested.flag を作成すると run_execution/run_monitoring は起動ループを抜けます。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag をクリアできますが、本番では 0 推奨です。

## ログ
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name=...)
  - stdout（StreamHandler）と日次ローテーション（TimedRotatingFileHandler）を設定
  - ログディレクトリ: LOG_DIR 環境変数または logs/
  - ログファイル: <log_dir>/<app_name>.log（例: logs/execution.log）

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主なファイル・モジュールの概要です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 自動読み込み、Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 発注株数計算、集約キャップ調整
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py      — モメンタム/バリュー/ボラティリティ等の算出
    - feature_exploration.py  — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py             — ニュースセンチメント取得（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（AI + MA 合成）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化 & 永続化 API
    - monitoring_engine.py    — 各 Monitor を束ねるループ
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - trade_monitor.py        — （発注ログ監視等：ソース参照）
    - kill_switch.py          — Kill Switch 実装
    - alert_manager.py        — （アラート連携：LINE 等。ソース参照）
  - execution/                — ExecutionEngine、OrderManager、RiskManager 等（ソース参照）
  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/                     — デフォルト DB / flag ファイル置き場（実行時生成）

（※一部ファイルは本 README 作成時の抜粋により省略しています。詳細はソースコードを参照してください。）

## 開発時の注意点 / 運用メモ
- Paper trading は本番 DB と分離されるよう設計されています。テスト時は KABUSYS_ENV=paper_trading を利用してください。
- AI（OpenAI）連携は API キー管理に注意してください。料金やレスポンスの不確実性に備え、フェイルセーフ設計（フォールバック値、リトライ、ログ）があります。
- run_monitoring は監視用 SQLite を常に本番パス（SQLITE_PATH）で使用します。監視データは本番 DB に書き込まれます（環境にかかわらず）。
- .env ファイルは機密情報を含むため絶対に Git にコミットしないでください。

---

詳細な API や実装方針、アルゴリズムの設計ノートはソースコメント（各モジュールの docstring）内に記載されています。まずは config_setup で .env を作成し、validate_config でチェックした上で run_monitoring / run_execution を起動してください。必要があれば個別モジュールのドキュメント化も支援します。