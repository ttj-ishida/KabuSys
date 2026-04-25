# Changelog

すべての注目すべき変更点をここに記録します。  
フォーマットは Keep a Changelog に準拠します。

※ 本リポジトリはバージョン 0.1.0 が初回公開相当の内容として推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-25

### Added
- 基本アプリケーション骨組みを追加
  - パッケージエントリポイントとバージョン情報を追加（kabusys.__version__ = 0.1.0）。
- 環境設定 / ロード機能
  - .env 自動読み込み機能を追加（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
  - .env のパースを堅牢化（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
  - Settings クラスを実装し、環境変数をプロパティとして取得（必須チェック、値検証、デフォルト適用）。
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の妥当性チェックを実装。
- 環境設定ウィザード CLI
  - 対話形式で .env を生成・更新するツールを追加（kabusys.config_setup）。
  - 入力のマスク、デフォルト提示、確認画面、ファイル書き込みロジックを実装。
- 設定検証 CLI
  - 起動前に環境変数や config/*.yaml を検査する CLI を追加（kabusys.validate_config）。
  - 必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の値検査、DB パスの親ディレクトリ存在チェック、YAML のパースチェック（PyYAML が無ければ警告）。
  - --strict フラグで警告を FAIL 扱いにするオプションを実装。
- 実行系ランナー
  - ExecutionEngine 起動スクリプトを追加（kabusys.run_execution）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て。
    - PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止処理を実装。
    - デフォルトでプロセス優先度を "high" にセット。
- 監視系ランナー
  - SystemMonitor のポーリングループ起動スクリプトを追加（kabusys.run_monitoring）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
    - 監視 DB の初期化と DuckDB 接続を行う。
    - 停止フラグ検知で安全にループを終了。
- ロギング / プロセスユーティリティ
  - 統一的ログ設定ユーティリティを追加（kabusys.utils.logging_setup）。
    - コンソール (stdout) と日次ローテートファイルハンドラ（logs/<app>.log、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして警告を出力。
  - プロセス優先度と CPU affinity 管理ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows / POSIX を吸収して nice / priority を安全に設定。権限不足等は警告でスキップ。
- ポートフォリオ構築モジュール
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を追加（kabusys.portfolio.portfolio_builder）。
  - セクター集中制限とレジーム乗数（apply_sector_cap, calc_regime_multiplier）を追加（kabusys.portfolio.risk_adjustment）。
  - 株数算出（リスクベース / 等分 / スコア加重）・単元丸め・aggregate cap スケーリングを実装（kabusys.portfolio.position_sizing）。
  - 全て純粋関数で副作用無し（メモリ内計算のみ）。
- 分析・検証ツール
  - Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。コマンド引数で期間・DB 指定可能。
- リサーチ / ファクター計算（初期実装の骨組み）
  - DuckDB を用いたファクター計算モジュール基盤を追加（kabusys.research.factor_research）。
    - モメンタム / MA / ATR / ボリューム等の計算を想定した定数・関数構成を用意（実装続行中）。

### Changed
- 監視 DB の扱いに関する設計上の注意点を明示
  - run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用する実装。監視データは本番 DB に記録される点に注意。
- ロギング初期化の動作
  - setup_logging は既存のハンドラをすべて閉じてから再設定するため、複数回呼び出してもハンドラが重複しない。

### Fixed
- .env 読み込みでの一般的なパース落ちを回避
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等を改善。

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- 環境変数に機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を想定しており、config_setup で .env を生成する際にマスク表示を行います。 .env は絶対にリポジトリへコミットしない旨を強調。

### Notes / Known issues
- run_monitoring が本番 sqlite_path を使用する仕様は誤運用につながる可能性があるため、運用時は設定値を十分に確認してください。
- process_priority / cpu_affinity の設定は権限やプラットフォーム差により失敗することがある（その場合ログで警告し処理は継続します）。
- position_sizing の lot_size は全銘柄共通の仮定になっており、将来的に銘柄毎 lot_map を導入する余地がある。
- factor_research は設計の骨子があり一部未完（例: 関数内の途中で切れている箇所がある）ため、実装継続が必要。

---

（初期リリースのため「Added」が中心の記録です。以降の変更は本 CHANGELOG に逐次追記してください。）