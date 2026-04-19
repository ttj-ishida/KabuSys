# KabuSys

日本株向け自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、取引実行エンジン、監視/アラート、ポートフォリオ構築、ファクター計算、AIベースのニュース評価などを含むモジュール群で構成された自動売買フレームワークです。設計方針としては、テスト可能性・フェイルセーフ・本番/ペーパー分離を重視しています。

バージョン: 0.1.0

---

## 主要機能

- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（KABUSYS_ENV）をサポート
  - Paper Trading 時は MockBrokerClient を用い、data/paper_trading.db に記録（本番 DB とは分離）
  - リスク管理（RiskManager）、注文管理（OrderManager）、和解処理（Reconciler）等と連携

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk/データ鮮度/プロセス生存監視
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン、ポジション上限監視
  - MonitoringEngine によるポーリングと Kill Switch（data/kill.flag）による安全停止
  - 監視ログを SQLite（デフォルト: data/monitoring.db）へ永続化

- Portfolio Construction
  - 候補選定、等金額/スコア加重、セクター制限、レジーム乗数、ポジションサイズ計算
  - 単元株（lot）に合わせた丸めや集約キャップの処理を実装

- Research / Factor 計算
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用した SQL ベース）
  - 将来リターン・IC（Information Coefficient）・統計サマリー等のユーティリティ

- AI モジュール
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースのセンチメントスコアリング（ai_scores への書込）
  - regime_detector: ETF(1321) の MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定

- ツール
  - 設定ウィザード（.env 生成）: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

- 共通ユーティリティ
  - ログ設定（console + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env ローダー（プロジェクトルートを探索して自動読み込み）

---

## セットアップ手順（開発・ローカル実行向け）

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証用。未インストールなら YAML 検証はスキップされます）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを使用してください）

3. .env ファイルを作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example があれば参考にする）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（主要なもの）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用。デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB。デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - OPENAI_API_KEY（AI 機能を使う場合に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/、logs/ などを想定します。ログディレクトリは環境変数 LOG_DIR で変更可能。

---

## 使い方（主要なコマンド）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で切り替え（paper_trading では MockBrokerClient）
  - 停止制御:
    - data/stop_requested.flag が存在すると起動/実行中のループは停止します
    - Kill Switch は data/kill.flag を書き込み（監視側コンポーネントが評価して設定）

- 監視ループ起動（SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒。デフォルト 60）
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依らず）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH で指定可）

- AI / レジームスコア / ニューススコア（プログラム呼び出し）
  - kabusys.ai.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
  - これらは OpenAI API キー（OPENAI_API_KEY）を環境変数または引数で渡す必要があります

---

## 重要な挙動メモ

- DB 分離
  - monitoring（監視）は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用
  - Execution（発注）は本番 / ペーパーで SQLite ファイルを分離（PAPER_TRADING_SQLITE_PATH を使用）

- Kill Switch / Stop 制御
  - data/kill.flag : 監視ロジック（KillSwitch）が特定条件で書き込み、ExecutionEngine に停止シグナルを送る
  - data/stop_requested.flag : run_execution / run_monitoring の外部停止フラグ（存在を検知するとループ終了）

- ログ
  - ログは stdout と日次ローテートファイル（logs/<app_name>.log）に出力
  - ログレベル: LOG_LEVEL 環境変数 または setup_logging() の引数で制御
  - LOG_DIR 環境変数でログ出力先を変更可能

- Process Priority
  - run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（psutil 経由、権限がない場合は警告を出してスキップ）

- AI モジュールの安全策
  - OpenAI 呼び出しはリトライ・バックオフ・バリデーションを行い、失敗時はフェイルセーフ（0.0 等）で継続します
  - レスポンスの JSON 検査・スコアクリッピング（±1.0）を実施

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
  - 環境変数・自動 .env ロード・Settings クラス（アプリ設定）
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py — ログの初期化（console + 日次ローテート）
  - process_priority.py — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 & 永続層
  - system_monitor.py — システム状態・データ鮮度のチェック
  - trade_monitor.py — （コードベースに含まれる）注文監視ロジック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みロジック
  - monitoring_engine.py — Monitor を束ねるポーリングエンジン
  - alert_manager.py —（アラート送信／LINE 等の抽象）
- execution/
  - execution_engine.py — エンジン本体
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py — ニュースセンチメント (OpenAI)
  - regime_detector.py — 市場レジーム判定 (OpenAI)
- data/  （実行時に作成されることを想定）
  - monitoring.db（default）
  - paper_trading.db（paper_trading モード時）
  - kill.flag / execution.pid / stop_requested.flag
- logs/  （ログ出力先、デフォルト）

（上記は主要ファイルのみを抜粋した構成です。詳細はソースを参照してください。）

---

## 開発者向けノート

- DuckDB を使って大量の時系列・ファクタ計算を SQL で効率的に行います。prices_daily / raw_financials / raw_news 等のテーブル設計に依存します。
- 多くの研究系関数（factor_research, feature_exploration）は DuckDB 接続を受け取り、外部副作用を持たない純粋関数群として実装されています。
- 設定の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START の設定に注意してください（デフォルトでは自動クリア無効が推奨）。

---

## よく使うコマンド例

- .env 作成
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config

- 実行エンジン（ペーパー／本番は KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視プロセス起動（ポーリング）
  - python -m kabusys.run_monitoring

- Paper Trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ライセンス / 責任範囲

（この README にライセンス情報は含めていません。利用前にリポジトリの LICENSE ファイルを確認してください。）

本ソフトウェアは投資助言を目的とするものではなく、実運用で利用する場合は十分なテストとリスク管理を行ってください。特に本番（live）モードでは資金・注文が実際に動作します。設定ミスや外部 API エラーによる損失に注意してください。

---

この README は主要な利用フローとアーキテクチャの概要を示しています。詳細は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば、導入手順や設定例（.env テンプレート）、運用手順書を別途作成できます。