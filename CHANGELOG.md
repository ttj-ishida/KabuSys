# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース日はコードベース内の現行日付（2026-04-18）を使用しています。

全体的な注意:
- 本 CHANGELOG は与えられたソースコードから機能・振る舞いを推測して作成しています。
- バージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に合わせています。

## [Unreleased]

注記 / 既知の改善点（今後の対応候補）
- position_sizing.calc_position_sizes:
  - 価格が欠損（0.0）な場合のフォールバック（前日終値や取得原価を用いる等）が未実装。将来的な拡張を検討中。
- process_priority:
  - 未対応 OS（特殊な POSIX 派生など）では優先度設定がスキップされる旨のログ出力がある。必要に応じて対応 OS の拡張を検討。
- .env 自動ロード:
  - プロジェクトルートが検出できない場合は自動ロードをスキップする。テスト環境等で KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。
- テストやドキュメントの追加（特に各アルゴリズムの数値検証）を推奨。

---

## [0.1.0] - 2026-04-18

Added
- 基本アプリケーション構成（初期リリース）。
  - パッケージエントリポイントとバージョンを定義（src/kabusys/__init__.py）。
- 環境設定管理
  - Settings クラスを実装し、環境変数経由で各種設定（DB パス、API トークン、監視閾値、実行環境フラグなど）を参照可能に。
  - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml）を検出して .env / .env.local を読み込む（OS 環境変数を保護する挙動を持つ）。
  - .env のパースはクォート、エスケープ、コメントなど複数ケースに対応。
- 設定ウィザード CLI
  - config_setup.py に対話式ウィザードを実装。.env の初期作成・更新を支援。
  - 生成される .env テンプレートは機密情報はマスク、Git コミット禁止の注意書きを含む。
- 設定検証 CLI
  - validate_config.py に設定チェック機能を実装（必須環境変数、KABUSYS_ENV 値、DB パス、config/*.yaml の存在とパースなど）。
  - --strict フラグで警告を失敗扱いにできる。
  - PyYAML 未インストール時は YAML 検証をスキップし警告を出す。
- 実行系 / 監視系 スクリプト
  - run_execution.py: ExecutionEngine を起動するランチャー。Paper Trading 環境では専用の SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず監視用 sqlite_path を使用。
  - 両スクリプトとも起動時にプロセス優先度を "high" に設定する呼び出しを行う（utils/process_priority.set_process_priority）。
  - 停止フラグ（data/stop_requested.flag）や PID ファイルの取り扱いを実装。
- データベース連携
  - SQLite と DuckDB の接続を利用（monitoring テーブル保証のための init_monitoring_db 呼び出しを含む）。
- Execution コンポーネント組み立て（run_execution 側）
  - BrokerClientFactory を通じて実際のブローカークライアント／モックを切り替え可能（KABUSYS_ENV により動作）。
  - OrderRepository、OrderManager、RiskManager（RiskConfig）、Reconciler、ExecutionEngine の組み立てと実行スレッド管理実装。
  - RiskConfig の初期パラメータを設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）。
- プロセス管理ユーティリティ
  - utils/process_priority.py にて Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを提供。
  - CPU affinity を設定する set_cpu_affinity 関数を実装（指定されたコア数に固定する。失敗した場合は警告でスキップ）。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で上位 N 件を選択。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分の計算（スコア全0 の場合は等配分へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存保有を考慮して特定セクターの新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知レジームはログ警告の上 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based, equal, score）に基づき、単元株丸めや aggregate cap（利用可能現金に基づくスケーリング）を含めて各銘柄の発注株数を計算。cost_buffer を用いた保守的見積りにも対応。
- リサーチ / ファクター計算
  - research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率の計算（DuckDB の prices_daily を参照）。
    - calc_volatility: ATR、平均売買代金、出来高変化率等を計算する仕組み（skip 条件や NULL 伝播の扱いに注意）。
- ツール
  - tools/paper_verification_report.py:
    - ペーパートレーディングの検証レポート生成 CLI。期間フィルタ (--from, --to)、DB パス指定 (--db) に対応。
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。既定の合否基準をファイル内に定義（稼働率 99% 等）。
    - P95 計算実装およびデータ存在時のフォールバック処理を実装。
- 監視データの初期化
  - monitoring.monitoring_db.init_monitoring_db 呼び出しによる監視テーブル存在保証を行う（冪等処理）。

Changed
- 環境に依存する DB の取り扱いを明確化
  - run_monitoring は KABUSYS_ENV にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用。
  - run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離。
- ログ・警告の強化
  - 環境変数や設定値が不正な場合、詳細な警告 / 例外メッセージを出す（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
  - MONITOR_POLL_INTERVAL の不正値はデフォルトにフォールバックして警告を出すように変更。
- validate_config のチェック項目拡張
  - config/*.yaml の存在確認と（PyYAML が利用可能な場合の）パース検証を追加。
  - 本番環境向けの追加ガード（LINE 通知の設定確認、KILL_FLAG_CLEAR_ON_START の危険性警告）を追加。

Fixed
- 設定ロード・パースの堅牢化
  - .env のクォート内でのバックスラッシュエスケープや行内コメント処理を正確に扱う実装を提供。
  - .env の上書き動作は protected set（OS 環境変数）を保持するように設計（override オプションあり）。
- プロセス優先度設定での例外ハンドリングを追加
  - psutil の AccessDenied 等が発生した場合は警告を出してスキップするようにした（起動失敗を防ぐ）。

Security
- .env ファイルに対する注意喚起を追加（config_setup が生成する .env に警告コメントを付与し、Git にコミットしないよう明記）。

Removed / Deprecated
- 該当なし（初期リリース）。

参考（設計上の備考）
- 多くの関数は DB を直接書き換えず、純粋関数としてメモリ内で計算する設計（portfolio モジュール等）。
- Paper Trading と Live の完全分離を意図した設計（設定による DB 切替、MockBroker の利用）。
- 一部箇所に TODO コメントあり（例: position_sizing の価格フォールバック、銘柄別 lot_size の将来的対応など）。

---

この CHANGELOG はソースコードの現状から機能や意図を推測して作成しています。追加でリリースノート向けに詳細（例: API 仕様、CLI 使用例、既知のバグ一覧等）が必要であれば、その点を教えてください。