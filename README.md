README — KabuSys

概要
- KabuSys は日本株向けの自動売買および関連ツール群をまとめたパッケージです。
- 主な目的は（1）発注実行エンジン（ExecutionEngine）、（2）システム／取引／リスクの監視（Monitoring）、（3）ポートフォリオ構築・サイズ決定・リスク調整、（4）リサーチ（ファクター計算 / 特徴量解析）、（5）AI を使ったニュースセンチメント評価・レジーム判定、（6）各種運用ユーティリティ／ツール、を提供することです。
- 設計方針の例：
  - 環境依存設定は .env（または環境変数）で管理
  - Paper Trading（ペーパートレード）は本番 DB と分離
  - DuckDB（分析用）と SQLite（監視・ログ用）を併用
  - OpenAI API を用いた NLP 機能は API キー必須、失敗時はフェイルセーフで続行

主要機能
- 実行エンジン（run_execution.py）
  - ブローカークライアント（実口座 or Mock）を生成して注文発行を行う。
  - Paper Trading では専用 SQLite（data/paper_trading.db）に記録して本番 DB と分離。
  - プロセス優先度設定、PID 管理、停止フラグ検知をサポート。

- 監視（run_monitoring.py / monitoring/*）
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、発注ログ、リスク（ドローダウン・ポジション上限）を定期チェック。
  - Kill Switch（data/kill.flag）により ExecutionEngine の停止を指示可能。
  - アラート（AlertManager 経由）と履歴保存（SQLite）を実装。

- ポートフォリオ構築（portfolio/*）
  - シグナルから候補選定、等ウェイト／スコア加重の重み計算、ポジションサイズ算出（lot 単位丸め、aggregate cap/スケールダウン）、セクター制限適用、レジーム乗数計算など。

- 研究用モジュール（research/*）
  - DuckDB の prices_daily / raw_financials 等を参照してモメンタム・ボラティリティ・バリュー等のファクターを計算。
  - 将来リターン計算、IC（Information Coefficient）や統計サマリを提供。

- AI（ai/*）
  - news_nlp: OpenAI（gpt-4o-mini）を用いて銘柄別ニュースを集約してセンチメントスコアを ai_scores テーブルに書込。
  - regime_detector: ETF（1321）の MA 乖離とマクロニュースセンチメントを合成して market_regime を算出・保存。

- ユーティリティ
  - 設定ウィザード（config_setup.py）: 対話式で .env を作成
  - 設定検証（validate_config.py）: .env と config/*.yaml を起動前にチェック
  - 各種ログ/ローテーション設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

セットアップ手順（例）
1. Python 環境
   - 推奨: Python 3.10 以上（typing の表記などに依存しませんが新しめを推奨）
   - 仮想環境作成:
     python -m venv .venv
     source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 主に必要な外部パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の検証で任意に使用）
   - 例:
     pip install duckdb psutil openai PyYAML

   注: requirements.txt はリポジトリに含まれていない想定のため、上記を基に適宜追加してください。

3. .env の準備
   - 対話式ウィザードで初期設定:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参考に各環境変数を設定）
   - 重要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（分析 DB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LOG_LEVEL（例: INFO）

4. 設定検証（起動前推奨）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. ディレクトリ作成（必要に応じて）
   - data/ や logs/ は自動作成されますが、手動で作っておくと権限問題を回避できます:
     mkdir -p data logs

基本的な使い方
- 実行エンジン（Execution）
  - 本番（live）または development / paper_trading に応じて動作：
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - paper_trading モードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます。
  - 停止：
    - 実行中に data/stop_requested.flag が存在すると起動を抑止または停止処理が行われます。
    - モニタ側からの Kill Switch は data/kill.flag を書き込み、ExecutionEngine はそれを検知して停止します。

- 監視プロセス
  - デフォルトは 60 秒ポーリング（MONITOR_POLL_INTERVAL 環境変数で上書き可能）
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を参照してログ保存します（環境にかかわらず）。

- Paper Trading 検証レポート
  - 期間指定してレポートを生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ライブラリ利用例）
  - ニュース・AI スコア付与（DuckDB 接続が前提）:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="sk-...")
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="sk-...")

- コンポーネントをライブラリとして利用
  - ポートフォリオ関数:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - 研究関数:
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

監視・停止フローの概要
- run_monitoring と run_execution はそれぞれ stop_requested.flag を見て外部停止を受け付けます（run_execution は起動時に既にフラグがあれば起動せず終了）。
- KillSwitch（monitoring/kill_switch.py）は RiskMonitor 等の結果に基づき data/kill.flag を作成し、ExecutionEngine の停止を誘発します。
- 実行中の PID 管理は data/execution.pid（設定で変更可）で行われます。

ディレクトリ構成（重要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — Settings クラス（環境変数/.env の読み込み・解釈）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - ai/
    - news_nlp.py — ニュースセンチメント評価（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロ NLP）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — ファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・永続化層
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 取引ログ監視（ファイル内に実装あり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — アラート送信（LINE 等、実装に依存）
  - execution/ (発注関連の実装が含まれる想定)
    - execution_engine.py, order_manager.py, broker_factory.py, order_repository.py, reconciler.py, risk_manager.py など
  - data/（ランタイム）
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 用）
    - kabusys.duckdb（DuckDB）
    - kill.flag、stop_requested.flag、execution.pid などのフラグ/メタファイル
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — 優先度 / affinity ヘルパ
    - ほか共通ユーティリティ

注意事項・運用上のヒント
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しはリトライ／フェイルセーフ実装がありますが、コストやレイテンシには注意してください。
- 本番モード（KABUSYS_ENV=live）での .env 設定は厳重に管理し、KILL_FLAG_CLEAR_ON_START の設定に注意してください（本番では 0 推奨）。
- logging_setup はログディレクトリが作成できない場合、コンソール出力のみで継続します。logs/ のファイル出力が必要な場合は書込み権限を確認してください。
- Paper Trading と本番は DB を分離しているため、検証時に意図せず本番 DB を汚染するリスクは低く設計されていますが、環境変数の設定ミスには注意してください。

貢献・拡張
- 新しいブローカークライアントや戦略モジュールは execution/ 以下に実装し、BrokerClientFactory 等を通じて組込みます。
- ファクター・特徴量追加や DuckDB クエリ追加は research/ 以下へ。DuckDB スキーマ（prices_daily, raw_financials 等）に合わせて実装してください。

ライセンスや作者情報は本リポジトリのルートにあるライセンスファイルを参照してください。

以上。README に加えて実行時のエラーメッセージやログを参考に環境設定を微調整してください。必要であれば README のサンプル .env テンプレートや起動/停止スクリプトの雛形を追記します。希望があれば追記します。