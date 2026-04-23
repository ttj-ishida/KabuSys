# CHANGELOG

すべての注目すべき変更をこのファイルに記載します。形式は「Keep a Changelog」に準拠しています。

※ 本ファイルは、提示されたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-04-23

### Added
- 全体
  - 初期パッケージ構成を追加。パッケージ名: `kabusys`（バージョン 0.1.0）。
  - DuckDB / SQLite を併用するデータ管理基盤のサポートを追加。
  - ログ出力の統一ユーティリティを追加（kabusys.utils.logging_setup）。
    - 標準出力（stdout）と日次ローテーションされるファイル出力（logs/<app_name>.log）を自動設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
    - デフォルト保持期間は 30 日。
- 実行・運用用スクリプト
  - run_execution.py: 実際の取引エンジン起動スクリプトを追加。
    - 環境変数 `KABUSYS_ENV=paper_trading` の場合は paper trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory に基づき実際のブローカーまたはモックを切り替え。
    - ExecutionEngine、OrderManager、RiskManager、Reconciler 等のコンポーネントの組立てとデーモンワークスレッド起動ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全な停止処理を実装。PID ファイル出力をサポート。
  - run_monitoring.py: システム監視（SystemMonitor）ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用（監視データを一元化）。
    - 停止フラグの検出および例外発生時のログ出力・継続動作を実装。
- 設定管理・検証
  - kabusys.config: 環境変数・.env ロード・Settings クラスを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local の自動ロードを行う。環境変数で自動ロードを無効化可能（`KABUSYS_DISABLE_AUTO_ENV_LOAD`）。
    - .env パースは `export KEY=val` 形式、引用文字列（シングル/ダブル）およびインラインコメントの扱いに対応。
    - Settings クラスで主要設定（DB パス、API トークン、paper trading 用設定、PID/kill flag パス、閾値等）をプロパティで提供。入力値のバリデーション（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）を行う。
  - kabusys.validate_config: 起動前に .env および config/*.yaml の設定不備を検出する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML があれば実行）を行う。
    - `--strict` オプションで警告を失敗（exit 1）として扱う。
  - kabusys.config_setup: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - 秘匿項目のマスク表示、選択肢/デフォルトのサポート、保存確認、.env のフォーマットで書き出し。
- ユーティリティ
  - kabusys.utils.process_priority: プロセス優先度設定および CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux, macOS, FreeBSD) の差分を吸収して優先度を設定。
    - アクセス権限不足や未対応 OS の場合は警告を記録して安全にスキップ。
  - kabusys.tools.paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を集計して PASS/FAIL を判定。
    - 日付フィルタ（--from/--to）と DB パス指定（--db / 環境変数）をサポート。
    - デフォルトの判定閾値を設定（例: 稼働率 >= 99.0%、注文成功率 >= 90.0% など）。
- ポートフォリオ構築ライブラリ（純関数群）
  - kabusys.portfolio.portfolio_builder: 候補選定と重み計算関数を追加。
    - select_candidates: スコア降順で上位 N を選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分（スコア全 0 の場合は等配分にフォールバック）。
  - kabusys.portfolio.risk_adjustment: セクター集中制限とレジーム乗数を追加。
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を提供（unknown の場合は 1.0 にフォールバック）。
  - kabusys.portfolio.position_sizing: 発注株数算出のロジックを追加。
    - リスクベース（risk_based）および比率ベース（equal / score）配分をサポート。
    - 単元株（lot_size）で丸め、1 銘柄上限・総投入上限（available_cash）のスケール調整、コストバッファ（手数料/スリッページ想定）を考慮。
    - aggregate cap によるスケールダウン後の端数処理（lot 単位で補正）を実装。
- 研究用モジュール
  - kabusys.research.factor_research: モメンタム / ボラティリティ / 流動性 / バリュー等のファクター計算モジュールを追加（DuckDB 接続を受け取り SQL/Python で計算する設計）。（ファイルは計算関数を含む実装が始まっている）

### Changed
- なし（初期リリース）

### Fixed
- .env パーサーの堅牢化
  - 引用付き値のバックスラッシュエスケープや対応する閉じクォート探索、コメント判定の改善を実装。
  - export プレフィックスの許容。
- ロギング設定の堅牢化
  - ログディレクトリ作成/ファイルハンドラ生成に失敗した場合にコンソール出力でフォールバックするように改善。
- process_priority
  - 未対応 OS / 権限不足時に例外で停止させず警告ログでスキップするように改善。

### Notes / Known issues / TODO
- research/factor_research.py: ファイル末尾が途中で切れている（提示されたコードの関係で一部実装が未完の可能性あり）。ファクター計算の完全な実装は要確認。
- position_sizing.calc_position_sizes:
  - 現状 lot_size は全銘柄共通で処理。将来的に銘柄別 lot_size を stocks マスタ等から取得する拡張が想定されている（TODO コメントあり）。
- risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少算出され、上限チェックが甘くなる可能性がある旨の注意コメントあり。前日終値などのフォールバック価格利用を検討予定。
- run_monitoring の仕様:
  - 監視は「環境にかかわらず本番 sqlite_path を使用」となっているため、開発環境での監視データを分離したい場合は設定の見直しが必要。
- テスト・CI:
  - 提示コードにはユニットテストや CI 設定の痕跡がないため、リファクタリングや変更時は手動確認またはテストの追加を推奨。

---

（以降のリリースやパッチはここに追記してください。）