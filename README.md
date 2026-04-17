README.md

概要
- KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。
- 主な機能は、ExecutionEngine（発注実行）および Monitoring（稼働監視）、ファクター計算・リサーチ、ポートフォリオ構築、AI ベースのニュースセンチメント解析などです。
- 設計方針のポイント:
  - 本番とペーパートレードは DB を分離（paper_trading モードでは data/paper_trading.db を使用）。
  - 監視は本番の monitoring DB を参照して動作（環境に依存しない）。
  - OpenAI を用いる AI 機能は API キーを環境変数で与える（失敗時はフェイルセーフ）。
  - .env による設定管理、config_setup で対話的に .env を作成可能。

主な機能一覧
- 実行系
  - run_execution: ExecutionEngine を起動し、ブローカークライアント経由で注文を処理（KABUSYS_ENV によりペーパートレード/本番切替）。
- 監視系
  - run_monitoring: SystemMonitor をポーリングしてシステム状態・データ鮮度を記録・アラート発火。
  - monitoring_engine: 複数 Monitor をまとめて周期実行、Kill Switch 判定、LINE 通知管理。
  - SystemMonitor / TradeMonitor / RiskMonitor: CPU/memory/disk、滞留注文、ドローダウン等の判定。
  - monitoring_db: SQLite に監視ログ・トレードログ等を永続化。
- 設定・ユーティリティ
  - config_setup: .env を対話式に作成/更新するウィザード。
  - validate_config: .env と config/*.yaml の基本チェックを行う CLI。
  - utils/process_priority: プラットフォーム間の差分を吸収してプロセス優先度や CPU Affinity を設定。
- 研究・ポートフォリオ
  - research.factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB ベース）。
  - portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数。
- AI 関連
  - ai.news_nlp: OpenAI を用いたニュースの銘柄別センチメント算出と ai_scores への書込み。
  - ai.regime_detector: ma200 とマクロニュースを組み合わせて市場レジーム判定。
- ツール
  - tools.paper_verification_report: ペーパートレード DB から動作検証用レポートを生成。

セットアップ手順
1. リポジトリをクローンし、python 仮想環境を作成
   - python3 -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - 少なくとも以下をインストールしてください（requirements.txt があればそれを使用）。
     - duckdb
     - psutil
     - openai
     - requests
     - PyYAML（config の YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai requests PyYAML

3. data ディレクトリ作成（必要に応じて）
   - mkdir -p data

4. .env の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI 利用時は:
     - OPENAI_API_KEY を環境変数に設定するか、呼び出し側で渡す

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - 監視用 SQLite（デフォルト: data/monitoring.db）は起動時に自動でテーブル作成（init_monitoring_db）されます。
   - ペーパートレード用 DB（KABUSYS_ENV=paper_trading 時のデフォルト: data/paper_trading.db）も実行時に使用されます。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能で使用）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db） — Monitoring は環境に関わらず本番 sqlite_path を参照します
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB。デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（ペーパートレードの約定動作: instant|partial|never|reject）
- KABUSYS_ENV（development|paper_trading|live、デフォルト: development）
- LOG_LEVEL（DEBUG|INFO|...、デフォルト: INFO）
- PID_FILE_PATH（ExecutionEngine の pid ファイル、デフォルト: data/execution.pid）
- KILL_FLAG_PATH（Kill Switch のフラグファイル、デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか: 0|1。production は 0 推奨）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト: 60）

使い方（主なコマンド）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成すると監視ループが検知して停止します。

- 実行エンジンの起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 実行中は PID ファイル（data/execution.pid がデフォルト）を使用。停止は data/stop_requested.flag を作成するか、Kill Switch（監視側が kill.flag を書き込む）で制御されます。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI 機能（ニューススコア / レジーム判定）
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をコードから呼び出す際は OpenAI API キーを渡すか環境変数 OPENAI_API_KEY を設定してください。
  - これらの関数は DuckDB の接続オブジェクトと target_date を受け取り、結果をデータベースへ書き込みます。

運用上の注意
- 監視（Monitoring）は常に Settings.sqlite_path を使用するため、テスト時は設定に注意してください。
- ExecutionEngine は paper_trading モードで DB を分離するため、ペーパートレードと本番のデータが混ざりません。
- プロセス優先度変更（High）を試みますが、権限不足で失敗する場合があります。その場合は警告ログが出ます。
- Kill Switch:
  - RiskMonitor 等の条件により kill.flag（デフォルト data/kill.flag）を書き込むと ExecutionEngine を停止させるトリガになります。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動削除します（本番では 0 を推奨）。

ディレクトリ構成（主要ファイル・モジュール）
- src/kabusys/
  - __init__.py (パッケージ定義)
  - config.py              — 環境変数 / 設定のロードとアクセスラッパ
  - config_setup.py        — .env 作成ウィザード
  - validate_config.py     — 起動前チェック CLI
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py     — SQLite の監視テーブル定義・アクセス
    - system_monitor.py    — CPU/メモリ/ディスク・データ鮮度監視
    - trade_monitor.py     — 滞留注文 / 約定異常監視
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag 書き込みユーティリティ
    - alert_manager.py     — LINE 通知用（HTTP push）
    - monitoring_engine.py — 複数 Monitor を束ねる
  - execution/              — ExecutionEngine 関連（Engine、OrderManager 等、実装は別ファイル）
  - portfolio/
    - portfolio_builder.py  — 候補選定 / 重み計算
    - position_sizing.py    — 発注株数計算
    - risk_adjustment.py    — セクター上限・レジーム乗数
  - research/
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py           — ニュースセンチメント取得（OpenAI）
    - regime_detector.py    — ma200 + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - data/                   — データファイル（DB、PID、フラグファイル等）を置く想定ディレクトリ（リポジトリ外に配置しても可）

追加情報
- ログ出力は基本的に標準出力（logging.basicConfig で INFO レベルがデフォルト）です。運用では systemd / supervisor / Docker ログ収集と合わせて使うことを想定しています。
- DuckDB と SQLite を併用しています。DuckDB は主に分析・リサーチ用テーブル（prices_daily, raw_financials 等）を想定しています。
- テスト／CI のため、config 内に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動で .env を読み込まないようにできます。

ライセンス・貢献
- （このリポジトリにライセンスファイルがあればその記載に従ってください）

問題報告・改善提案
- バグや使い勝手の改善は Issue を立てるか、Pull Request を送ってください。README の補足やサンプル .env.example の追加は歓迎です。

以上。README に追加したい具体的なコマンド例や .env のサンプル（例: .env.example）を希望する場合は教えてください。