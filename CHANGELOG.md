# Changelog

すべての重要な変更履歴をここに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

- https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

予定・既知の改善点（コード中の TODO や将来的な拡張案に基づく推測）
- 単元株（lot_size）を銘柄ごとに管理するための stocks マスタ導入（position_sizing の拡張）。
- 価格欠損時のフォールバック（前日終値や取得原価）の実装（risk_adjustment 内 TODO）。
- research モジュールのさらなるファクター実装（現在はモメンタム計算等の実装途中）。
- DuckDB を用いた集計・分析の追加ユーティリティ（さらなるクエリ最適化・インデックス検討）。
- テストカバレッジの拡充と CLI に対する自動テストの追加。

---

## [0.1.0] - 2026-04-19

初回リリース。KabuSys 自動売買システムの基盤となる機能群を実装しました。
（以下はコードベースから推測して作成した要約です）

### Added
- 設定・環境
  - Settings クラスによる環境変数ラッパーを実装（config.py）。.env 自動ロード機能を備え、.env/.env.local の読み込み順序をサポート。OS 環境変数は保護され上書きされない。
  - .env の対話式作成/更新ウィザードを実装（config_setup.py）。プロンプト、既存値の再利用、書き出しフォーマットをサポート。
  - 設定検証 CLI を追加（validate_config.py）。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス・config YAML の存在/パース検証、KABUSYS_ENV=live 時の追加ガード、--strict モードをサポート。

- 実行・監視
  - ExecutionEngine 起動スクリプトを実装（run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を通じたブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立てを行い、ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
  - SystemMonitor 起動スクリプトを実装（run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔のオーバーライド（デフォルト60秒）。
    - 監視は環境に依らず本番の sqlite_path を使用し、停止フラグでループを終了。
    - モニタリング DB 初期化と DuckDB への接続を行う。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み算出（portfolio/portfolio_builder.py）
    - select_candidates: スコア順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等重み・スコア加重を実装（スコア全件 0 の場合は等重みへフォールバック）。
  - セクター制限・レジーム乗数（portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に候補を除外（unknown セクターは除外しない）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバックで 1.0）。
  - 発注株数計算（portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method に応じた株数決定（risk_based / equal / score）。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（available_cash に合わせたスケールダウン）、cost_buffer を加味した保守的推定、残差に基づく追加割当ロジックを実装。

- 研究・ファクター計算
  - research/factor_research.py: DuckDB と prices_daily/raw_financials を用いるファクター計算のフレームワークを追加。モメンタム（1M/3M/6M）、MA200 乖離、ATR/出来高系等を想定（calc_momentum 実装の開始）。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定（閾値はソース中に定義）。
    - 日付フィルタ、DB パスオーバーライド、P95 計算ロジックを実装。

- ユーティリティ
  - ロギングセットアップ（utils/logging_setup.py）
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次, 30日保持）を設定。ログレベル・ログディレクトリの解決順を定義。ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続。
    - stdout を用いることで外部ジョブスケジューラとの統合を考慮。
  - プロセス優先度/CPU affinity 設定ユーティリティ（utils/process_priority.py）
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。CPU affinity の固定もサポート。権限不足時は警告を出し安全にスキップ。

- データベース
  - SQLite（monitoring / paper_trading 用）と DuckDB（分析用）の両方を前提とした接続処理を導入。monitoring_db 初期化ユーティリティ（monitoring.monitoring_db の呼び出し）を利用。

- パッケージ情報
  - パッケージ初期バージョンを設定（__version__ = "0.1.0"）。

### Changed
- （初回リリースのため主に追加。内部での保守的なフォールバックや安全弁を多数導入）
  - ログ出力は標準エラーではなく標準出力に出す方針を採用（logging_setup）。
  - .env 読み込みは OS 環境変数を保護するために既存値優先で読み込む挙動を採用（.env.local は上書き可能）。

### Fixed
- 環境ファイルパーサの堅牢化（config._parse_env_line）
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - 無効行・空行・コメント行の無視処理を厳密化。

### Notes / Behavior guarantees
- Paper Trading モードでは実際のブローカーにアクセスせず MockBrokerClient を使用して DB に記録する想定（run_execution の分離設計）。
- 監視コンポーネントは停止フラグ（data/stop_requested.flag）を監視して安全に終了可能。
- 設定検証 CLI（validate_config）は PyYAML が未インストールの場合は YAML 内容検証をスキップするが警告を出す。

### Security
- .env の生成スクリプトが .env ファイルを生成する旨を明記し、Git にコミットしないよう注意書きを追加（config_setup）。

---

開発中の機能や改善点は Unreleased セクションに記載した通りです。必要があれば、より詳細な変更箇所（ファイル単位・関数単位）を追加で生成できます。どの粒度で記録したいか指定してください。