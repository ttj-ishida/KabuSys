# CHANGELOG

すべての変更は Keep a Changelog 規約に準拠します。  
主なバージョンは semantic versioning を想定しています。

## [Unreleased]
（現在未リリースの作業はありません）

## [0.1.0] - 2026-04-18
初回リリース — KabuSys のコア機能を実装しました。

### 追加
- 基本パッケージ情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として公開。

- 設定/環境管理
  - 環境変数を自動読み込みする Settings モジュールを追加（kabusys.config）。
    - 自動ロード順序: OS 環境変数 > .env.local > .env（プロジェクトルートが検出できない場合はスキップ）。
    - 必須環境変数取得ヘルパー `_require()` を提供。
    - 環境種別（development, paper_trading, live）、ログレベル、各種 DB パス、モニタ閾値、Paper Trading の挙動などのプロパティを実装。
    - PAPER_FILL_MODE の妥当性チェック（"instant" | "partial" | "never" | "reject"）。
    - paper_trading 用のデフォルト SQLite パス `data/paper_trading.db` をサポート。

  - 対話式の .env 作成/更新ウィザードを追加（kabusys.config_setup）。
    - J-Quants / kabu API 等の主要設定を対話的に入力可能。
    - 既存 .env 読み込み、シークレット表示マスク、保存プレビューを実装。
    - ファイル書式のテンプレート（注: .env を Git に含めない注意書き）を作成。

  - 設定検証 CLI を追加（kabusys.validate_config）。
    - 必須環境変数の有無チェック、KABUSYS_ENV/LOG_LEVEL の値検証、DB パスの親ディレクトリチェック、config/*.yaml の存在／YAML パース検証（PyYAML があれば実行）など。
    - --strict オプションで警告をエラー扱いにできる。

- 実行/監視プロセス起動スクリプト
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）を追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使いデータを `data/paper_trading.db` に分離して記録する動作をサポート。
    - プロセス優先度を起動時に "high" に設定。
    - 停止を示すフラグファイル（data/stop_requested.flag）と PID ファイル管理を実装。
    - Engine を別スレッドで実行し、フラグ検知で安全停止を行うループを実装。
  - SystemMonitor 起動スクリプト（kabusys.run_monitoring）を追加。
    - デフォルトポーリング間隔 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（不正値時はデフォルトへフォールバック）。
    - 監視は環境に関わらず本番用 sqlite_path を使用する設計（監視データは一元管理）。
    - stop flag によりループを終了、例外発生時はログ出力して次サイクルに継続。

- モニタリング DB 初期化フック（init_monitoring_db）と SystemMonitor 呼び出しを統合（起動スクリプトから自動で初期化）。

- Execution コンポーネント骨格
  - BrokerClientFactory（ブローカー抽象のファクトリ）を導入。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine 等の実行系コンポーネントを結合して起動するフローを実装（設定に応じた RiskConfig / EngineConfig を使用）。
  - RiskManager の初期パラメータ（例: max_position_pct=0.20, max_utilization=0.80 等）をデフォルトとして設定。initial_portfolio_value は broker.get_available_cash() から取得。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: score 降順・タイブレークに signal_rank を採用する候補選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有を考慮したセクター集中度チェックと候補除外（"unknown" セクターは制限適用外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた資金乗数を返す。未知レジームは 1.0 でフォールバック（警告ログ）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づいて発注株数を計算。単元株（lot_size）丸め、per-position と aggregate の上限、コストバッファによる保守的見積り、利用可能現金に応じたスケールダウン（および残差処理）を実装。

- 研究/ファクター計算
  - research.factor_research にモメンタム / ボラティリティ等のファクター計算ロジックを追加（DuckDB を用いて prices_daily テーブルから計算）。
    - mom_1m/mom_3m/mom_6m、MA200 乖離、ATR20、20日平均出来高、volume ratio などを計算する設計方針を実装。
    - データ不足時は None を返す設計（堅牢化）。

- ユーティリティ
  - process_priority ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX に対応したプロセス優先度設定（"high"/"normal"/"low"）。
    - CPU affinity を最初の N コアに固定するヘルパー。
    - 権限不足や未対応 OS の場合は警告ログでフォールバック。

- ツール
  - Paper Trading 検証レポートジェネレータ（kabusys.tools.paper_verification_report）を追加。
    - SQLite の paper_trading DB を読み取り、システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を算出。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を用いて PASS/FAIL 判定を出力。
    - --from/--to/--db オプションをサポート。DB が存在しない場合はエラーメッセージを出力。

### 変更
- なし（初回リリース）

### 修正
- なし（初回リリース）

### 既知の注意点 / 制限
- .env の自動ロードはプロジェクトルート検出に依存する（.git または pyproject.toml を基準）。配布後にプロジェクトルートが検出できない場合は自動ロードをスキップする。
- apply_sector_cap の価格欠損時の挙動について注記あり（price が 0.0 の場合はエクスポージャーが過小見積りされる可能性）。将来的な価格フォールバックの検討が必要。
- process priority / cpu affinity の設定は権限やプラットフォームによって失敗する可能性があり、その場合はログでスキップされるのみ。
- monitoring は「環境にかかわらず本番 sqlite_path を使用」する設計になっているため、開発時に監視データを隔離したい場合は注意が必要（設定でパスを変更可）。
- Paper Trading 周りは mock ブローカや専用 DB により本番データと分離される設計だが、完全な隔離を保証するために環境変数の設定に注意すること。

---

作業や導入に関する質問、CHANGELOG の調整や追加事項があればお知らせください。