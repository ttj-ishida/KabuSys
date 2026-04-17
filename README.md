# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ兼実行スクリプト群）。

このリポジトリは取引エンジン、監視、リサーチ、AI（ニュース／レジーム判定）、ポートフォリオ構築などの主要機能をモジュール化して提供します。各モジュールは可能な限り副作用を避け、単体でのテストや再利用がしやすい設計になっています。

バージョン: 0.1.0

## 主な機能
- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
  - 本番 / ペーパートレード（MockBroker）を環境で切替
  - リスク管理（RiskManager）、注文管理、再整合（Reconciler）を組み合わせて実行
  - 停止フラグ（data/stop_requested.flag）で外部から停止可能
- 監視プロセス（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク、プロセス存在、データ鮮度を監視
  - TradeMonitor：滞留注文・約定価格異常を検出
  - RiskMonitor：ドローダウン・ポジション上限監視、Kill Switch 連携
  - MonitoringEngine：上記をまとめてポーリング・アラート発行
- 環境設定ウィザード（config_setup）と設定検証（validate_config）
  - .env の対話的作成/更新
  - 起動前チェック（必須環境変数、ファイルパスや YAML の存在チェック等）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report）
  - ペーパートレード DB から稼働率・注文成功率・レイテンシ等を集計
- リサーチモジュール（research）
  - ファクター（モメンタム / ボラティリティ / バリュー）計算
  - 特徴量探索、IC（Information Coefficient）計算など
- AI モジュール（ai）
  - news_nlp: OpenAI を用いたニュースセンチメント集計（ai_scores へ書き込み）
  - regime_detector: ETF MA とマクロニュースを合成した市場レジーム判定
- ポートフォリオ構築（portfolio）
  - 銘柄候補選定、重み計算、ポジションサイズ算出、セクター上限適用 等
- ユーティリティ
  - process_priority: プロセス優先度 / CPU affinity 設定（Windows/Linux 抽象化）
  - monitoring_db: SQLite を使った監視ログ永続化レイヤ

## 動作要件
- Python 3.10 以上（型注釈に | を使用）
- 推奨パッケージ（主な依存）
  - duckdb
  - psutil
  - openai
  - sqlite3（標準）
  - PyYAML（config 検証で optional）
- ※ requirements.txt は本コードに含まれていません。必要に応じて上記パッケージをインストールしてください。

例:
pip install duckdb psutil openai pyyaml

## セットアップ手順（概要）
1. リポジトリをクローン / checkout
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai pyyaml
4. .env を作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - または手動でルートの .env を作成（.env.example を参照）
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
6. データディレクトリ作成（必要なら）
   - mkdir -p data

注: config_setup はプロジェクトルート（.git または pyproject.toml を基準）を検出して .env を作成します。

## 主要な環境変数（概要）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行関連
  - KABUSYS_ENV — 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
    - paper_trading: MockBroker 使用、ペーパートレード専用 DB に記録
  - LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- Paper Trading
  - PAPER_FILL_MODE — ペーパートレードの約定モード（"instant" | "partial" | "never" | "reject"）
- OpenAI
  - OPENAI_API_KEY — news_nlp / regime_detector 等で使用
- 監視 / 制御
  - PID_FILE_PATH — execution.pid ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — kill.flag（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1" = true）
  - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

自動 .env ロード:
- 起動時にプロジェクトルートが検出されると .env を自動で読み込みます（.env → .env.local、OS 環境変数を保護）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 使い方（実行例）
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - ペーパートレードで起動するには .env で KABUSYS_ENV=paper_trading を設定
  - 停止：実行中にリポジトリルート下の data/stop_requested.flag を作成すると安全に停止します
  - 実行中は data/execution.pid に PID が書かれる（存在チェックにより stale PID を検出）
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 停止：data/stop_requested.flag による検知や Ctrl+C（KeyboardInterrupt）
- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
    - --strict を付けると警告も失敗扱い
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db でパス指定可能。
- ライブラリ関数の利用例（プログラムから）
  - AI: from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定: from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - ポートフォリオ: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - 監視エンジン単体起動（テスト用）:
    - MonitoringEngine.run_once() を使って単発チェックが可能

## 制御ファイル・フラグ
- data/stop_requested.flag
  - run_execution / run_monitoring がループ中に確認する停止フラグ。存在するとループ終了。
- data/kill.flag
  - KillSwitch（RiskMonitor 等の評価で条件を満たすと生成）により ExecutionEngine 停止を要求するためのファイル。生成は冪等（既存ファイルがあれば上書きしない）。
- data/execution.pid
  - ExecutionEngine の PID を書くファイル。SystemMonitor はこの PID を見てプロセスの生存確認を行う。

## 主要スクリプト一覧（エントリポイント）
- python -m kabusys.run_execution — ExecutionEngine 起動
- python -m kabusys.run_monitoring — SystemMonitor ポーリング起動
- python -m kabusys.config_setup — 対話式 .env 作成・更新
- python -m kabusys.validate_config — 設定検証 CLI
- python -m kabusys.tools.paper_verification_report — Paper Trading 検証レポート

## ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ宣言（バージョンなど）
  - config.py — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/ (実行エンジン関連)
    - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, ...（実行ロジック一式）
  - monitoring/
    - monitoring_db.py — SQLite 監視ログ永続化レイヤ
    - system_monitor.py — システム・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各モニタの束ね役
    - alert_manager.py — （アラート送信管理、未完の実装含む）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（単元丸め・リスク制限）
    - risk_adjustment.py — セクター上限 / レジーム乗数
  - research/
    - factor_research.py — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄別センチメント
    - regime_detector.py — MA と マクロセンチメント合成によるレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

（上記は抜粋です。詳しい実装は各ファイル内のドキュメントコメントを参照してください）

## 運用時の注意点 / 実装上の挙動
- Monitoring は環境に関わらず Settings.sqlite_path（本番 DB）を使用します。Paper Trading 時は run_execution が PAPER_TRADING_SQLITE_PATH を使用して発注ログを分離します。
- .env 自動ロードはプロジェクトルートを .git または pyproject.toml から検出して行います。テストで自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- OpenAI 関連は API キーが必須（api_key 引数または OPENAI_API_KEY 環境変数）。API エラーはリトライ・フォールバックのロジックがありますが、キー未設定の場合は例外となります。
- プロセス優先度設定は psutil を使用し、権限がない場合は警告を出してスキップします。
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能。1 未満や不正値はデフォルト 60 秒にフォールバックします。
- DB マイグレーション（monitoring_db.init_monitoring_db）は起動時に冪等で実行され、必要カラムを追加します。

## トラブルシューティング
- PyYAML が無い場合、validate_config は YAML 内容検証をスキップして警告を出します。
- DuckDB / psutil / openai が未インストールだと該当機能で ImportError が発生します。必要に応じてインストールしてください。
- Kill Switch（data/kill.flag）は本番で誤ってクリアしないよう注意してください。KILL_FLAG_CLEAR_ON_START=1 を本番で設定することは推奨されません（validate_config で警告が出ます）。

---

詳細な API や内部ロジックについては各モジュール（src/kabusys 以下）のファイルヘッダと docstring を参照してください。不明点があればどの機能についての README を作るか指定してください。