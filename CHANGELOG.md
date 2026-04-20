# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

なお、本 CHANGELOG はリポジトリ内のソースコードを読んで推測した変更点・機能一覧です（自動生成）。実際のリリースノートと差異がある可能性があります。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-20

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基礎機能を実装。
- 実行/監視用エントリポイントスクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db を利用。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag による停止検知、PID ファイル data/execution.pid の利用。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値はデフォルトにフォールバック）。
    - 監視は常に本番用 sqlite_path を使用（環境に依存せず）。
- 設定管理・ウィザード・検証ツールを追加
  - config.py
    - .env 自動読み込み（プロジェクトルートの特定: .git または pyproject.toml を基準）。
    - .env / .env.local の読み込み順序と上書きポリシー（OS 環境変数を保護）。
    - 環境変数パーサ（クォート処理、コメント処理、export KEY= 値対応）。
    - Settings クラスで各種設定値をプロパティとして提供（J-Quants、kabu API、DB パス、監視閾値、env 判定等）。
    - PAPER_FILL_MODE のバリデーションを実装（instant|partial|never|reject）。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザード。
    - デフォルト値・シークレットマスク表示・確認プロンプト付きで .env を生成。
    - .env に保存する際、書式と注意書きを出力（.env を Git にコミットしない旨を明記）。
  - validate_config.py
    - 起動前の設定検証 CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がない場合は警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築・リスク調整・ポジションサイジングの純粋関数モジュールを追加
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート + タイブレーク。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重（スコア全0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用（unknown セクターは除外しない挙動）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数算出、単元（lot_size）丸め、aggregate cap（available_cash）に応じたスケーリングと残差配分ロジック。
    - cost_buffer を考慮した保守的見積りの実装。
    - TODO コメントで将来的な銘柄別 lot_size 対応等の拡張を示唆。
- ロギング・プロセス制御ユーティリティを追加
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）をルートロガーに設定する共通ユーティリティ。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
  - utils/process_priority.py
    - プラットフォーム差（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を設定するヘルパーも実装。
    - アクセス権限や未対応 OS の場合は警告ログを出力してスキップ。
- 監視・実行エンジンの DB 初期化と DuckDB 統合
  - 監視用 sqlite に対する init_monitoring_db 呼び出し（冪等で監視テーブル存在を保証）。
  - DuckDB との接続を受け渡し、分析処理等に利用する設計を用意（duckdb_path を設定で指定）。
- Paper Trading 向け検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB（デフォルト data/paper_trading.db）から期間内の指標を集計してレポート出力（稼働率、注文成功率・送信率、リスク却下数、レイテンシ指標）。
    - P95 計算、フィルタ（from/to）、NULL 対応、閾値判定（PASS/FAIL）を実装。
- research/factor_research.py（計算モジュール骨格）
  - モメンタム・ボラティリティ等のファクター計算の方針と定数を実装（DuckDB の prices_daily / raw_financials を参照する想定）。一部関数実装中（途中のファイル構成を含む）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- 複数の堅牢性向上処理を実装
  - MONITOR_POLL_INTERVAL が不正な値のときに警告を出してデフォルトにフォールバック。
  - .env 読み込みでファイルオープン失敗時に warnings.warn を出力して継続。
  - logging_setup でログディレクトリ作成失敗時に stderr に警告出力しファイル出力を無効化。
  - process_priority のプラットフォーム未対応やアクセス拒否時に警告を出して処理をスキップ。
  - position_sizing 等で価格欠損時にスキップすることで例外発生を防止。
  - apply_sector_cap は "unknown" セクターの扱いを明確化（上限適用除外）。

### Known limitations / Notes
- position_sizing の単元 (lot_size) は現状グローバル共通値（デフォルト 100）。将来は銘柄別単元対応を検討。
- apply_sector_cap の価格欠損（price=0.0）の場合、実際のエクスポージャーが過少見積りとなる旨の TODO コメントあり（フォールバック価格の導入が望まれる）。
- research/factor_research.py はファクター計算の骨格と定数を定義しているが、ファイル末尾に未完の実装断片あり（引き続き実装が必要）。
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップする仕様のため、配布後やテスト環境で注意が必要。
- 本リリースではセキュリティ上の注意事項として .env の Git 管理を禁止するメッセージを出力しているが、運用での取り扱いに注意すること。

---

以上がソースコードから推測して作成した CHANGELOG（初回リリース: 0.1.0）です。実際のリリースノートや配布物に合わせて日付・内容の調整を推奨します。必要であればセクション分けや各ファイルごとのより詳細な変更点リストも生成できます。