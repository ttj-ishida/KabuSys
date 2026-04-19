CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-19
--------------------

初回リリース。主要な機能・ユーティリティ群を実装しました。

Added
- 全体
  - パッケージ初期バージョンを 0.1.0 として公開（src/kabusys/__init__.py）。
- 設定管理
  - Settings クラスを実装し、環境変数経由で各種設定を取得できるようにしました（src/kabusys/config.py）。
    - J-Quants / kabuAPI / LINE / DBパス / 監視しきい値 / ログ・環境種別などをプロパティで提供。
    - KABUSYS_ENV（development / paper_trading / live）・LOG_LEVEL 等の妥当性チェックを実装。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の paper_trading 向け設定に対応。
  - .env 自動ロード機能を導入（プロジェクトルートに基づき .env → .env.local の順、OS 環境変数を保護）。
  - 高度な .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントルールをサポート）。
- 設定支援 CLI
  - 対話式環境設定ウィザードを追加（python -m kabusys.config_setup）。
    - .env の生成・更新を支援。シークレット項目はマスク表示。
  - 設定検証ツールを追加（python -m kabusys.validate_config）。
    - 必須環境変数のチェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パス・config/*.yaml の存在/パースチェック、live 環境時の注意喚起等を実行。
    - --strict オプションで警告を FAIL 扱いにできる。
- 起動スクリプト / 実行エンジン
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - プロセス優先度を起動直後に high に設定。
    - paper_trading 環境では paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を構成して ExecutionEngine を起動。
    - 実行中は stop フラグ（data/stop_requested.flag）を監視し、安全に停止可能。
    - PID ファイル出力（data/execution.pid）をサポート。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB の分離に留意）。
    - stop フラグ検知でループ終了、KeyboardInterrupt による終了処理を実装。
    - check_once の例外をキャッチしてループ継続（単一ポーリングでの障害耐性を向上）。
- ロギング / 運用ユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力( stdout ) と 日次ローテートのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続。
    - ログレベル/ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows (psutil の優先度定数) と POSIX (nice 値) を吸収して呼び出し元を単純化。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。権限不足や未対応 OS では警告を出してスキップ。
- ポートフォリオ構築（純関数群）
  - 銘柄選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
    - 同スコア時は signal_rank によるタイブレークを実装。全スコアが 0 の場合は等金額にフォールバックして警告を出力。
  - セクター制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）。
    - 既存保有のセクター暴露を計算し、max_sector_pct を超えるセクターから新規候補を除外（"unknown" セクターは除外対象外）。
    - レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームは 1.0 でフォールバックして警告。
  - 株数決定・投資上限ロジック: calc_position_sizes（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1銘柄上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer（手数料・スリッページ見積り）を加味した保守的算出を実装。
    - 利用可能現金を超過する場合はスケールダウンし、端数は残差に基づいて lot_size 単位で再配分する。
- 研究モジュール（途中実装）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / MA / ATR / Volume 系の指標を DuckDB の prices_daily テーブルから計算する設計（calc_momentum 等、仕様記述あり。実装はファイル末尾で未完）。
- Tools
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - SQLite（デフォルト data/paper_trading.db）からシステム稼働率・注文成功率・送信率・レイテンシ等を集計して、PASS/FAIL を判定。
    - P95 計算、欠損テーブルに対する堅牢なフォールバック（OperationalError を捕捉）を実装。
    - デフォルトの閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。

Changed
- （初回リリースのため履歴無し）

Fixed
- （初回リリースのため履歴無し）

Deprecated
- （初回リリースのため履歴無し）

Removed
- （初回リリースのため履歴無し）

Security
- （初回リリースのため履歴無し）

注記
- 各スクリプト・モジュールは本番運用を想定した安全弁（stop flag の監視、例外捕捉、ログ出力の堅牢化）を備えていますが、本番環境での運用前に設定（.env、config/*.yaml、LINE 通知設定等）の十分な検証を行ってください。
- .env は決してリポジトリにコミットしないでください（config_setup のヘッダにも記載）。
- ファイルによっては未実装・ TODO コメントが残っている箇所があります（例: factor_research の続き、price のフォールバックロジックなど）。今後のリリースで改善予定です。

--- 

（参考）リンク等を追加する場合は下記の形式で追記してください：
[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0