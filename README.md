KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買 / 研究用ユーティリティ群を集めたパッケージです。
主要コンポーネントは実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュースNLP／レジーム判定）等です。

主なポイント
- Python パッケージ名: kabusys
- 対応 Python: 3.10+（PEP 604 の型注釈を想定）
- 外部依存（主なもの）: duckdb, psutil, openai, PyYAML（オプション）
- 簡易設定方法: .env ウィザード（config_setup）→ validate_config → 実行スクリプト起動

機能一覧
- 実行エンジン起動スクリプト（run_execution）
  - KABUSYS_ENV に応じて実口座 / ペーパートレードを切り替え
  - Paper Trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離
  - プロセス優先度を「high」に設定し PID ファイルを出力
  - data/stop_requested.flag による外部停止検知
- 監視デーモン起動スクリプト（run_monitoring）
  - SystemMonitor をポーリングして監視ログを SQLite に保存
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視は本番の sqlite_path を使用（環境に依らず）
  - data/stop_requested.flag による停止検知
- 監視ロジック（monitoring package）
  - SystemMonitor: CPU/Mem/Disk/プロセス稼働・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常の検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB: SQLite を使った永続化（テーブル作成・簡易マイグレーション含む）
  - MonitoringEngine: 各 Monitor を束ねてポーリング・アラート発行
- ポートフォリオ構築（portfolio package）
  - 候補選定、等配分／スコア配分、リスク調整（セクター上限・レジーム乗数）
  - 株数決定ロジック（単元丸め・aggregate cap スケーリング）
- リサーチ（research package）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン・IC 計算・ファクター統計サマリ
  - DuckDB を用いた高速 SQL ベース処理を想定
- AI 関連（ai package）
  - news_nlp: raw_news をまとめて OpenAI（gpt-4o-mini）に投げ、銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ETF (1321) MA200 とマクロニュースの LLM 判定を組み合わせて日次レジーム判定（market_regime に書き込み）
  - API 呼び出しは冗長性を考慮したリトライ・バリデーション実装
- ツール
  - paper_verification_report: ペーパートレード DB を解析して稼働率・注文成功率・レイテンシ等の検証レポートを生成
- ユーティリティ
  - logging_setup: コンソール + 日次ローテートログ設定（logs/<app>.log）
  - process_priority: Windows / POSIX を吸収するプロセス優先度・CPU affinity 設定
- 設定支援
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前チェック（必須環境変数・パス・config/*.yaml の存在等）

セットアップ手順（開発・運用共通）
1. Python 環境準備
   - Python 3.10 以上を推奨
   - 仮想環境作成（venv / conda 等）

2. 必要ライブラリをインストール
   - 例:
     pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合はそれを使用）

3. .env を作成
   - 対話ウィザードを使う:
     python -m kabusys.config_setup
   - 必須環境変数
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - AI 関連を使用する場合:
     - OPENAI_API_KEY を設定
   - 自動ロードについて:
     - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動読み込みします
     - テスト等で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

4. 設定検証
   - 設定整合性をチェック:
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

基本的な使い方（起動 / 操作）
- 実行エンジン（ExecutionEngine）を起動
  - 開発（デフォルト .env で KABUSYS_ENV=development）：発注なし（シミュレーション）
  - ペーパートレード:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
  - 本番:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - 起動時に PID を data/execution.pid に書きます
  - 停止: data/stop_requested.flag を作成すると起動中の実行プロセスが検知して停止します

- 監視デーモンを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は monitoring 用 SQLite（Settings.sqlite_path、デフォルト data/monitoring.db）を使用します（環境に依らず本番 sqlite_path を参照）
  - 監視中に data/stop_requested.flag を作成すると監視ループを終了します

- Kill Switch
  - リスク条件（ドローダウン超過、ポジション上限超過等）により data/kill.flag が書き込まれます
  - ExecutionEngine は起動時にこのフラグを確認して停止／起動制御できます
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では 0 推奨）

- ログ
  - デフォルトで stdout にログを出力し、logs/<app>.log に日次ローテーションで保存します
  - ログレベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

主要環境変数（抜粋）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパー取引用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- LOG_LEVEL: ログレベル
- KILL_FLAG_CLEAR_ON_START: 起動時 kill.flag を自動クリアするか（0/1）

データ / 制御ファイル
- data/kill.flag         — Kill Switch が書き込む停止フラグ（ExecutionEngine 側で検出）
- data/stop_requested.flag — 実行スクリプト（run_execution / run_monitoring）を優雅に停止するための外部フラグ
- data/execution.pid     — 実行エンジンの PID を格納
- data/monitoring.db     — 監視ログ（SQLite）
- data/paper_trading.db  — ペーパートレード用（KABUSYS_ENV=paper_trading 時に使用）

開発メモ / 注意点
- config/*.yaml のテンプレートは scripts/generate_config.py で生成できる想定（該当スクリプトがある場合）
- DB マイグレーションは軽微な列追加を init_monitoring_db 内で行っています（冪等）
- AI 関連は OpenAI API の成功を仮定しているため、API キーと通信環境を用意してください。失敗時はフォールバックや部分スキップの挙動を埋め込んでいます
- 自動環境読み込み:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます
  - テストで無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / Settings
    - config_setup.py               — .env 対話式ウィザード
    - validate_config.py            — 起動前チェック CLI
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py                 — ニュース NPL スコアリング
      - regime_detector.py          — 市場レジーム判定
    - monitoring/
      - monitoring_db.py            — MonitoringDB（SQLite）永続化
      - monitoring_engine.py        — 監視ループ統括
      - system_monitor.py           — システム監視
      - trade_monitor.py            — 注文監視（参照）
      - risk_monitor.py             — リスク監視（ドローダウン等）
      - kill_switch.py              — kill.flag 管理
      - alert_manager.py            — アラート送信（未列挙詳細）
    - portfolio/
      - __init__.py
      - portfolio_builder.py        — 候補選定・スコアソート
      - risk_adjustment.py          — セクター上限・レジーム乗数
      - position_sizing.py          — 発注株数決定
    - research/
      - __init__.py
      - factor_research.py          — モメンタム/ボラティリティ/バリュー
      - feature_exploration.py      — 将来リターン/IC/統計
    - tools/
      - __init__.py
      - paper_verification_report.py — ペーパートレード検証レポート
    - utils/
      - __init__.py
      - logging_setup.py            — 統一ログ初期化
      - process_priority.py         — プロセス優先度設定
    - monitoring/…（上記に含む）
    - execution/…（ExecutionEngine 等の実装ファイルが存在する想定）
    - data/…（実行時に作成されるファイル群: logs/, data/ 以下）

よくある操作例
- .env を作って起動前チェック:
  python -m kabusys.config_setup
  python -m kabusys.validate_config

- 監視をデフォルトで起動（60秒間隔）:
  python -m kabusys.run_monitoring

- ポーリング間隔を 30 秒に変更:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジンを起動（ペーパートレード）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポートを生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ / 貢献
- コード改善やバグ修正、ドキュメント補足は Pull Request を歓迎します
- 設計方針や仕様に関する議論は Issues を使ってください

以上。README の内容はコードベースの主要な動作と運用手順を抜粋したものです。運用前に python -m kabusys.validate_config による検証を必ず行ってください。