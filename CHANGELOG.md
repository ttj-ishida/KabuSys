# Changelog

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

### 注意事項 / 既知の制約
- research/factor_research.py の calc_momentum 実装は途中までの状態（ファイル切れ）であり、完全実装が必要です。  
- position_sizing.calc_position_sizes には銘柄ごとの単元情報（lot_size のマスタ対応）など将来的な拡張を示す TODO が残っています。  
- apply_sector_cap は価格データが欠損（0.0）だった場合にエクスポージャーを過少に見積もる可能性がある点が注記されています。

---

## [0.1.0] - Initial release
（初期リリース。バージョン情報は src/kabusys/__init__.py に __version__ = "0.1.0" として含まれます）

### Added
- コア実行スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止管理にプロジェクト直下の data/stop_requested.flag を使用。
    - 監視用 DB は環境に関係なく本番 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグ・PID 管理・スレッド実行のロジックを実装。
- 設定関連
  - config.py
    - 環境変数読み込み・管理用 Settings クラスを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み（.env → .env.local の優先度処理、OS 環境変数保護あり）。
    - .env のパースはクォート・エスケープ・インラインコメント等に対応する堅牢な実装。
    - Paper Trading 関連の設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）をサポート。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加（項目定義、既存 .env 読み込み、保存機能）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在とパースチェック、live 環境向けのガード）。
    - --strict モードで警告を失敗扱いにできる。
- ポートフォリオ構築（純関数群、テスト容易）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。スコア全ゼロ時は等分配にフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap と市場レジーム乗数 calc_regime_multiplier を実装（regime による投下資金調整）。
  - portfolio/position_sizing.py
    - position sizes の計算（risk_based, equal, score の各 allocation_method をサポート）、単元（lot_size）丸め、aggregate cap によるスケールダウンロジックを実装。
  - portfolio/__init__.py で上記 API をエクスポート。
- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）を統一的に設定するユーティリティを追加。LOG_DIR / LOG_LEVEL の解決順をサポート。
  - utils/process_priority.py
    - Windows / POSIX（Linux/Mac/FreeBSD）向けにプロセス優先度（high/normal/low）と CPU affinity 設定を吸収するユーティリティを追加。権限不足等に対しては安全に失敗（警告ログ）する実装。
- Paper Trading / 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95 など）を算出し PASS/FAIL 判定を行う。
    - デフォルト閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を用意。
- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトで呼び出し、監視テーブルの存在を保証（冪等）。
- Execution 関連コンポーネント（参照される API の組み立て）
  - 実行時に BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine を組み立てて起動する流れを実装（実際の各クラス実装は別モジュールに依存）。

### Changed
- （該当なし — 初期リリースとして新規追加が中心）

### Fixed
- （該当なし）

### Security
- .env 作成時の注意喚起（.env を Git にコミットしない旨のヘッダを config_setup が出力）

### Notes / Implementation details
- .env 読み込みは OS 環境変数を保護する設計（protected set を用い、.env.local で上書きする場合でも OS 環境変数は上書きしない）。
- logging_setup はログディレクトリ作成に失敗してもコンソール出力を継続するフォールトトレラントな挙動。
- process_priority は OS による違いを吸収しつつ失敗を警告で済ませるため、権限がない環境でも安全。
- ExecutionEngine の RiskConfig にデフォルト値を設定（max_position_pct, max_utilization, rate_limit_per_sec 等）、初期 available cash を broker.get_available_cash() で取得する設計。
- Paper Trading 用 DB と本番 DB を明確に分離（settings.is_paper に基づき sqlite 接続先を切り替え）。

---

開発・運用者向け補足:
- run_monitoring/run_execution の停止は data/stop_requested.flag（プロジェクトルートの data/ 以下）を作成することで行えます。実行中は PID ファイルが生成される設計（エンジン側で pid_file を管理）。
- validate_config は CI / 起動前チェックに利用できます。--strict モードは本番デプロイ前の厳密チェックに有用です。
- paper_verification_report は Paper Trading の検証基準を出力するため、バックテスト確認やペーパートレード後の品質管理に使用できます。

もし差分（追加・修正・削除）をさらに細かく分割したい場合や、未実装箇所（research.calc_momentum の残り等）を Issue として記載したい場合は、その内容をベースに追記します。