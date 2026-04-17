# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  
このファイルは人間とマシンの双方が読みやすいことを意図しています。

なお、記載内容は提供されたコードベースから推測して作成したもので、実際のコミット履歴ではありません。

## [Unreleased]

- なし（初回リリースに相当する変更を以下に記載）

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報
  - パッケージのバージョンを定義 (`src/kabusys/__init__.py`: __version__ = "0.1.0")。

- 設定管理
  - 環境変数／.env 自動読み込みとパーサーを実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から自動検出。
    - .env / .env.local の順で読み込み、OS 環境変数を保護する仕組みを導入。
    - export プレフィックス、クォート文字、エスケープ、インラインコメント（スペース前の #）等に対応する堅牢なパーサーを実装。
    - 多数の設定プロパティを提供（J-Quants トークン、kabu API、DB パス、PID/Kill フラグ、監視しきい値、環境判定等）。
    - PAPER_FILL_MODE に対する入力バリデーション（有効値: instant/partial/never/reject）。
    - KABUSYS_ENV の有効値チェック（development/paper_trading/live）およびログレベル検証。

- 設定ウィザード CLI
  - 対話式 .env 生成/更新ツールを追加（src/kabusys/config_setup.py）。
    - デフォルト値、選択肢、シークレット入力、既存値の再利用、保存確認機能を提供。
    - .env 書き込みフォーマット（コメント付きテンプレート）を備える。

- 設定検証 CLI
  - 起動前設定検証ツールを追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の検証、ログレベル・DB パスの検査。
    - config/*.yaml の存在確認および PyYAML が利用可能な場合はパース検証。
    - KABUSYS_ENV=live 時のガード（LINE 設定や kill フラグの自動クリア設定の警告）。
    - --strict オプションで警告を失敗として扱い exit(1) にする機能。

- 実行制御・起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、本番 DB と分離して paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てと ExecutionEngine の起動を行う。
    - デーモンスレッドでエンジンを実行し、 data/stop_requested.flag による外部停止（停止フラグ）に対応。
    - 起動時に process priority を "high" に設定する呼び出しを追加。

  - 監視（モニタリング）ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトへフォールバック。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用してデータを記録。
    - data/stop_requested.flag による安全な停止、KeyboardInterrupt ハンドリング、check_once() 実行時の例外捕捉とログ出力。
    - DuckDB 接続・SQLite 初期化呼び出しを含む。

- プロセス制御ユーティリティ
  - プロセス優先度および CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して set_process_priority(level) を提供（high/normal/low）。
    - set_cpu_affinity(cpu_count) による最初 N コアへのピン留め機能（権限不足や未サポート環境では警告してスキップ）。
    - psutil に依存しつつ、存在しない定数へのフォールバック、安全な例外ハンドリングを実装。

- ポートフォリオ構築（純関数群）
  - 銘柄選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重の重み計算。スコア合計が 0 の場合はフォールバック。

  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有に基づくセクターごとの時価総額を計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。sell_codes を除外して計算可能。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に基づく投下資金乗数を返す。未知レジームは 1.0 でフォールバックし警告を出す。

  - 株数決定（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を決定。
    - risk_based: 許容リスク（risk_pct）と stop_loss_pct に基づく理論株数算出。
    - equal/score: ウェイトに基づいた割当て、max_position_pct と max_utilization による上限適用。
    - lot_size（単元）での切り捨て、cost_buffer（手数料・スリッページ想定）を考慮した aggregate cap のスケーリング、残差分の安定的な再配分ロジックを実装。
    - 価格欠損時のスキップやデバッグログを追加。

  - ポートフォリオパッケージのエクスポート設定（src/kabusys/portfolio/__init__.py）。

- 研究・ファクター計算
  - DuckDB を用いたファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M リターン、MA200 乖離）計算（データ不足時の None 処理）。
    - Volatility/流動性（ATR20、相対 ATR、20日平均売買代金、出来高比）計算（true_range の NULL 伝播を制御）。
    - 計算に使用する窓幅やスキャン日数は定数化（可読性のため）。
    - DuckDB の SQL を用いることで大規模データの効率的処理を想定。

- Paper Trading 検証ツール
  - paper_verification_report CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から集計し、稼働率、注文成功率、送信率、P95 レイテンシ等を計算してレポート出力。
    - 日付フィルタ（--from/--to）および --db オプションをサポート。
    - P95 計算、各種しきい値（稼働率 99% 等）を定義して PASS/FAIL 判定を行う。
    - DB スキーマが存在しない場合でも例外を吸収して N/A を表示するなど堅牢性を確保。

### Changed
- なし（初回リリース相当の追加中心）

### Fixed
- なし（特定のバグ修正記録なし。コードには堅牢化・例外処理が多数追加されているため運用時の安定性向上を意図）

### Security
- .env ファイルは .git にコミットしない旨をテンプレート内に明記（config_setup が出力する .env ヘッダ）。
- 必須トークン等が未設定の場合の明示的エラー/警告により、本番誤設定を検出しやすくしている（validate_config の live ガード等）。

### Notes / Migration
- 実行時の注意
  - run_execution/run_monitoring は外部ファイル（data/stop_requested.flag, data/execution.pid など）による起動/停止制御を想定しているため、運用環境ではこれらファイルの管理に注意してください。
  - run_monitoring は監視用 DB として常に sqlite_path（本番向け）を使用します。paper_trading で分離したい場合は設計上の目的を確認してください。
- 環境変数の自動ロード
  - デフォルトではプロジェクトルートが見つかれば .env が自動読み込みされます。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- 将来の拡張
  - position_sizing の lot_size は現状共通値を前提としているが、将来的に銘柄別 lot_map を渡す拡張を想定している旨をコードコメントで明示。

---

この CHANGELOG はコード内容からの推測に基づいて作成しています。実際のコミットメッセージや差分と照合して必要に応じて修正してください。