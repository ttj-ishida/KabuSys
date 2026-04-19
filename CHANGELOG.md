# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを用います。

ドキュメント作成はソースコードの内容から推測して作成しています。実際のコミット履歴とは差異がある場合があります。

## [Unreleased]

- （現在のコードベースに対する未リリースの変更はありません。次回リリースで反映してください。）

## [0.1.0] - 2026-04-19

初期リリース。日本株自動売買システム「KabuSys」の基盤となるコア機能群を実装しました。

### Added
- 全体
  - パッケージ初期バージョンを `0.1.0` として公開。
  - モジュール構成を整備（execution / monitoring / portfolio / utils / config / tools / research 等を含む）。

- 起動スクリプト / デーモン
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル（data/stop_requested.flag）検知でループを終了。
    - 監視用 DB は環境に依存せず本番用 sqlite_path を使用。
    - プロセス優先度を起動時に "high" に設定。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード用 DB（data/paper_trading.db）に記録して本番 DB と分離。
    - エンジンの PID 管理（data/execution.pid）および停止フラグ検知を実装。
    - プロセス優先度を起動時に "high" に設定。

- 設定・環境変数管理
  - config: 環境変数/ .env 読み込みと Settings クラスを実装。
    - プロジェクトルート検出（.git または pyproject.toml 基準）により .env 自動読み込み（.env.local を優先上書き）。
    - `.env` パースにおいてクォート・エスケープ・インラインコメント等に対する堅牢な実装。
    - 必須変数取得用 `_require()` と `Settings` の各種プロパティ（DBパス、APIトークン、紙取引設定、監視閾値、環境検証等）を提供。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
    - `PAPER_FILL_MODE` の検証（instant/partial/never/reject）。
    - `env` / `log_level` 等の値検証と便利プロパティ（is_live / is_paper / is_dev）。

  - config_setup: .env 作成・更新のための対話式ウィザードを追加。
    - よく使う設定項目のプロンプト、既存 .env の読み込み、シークレット項目のマスク表示、保存機能を提供。

  - validate_config: 起動前に設定不備を検出する検証 CLI を追加。
    - 必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在と（PyYAML があれば）パース検証、`live` 環境向けの追加ガードを実装。
    - `--strict` オプションで警告を失敗扱いにするモードを提供。

- ロギング・プロセス制御ユーティリティ
  - utils.logging_setup: 統一的なログセットアップ関数 `setup_logging()` を追加。
    - コンソール (stdout) と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソール出力のみで継続するフェールセーフを実装。
    - 既存ハンドラの重複登録を防止するためハンドラクリアを実施。
  - utils.process_priority: Windows / POSIX の差分を吸収するプロセス優先度設定ユーティリティを追加。
    - `set_process_priority(level)` で high/normal/low を設定（権限不足等は警告出力してスキップ）。
    - `set_cpu_affinity(cpu_count)` で最初の N コアに固定するヘルパを実装（未対応 OS / 権限不足は警告でスキップ）。

- 監視・モニタリング
  - monitoring_db 初期化ユーティリティ（監視テーブルの作成を保証）。
  - SystemMonitor と連携する監視ループ起動（run_monitoring）。

- 実行エンジン周辺（Execution）
  - BrokerClientFactory によるブローカークライアント生成を想定した実行環境構築。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組立てと起動ロジック（実行スレッド処理、停止検知）。
  - RiskManager 用のデフォルト RiskConfig を実装（最大ポジション比率、利用率上限、レート制限、サーキットブレーカーなど）。initial_portfolio_value を broker.get_available_cash() から初期化。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: スコア降順で候補選定（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額へフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限に基づく候補除外ロジック（sell_codes を除外して既存エクスポージャー計算）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をマップ、未知は警告して 1.0 にフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。
      - 単元株（lot_size）丸め、per-stock 上限 (max_position_pct)、aggregate cap のスケーリングロジック、cost_buffer（手数料・スリッページ見積り）を考慮した保守的な算出と余剰の配分アルゴリズムを実装。
      - 価格欠損時のスキップやログ出力など堅牢性を考慮。

- ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成スクリプトを追加。
    - SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から以下指標を集計してレポート出力:
      - システム稼働率（uptime_pct）、総ポーリング数、エラー数
      - 注文関連: Created/Filled/Sent カウント、注文成功率 (fill_rate)、送信率 (send_rate)
      - リスク却下数（risk_logs）
      - レイテンシ: 平均 / 最大 / P95（P95は独自実装で計算）
    - デフォルトの合格基準 (稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms) に基づく PASS/FAIL 判定を出力。
    - コマンドラインで日付範囲（--from / --to）や DB パス（--db）を指定可能。

- リサーチ / ファクター計算（下書き開始）
  - research.factor_research: DuckDB を用いたファクター計算モジュールを追加（モメンタム等の指標算出を設計）。
    - モメンタム計算（1M/3M/6M、MA200乖離など）の関数雛形を実装。将来の拡張に備えた定数・スキャン幅の定義を含む。
    - （注）ファイル末尾で関数実装が途中で切れている箇所があるため、今後の実装完了が必要。

### Changed
- （初期公開のため該当なし）

### Fixed
- （初期公開のため該当なし）

### Security
- 環境変数の取り扱いにおいて .env のシークレット項目は UI 上でマスク表示（config_setup）し、.env を Git にコミットしない旨の注意喚起を追加。

### Notes / Implementation details
- 多くのコンポーネントは外部依存（kabuステーション API クライアント、ブローカークライアント、ExecutionEngine の内部ロジック、SystemMonitor の詳細実装等）を想定しており、実運用前にそれら実装および結合テストが必要です。
- logging_setup と process_priority は各起動スクリプトから呼び出すことで統一的な挙動を提供しますが、ファイルアクセス許可や OS 権限により一部機能がスキップされる設計になっています（フォールトトレラント）。
- research.factor_research の一部関数が未完である箇所が見られます（将来的な拡張対象）。

---

既知の未実装 / TODO:
- research.factor_research の完全実装（ファクター計算の SQL / 実数実装）。
- 銘柄毎の lot_size をマスタデータから取得する拡張（position_sizing の TODO）。
- 監視 / 実行のより詳細なエラーレポーティング・再試行戦略の強化。

[Unreleased]: UNRELEASED
[0.1.0]: 0.1.0