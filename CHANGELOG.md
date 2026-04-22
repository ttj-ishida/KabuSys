# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（無し）

## [0.1.0] - 2026-04-11

初回リリース。自動売買システム KabuSys のコアユーティリティ、実行/監視エントリポイント、設定管理、ポートフォリオ構築ロジック、検証ツール等を実装しました。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV による paper_trading の切り替えをサポートし、paper_trading 環境時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - ブローカークライアント生成を BrokerClientFactory で抽象化。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせてエンジンを起動。EngineConfig / pid ファイル対応。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 初期化（init_monitoring_db）を行い、監視は環境にかかわらず本番 sqlite_path を参照。
    - 停止フラグ検知でループ終了、KeyboardInterrupt ハンドリングによる終了処理。

- 設定管理と CLI
  - config.py
    - .env 自動ロード（.env / .env.local）を実装。OS 環境変数は保護され上書きされない。
    - .env 行パーサ _parse_env_line を実装（export 形式、クォート、エスケープ、インラインコメント対応）。
    - Settings クラスを実装し、アプリケーション設定をプロパティで公開（J-Quants / kabu API / DB パス / 各種しきい値など）。
    - PAPER_FILL_MODE や KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
  - config_setup.py
    - .env を対話的に生成・更新するウィザードを追加（項目一覧、masked 入力、既存値の再利用、保存機能）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数のチェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガード。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 全起動スクリプトで共通に使えるログ設定を追加。
    - stdout 出力用 StreamHandler と日次ローテーション（TimedRotatingFileHandler）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル / 出力先解決順は引数 > 環境変数 > デフォルト。
  - utils/process_priority.py
    - psutil を使ったプロセス優先度設定を追加（Windows / POSIX 差分を吸収）。
    - set_cpu_affinity による CPU ピン留め機能を実装（存在しない環境では安全にスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア重み（calc_score_weights）を実装。スコア合計が 0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装。既存保有のセクター別時価を計算し、閾値超過セクターの新規候補を除外（unknown セクターは除外対象としない）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: risk_based / equal / score）。
    - 損切り率・risk_pct に基づく risk-based 計算、単元株（lot_size）での丸め、1 銘柄上限・aggregate cap（available_cash）でのスケーリング、cost_buffer を考慮した保守的なコスト見積り、端数処理（残差に基づく追加配分）を実装。

- データ解析 / レポートツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite DB を集計して検証レポートを出力する CLI を追加。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出。閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき PASS/FAIL を判定。
    - --from / --to / --db オプションにより期間・DB を指定可能。DB が存在しない場合は明示的なエラーメッセージを出力。

- 研究モジュール（下地）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（モメンタム、MA、ATR、ボラティリティなどの定義と設計方針）。calc_momentum などの実装が始まっている（ファイル末尾で未完の状態あり）。

- パッケージ定義
  - __init__.py にバージョン 0.1.0 と主要サブパッケージのエクスポートを追加。

### Changed
- ロギングの動作方針
  - console ログは stderr ではなく stdout を使用するように変更（cron 等からのリダイレクトで扱いやすくするため）。
- DB 初期化
  - run_execution/run_monitoring 起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等処理）。

### Fixed
- .env パーサの堅牢性向上
  - export 付き行、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い、未設定行のスキップ等を正しく処理するように修正。

### Notes / Implementation details
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行い、プロジェクト外でパッケージが使われる場合は自動ロードをスキップします。自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- paper_trading 環境は本番データベースと完全分離される設計です（専用 SQLite を使用）。
- process_priority や CPU affinity の設定は権限や OS に依存するため、失敗時は警告を出しスキップします（安全性重視）。
- 一部モジュール（研究モジュールなど）は今後の追加実装・拡張が予定されています。

### Security
- .env ファイルは絶対にバージョン管理にコミットしない旨の注記を config_setup で強調しています。

---

今後の予定（例）
- research/factor_research の完実装（momentum 等の計算完成）
- ExecutionEngine / SystemMonitor のユニットテスト追加
- BrokerClient の具体実装と paper_trading のモック挙動改善
- config/*.yaml のサンプル自動生成スクリプト強化

（必要があれば、各変更のトランク化差分やさらに詳細な設計メモを追記します。）