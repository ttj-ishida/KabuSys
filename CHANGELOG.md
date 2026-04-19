Keep a Changelog
================

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従います。  

[Unreleased]
------------

（現時点の提供コードベースは初期リリース相当の機能群を含んでいるため、Unreleased セクションに未反映の変更はありません）

0.1.0 - 2026-04-19
-----------------

Added
- 全体
  - 初期リリース。モジュール構成を整理し、自動売買システムのコアユーティリティ、実行エンジン起動スクリプト、監視スクリプト、設定管理、ポートフォリオ構築ロジック、解析ツールなどを実装しました。
  - バージョン情報をパッケージに追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 設定管理・起動支援
  - .env ファイルの自動読み込み機能を実装（プロジェクトルートの .env/.env.local を読み込み、既存 OS 環境変数を保護）。（src/kabusys/config.py）
  - .env パーサーの強化:
    - export KEY=val 形式、シングル/ダブルクォート値、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。（src/kabusys/config.py）
  - Settings クラスを実装。各種環境変数をプロパティで取得し、基本的な妥当性チェック（enum 検証や型変換）を行う。（src/kabusys/config.py）
  - 対話式の環境設定ウィザードを追加（.env の初期作成・更新支援）。項目定義・既存値の読み込み・確認・書き込みをサポート。（src/kabusys/config_setup.py）

- 設定検証
  - validate_config CLI を実装。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば）などをチェック。--strict モードで警告を失敗扱いに可能。（src/kabusys/validate_config.py）

- ロギング・プロセス管理
  - 統一ログ設定ユーティリティを実装。コンソール(stdout)出力と日次ローテーションファイル出力（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。（src/kabusys/utils/logging_setup.py）
  - プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS の差分を吸収し、psutil を用いてプロセス優先度(nice/HIGH_PRIORITY_CLASS)や CPU affinity を設定。権限不足時は警告して安全にスキップ。（src/kabusys/utils/process_priority.py）

- 実行エンジン / 監視
  - 実行エンジン起動スクリプトを実装。KABUSYS_ENV=paper_trading の場合は paper 用専用 SQLite を使用し、本番 DB と分離する挙動をサポート。BrokerClientFactory によりブローカークライアントを生成し、ExecutionEngine をスレッドで実行、停止フラグと pid ファイルを扱う。（src/kabusys/run_execution.py）
  - 監視ループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検出、監視 DB 初期化、例外保護、DBクローズ処理など。（src/kabusys/run_monitoring.py）
  - 監視 DB 初期化呼び出しと DuckDB 接続の確立を両起動スクリプトで行う（monitoring は環境に関わらず本番 sqlite_path を使用する旨を明示）。

- ポートフォリオ構築（純関数群）
  - 候補選定: 信号のスコア降順＋タイブレーク（signal_rank）で上位 N 件を選ぶ select_candidates を実装。（src/kabusys/portfolio/portfolio_builder.py）
  - 重み計算: 等金額配分 calc_equal_weights とスコア加重 calc_score_weights（全銘柄スコアが 0 の場合は等金額へフォールバック）を実装。（src/kabusys/portfolio/portfolio_builder.py）
  - セクター制約: apply_sector_cap を実装。既存保有のセクター別エクスポージャーを算出し、max_sector_pct を超えるセクターから新規候補を除外（unknown セクターは制限適用外）。売却予定銘柄をエクスポージャー計算から除外するオプションあり。（src/kabusys/portfolio/risk_adjustment.py）
  - レジーム乗数: calc_regime_multiplier を実装（bull/neutral/bear → 1.0/0.7/0.3、未知レジームは 1.0 でフォールバック・警告）。設計注記あり。（src/kabusys/portfolio/risk_adjustment.py）
  - 株数算出: calc_position_sizes を実装。allocation_method ("risk_based"/"equal"/"score") に対応し、単元株(lot_size)丸め、1銘柄上限(max_position_pct)、aggregate cap (available_cash) によるスケーリング、cost_buffer を用いた保守的見積もり、端数調整ロジックを持つ。（src/kabusys/portfolio/position_sizing.py）
  - モジュール再エクスポートを配置し、外部から主要関数を簡単に利用可能にした。（src/kabusys/portfolio/__init__.py）

- リサーチ（ファクター群）
  - factor_research の骨組みと定数を追加。モメンタム・MA200 乖離・ATR・流動性指標算出方針を記載。DuckDB 接続を受け取り prices_daily/raw_financials に依存する計算を行う設計。calc_momentum の実装を開始（関数ドキュメントと定数が含まれるが、実装は継続の必要あり）。（src/kabusys/research/factor_research.py）

- ユーティリティ・ツール
  - Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率・送信率、リスク却下数、平均/最大/P95 レイテンシなどを集計して PASS/FAIL 判定を行う。日付フィルタ、DB パス指定オプション、P95 計算、テーブル欠損時の堅牢性対応を含む。（src/kabusys/tools/paper_verification_report.py）

Changed
- （初期リリースのため大幅な変更履歴なし。実装上の設計注記や TODO をソース内に残しています。例: position_sizing の lot_size 将来拡張、risk_adjustment の price 欠損時の扱いなど。）

Fixed
- （初期リリースのため既知のバグ修正履歴はなし。run_* スクリプトは DB のクローズや例外ログ出力、停止フラグ検出の堅牢化を行っています。）

Notes / Known limitations
- factor_research.calc_momentum は実装の続きが必要（ファイル末尾が切れている状態のため、完全動作には追加実装が必要）。設計ドキュメント参照。
- 一部のロジックは外部コンポーネント（BrokerClientFactory, ExecutionEngine, SystemMonitor 等）に依存しており、それらの詳細実装が別モジュールに存在することを前提としています。
- process priority / cpu affinity の設定は権限や OS の違いで失敗し得ます。失敗時は警告を出して処理を継続するよう安全化済み。
- .env の自動ロードはプロジェクトルート検出に依存。ルートが見つからない場合は自動ロードをスキップします。
- Paper Trading と本番 DB の分離を意図していますが、運用前に validate_config で設定検証を行ってください。

今後の予定（短期）
- factor_research の完全実装（各ファクター計算の SQL / Python 実装）
- ExecutionEngine / Broker クライアント周りのテスト整備とフェイルセーフ強化
- 単体テスト・CI の整備、config ファイルの型検証強化（YAML schema 等）

--- 

この CHANGELOG は、現行のソースコードから推測可能な変更点・機能を基に作成しています。詳細なリリースノートやユーザー向けの更新履歴は、実際のコミット履歴・リリース手順に応じて補完してください。