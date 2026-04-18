CHANGELOG
=========

すべての変更は Keep a Changelog の規約に準拠して記載しています。  
セマンティックバージョニングを採用しています。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 初期リリース: KabuSys パッケージ全体を追加
  - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
- 起動スクリプト
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル data/stop_requested.flag による安全停止機構。
    - Monitoring は環境にかかわらず本番用 sqlite_path を使用する実装。
  - run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）・PID ファイル（data/execution.pid）に対応。
- 設定管理
  - config.py：.env ファイルの自動ロード機構を追加（.env < .env.local、OS 環境変数が最優先）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - 複数の設定プロパティ（J-Quants / kabu API / データベース / 監視しきい値 / システム設定等）を提供。
    - paper trading 用の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポート。PAPER_FILL_MODE の妥当性検査あり。
    - KABUSYS_ENV / LOG_LEVEL 等の値検証を実装（許容値チェック、未設定時の例外）。
  - config_setup.py：.env の対話式ウィザードを提供（.env の初期作成・更新支援）。
    - シークレット入力のマスク表示、既存 .env の読み込み、保存確認、.env ファイル書き出しロジックを実装。
- 設定検証 CLI
  - validate_config.py：.env および config/*.yaml の起動前検証ツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML 無ければ警告）を実装。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py：統一ロギング設定ユーティリティを追加。
    - stdout（StreamHandler）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成（失敗時はファイル出力をスキップして stdout のみ）。
    - ログローテーションは日次・30 世代保持。
  - utils/process_priority.py：プロセス優先度・CPU affinity のクロスプラットフォームユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）向けに high/normal/low の優先度設定をラップ。
    - CPU affinity を最初の N コアに固定する機能を提供。
    - 権限不足や未対応プラットフォームは警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py：候補選定および重み算出（等金額・スコア重み）を追加。
    - シグナルのソート基準（score 降順、同点は signal_rank 昇順）を実装。
    - スコア全体が 0.0 の場合は等金額配分へフォールバック（警告出力）。
  - portfolio/risk_adjustment.py：セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加。
    - セクター上限を超える既存保有がある場合、新規候補を除外。
    - regime に基づく乗数を提供（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告のうえ 1.0 でフォールバック。
  - portfolio/position_sizing.py：発注株数決定ロジックを追加（risk_based / equal / score）。
    - 損切り・リスク比率に基づく risk-based 算出、単元株（lot_size）での丸め、1 銘柄上限・総投下上限（aggregate cap）によるスケーリングを実装。
    - cost_buffer を加味した保守的なコスト見積りと残余配分ロジックを実装。
  - portfolio/__init__.py でモジュールを公開。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py：Paper Trading 用の検証レポート生成スクリプトを追加。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ統計（avg/max/P95）を集計して標準出力にレポートを出力。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）で PASS/FAIL 判定を行う。
    - --from/--to/--db の CLI オプションを提供。
- 研究用ファクター計算（未完）
  - research/factor_research.py：モメンタム等のファクター計算枠組みを追加（DuckDB 経由で prices_daily / raw_financials を参照）。
    - 指数・窓長等の定数を定義。関数 calc_momentum の導入（実装途中でファイル末尾が切れているが基盤を追加）。

Changed
- （初回公開のため履歴上の変更はありません）

Fixed
- （初回公開のため既知のバグ修正履歴はありません）

Notes / Implementation details
- .env の自動ロード挙動
  - プロジェクトルートは .git または pyproject.toml を探索して判定。発見できない場合は自動ロードをスキップ。
  - .env のパース実装は export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、およびインラインコメント（クォートなしの '#' の扱い）に対応。
  - .env.local は .env の上書き（OS 環境変数は保護される）。
- ログ出力
  - stdout を用いる設計にしているため、タスクスケジューラや cron でのリダイレクト運用に配慮。
- 実行スクリプトの安全機構
  - stop flag（data/stop_requested.flag）と PID ファイル、kill flag 周りの設定（KILL_FLAG_CLEAR_ON_START）を含む運用ガードを実装。
- 例外 / エラー処理
  - 起動スクリプトは内部例外をログに残してポーリング継続／セッション停止を適切に行うよう設計。

今後の TODO（推奨）
- research/factor_research.calc_momentum 等、研究系関数の完成
- 個別銘柄ごとの lot_size を扱う拡張（stocks マスタの導入）
- 価格欠損時のフォールバック（前日終値・原価）を用いたエクスポージャー計算改善
- ユニットテストの追加（.env パーサ、position sizing、sector cap、report 系など）

リンク
- Keep a Changelog: https://keepachangelog.com/ (形式に準拠して記載しています)