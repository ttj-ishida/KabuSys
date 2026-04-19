# KabuSys

日本株向け自動売買システムのリポジトリ（軽量プロトタイプ / 内部ツール群）。  
本プロジェクトは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などのコンポーネント群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール式の自動売買基盤です。

- 日次・リアルタイムに近い自動発注（本番 / ペーパートレード切替）
- システム健全性・注文状況・リスク監視と Kill Switch（フラグファイルによる停止）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ算出）
- DuckDB を用いたリサーチ・ファクター計算
- OpenAI（LLM）を活用したニュースセンチメント / 市場レジーム判定（任意）
- ペーパートレードの検証レポート生成ツール

設計要点：
- 環境変数（.env）ベースの設定管理
- SQLite（監視ログ / 発注ログ）と DuckDB（分析）を併用
- 本番環境とペーパートレードは DB を分離
- フェイルセーフ設計（API失敗時のフォールバック、冪等操作、部分失敗保護）

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine（注文管理、ブローカー抽象化）
  - BrokerClientFactory により live/paper の切替
  - Paper Trading: `PAPER_TRADING_SQLITE_PATH` に記録（本番 DB と分離）
- 監視（Monitoring）
  - SystemMonitor: CPU/Mem/Disk、プロセス生存確認、データ鮮度
  - TradeMonitor: 注文の滞留・異常約定検出（ソース参照）
  - RiskMonitor: ドローダウン、保有数上限監視、ダッシュボード更新
  - KillSwitch: リスクトリガーで `data/kill.flag` を書き込み Execution 停止
  - MonitoringEngine: 各 Monitor の統合、アラート発行
- コンフィグ / ツール
  - 対話式 `.env` 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
- ポートフォリオ構築（純粋関数）
  - 候補選定・等重/スコア重み計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め / aggregate cap）
- リサーチ（DuckDB）
  - モメンタム / ボラティリティ / バリュー等ファクター計算
  - 将来リターン計算、IC 計算、統計サマリ
- AI（OpenAI 連携）
  - news_nlp: ニュースを LLM でスコア化して ai_scores に保存
  - regime_detector: ETF の MA とマクロ記事センチメントを合成して市場レジーム判定

---

## セットアップ手順

前提
- Python 3.9+（推奨）
- SQLite は標準ライブラリで利用可能
- system-level: DuckDB クライアント関連のライブラリ（pip でインストール）

推奨手順（仮想環境利用）:

1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone <repo> && cd <repo>

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml
   - pyyaml は設定ファイル（config/*.yaml）検証時に必要

   ※ requirements.txt があれば `pip install -r requirements.txt` を推奨します。

4. 初期設定（.env 作成）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - 本番利用時は --strict を付けると警告もエラー扱いになります

5. データディレクトリの準備
   - デフォルトで使用するパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要なら .env で上書きしてください（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）

6. OpenAI を使う機能を利用する場合
   - 環境変数 OPENAI_API_KEY を設定するか、関数呼び出しで api_key を明示してください。

注意:
- 自動で .env をロードします（プロジェクトルートに .env / .env.local がある場合）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方

主要なコマンド例

- 設定ウィザード（.env を作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更: export MONITOR_POLL_INTERVAL=30
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは一元管理）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient（ペーパートレード）を使用し、data/paper_trading.db に記録します
  - 停止フラグ: data/stop_requested.flag / data/kill.flag の存在で挙動を制御

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / リサーチ関数の呼び出し（Python から直接）
  - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - 各関数に DuckDB 接続と target_date を渡して使用

注意点 / 環境変数の要点
- KABUSYS_ENV: development | paper_trading | live（必須ではないが適切に設定推奨）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD は必須（.env で設定）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject）
- LOG_DIR, LOG_LEVEL: ログの場所・レベルを制御
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

停止 / Kill Switch の仕組み
- KillSwitch は RiskMonitor 等の出力に基づき data/kill.flag に理由を書き込みます
- ExecutionEngine は起動時に kill_flag_clear_on_start（.env）に応じて kill.flag をクリアできます（本番では通常 0 を推奨）
- 強制停止リクエスト（手動）には data/stop_requested.flag を作成することで run_monitoring や run_execution のループを終了させられます

ログ
- デフォルトは logs/<app_name>.log（TimedRotatingFileHandler により日次ローテーション、30日保持）
- コンソール出力は stdout に統一

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要なモジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                - 環境変数 / .env の読み込みと Settings
  - config_setup.py          - .env 対話式ウィザード
  - validate_config.py       - 設定検証 CLI
  - run_monitoring.py        - SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         - ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       - 共通ログ設定ユーティリティ
    - process_priority.py    - プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       - SQLite スキーマ・永続化 API
    - monitoring_engine.py   - 各 Monitor の統合処理
    - system_monitor.py      - システム状態・データ鮮度チェック
    - trade_monitor.py       - 注文・約定監視（ソース参照）
    - risk_monitor.py        - ドローダウン・ポジション数監視
    - kill_switch.py         - kill.flag 管理
    - alert_manager.py       - （アラート送信ロジック）
  - execution/
    - execution_engine.py    - 実行エンジン（注文セッション管理）
    - broker_factory.py      - BrokerClient の生成（本番 / paper 切替）
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
  - ai/
    - news_nlp.py            - ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     - 市場レジーム判定（OpenAI + ETF MA）
  - data/                   - デフォルトの DB / PID / flag が作成される場所（実行時に生成）
  - tools/
    - paper_verification_report.py

（上記は抜粋です。実際のファイルやサブモジュールはソースツリーを参照してください）

---

## 補足・運用上の注意

- 監視（Monitoring）は常に本番用の sqlite_path を参照する設計（環境に依らず監視ログを一元化）。Execution は KABUSYS_ENV により paper/live を分離します。
- OpenAI 等外部 API を利用する機能は、APIキーや利用制限に注意してください。失敗時はフェイルセーフ（0.0 など）で継続する設計ですが、運用判断が必要です。
- データ鮮度やログ出力は運用時に重要です。LOG_DIR、LOG_LEVEL を適切に設定して運用してください。
- 本番環境では KILL_FLAG_CLEAR_ON_START=0（自動クリア無効）を推奨します。誤った自動クリアは致命的な停止回避の無効化を招きます。
- .env は機密情報（API トークン・パスワード）を含むため、絶対にリポジトリにコミットしないでください。

---

必要な箇所の補足や README に含めたい運用手順（systemd / supervisor の unit ファイル例、CI/CD の設定、運用チェックリスト等）があれば教えてください。README に追記して作成します。