# Changelog

すべての変更は "Keep a Changelog" 形式に準拠しています。  
このファイルはコードベース（src/kabusys 以下）から推測して作成した変更履歴です。

## [0.1.0] - 2026-04-19

### Added
- 基本パッケージ初期リリースを追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。
- 実行用スクリプトを追加。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV により paper_trading の場合は専用 Mock 環境へ切替（paper_trading 用 SQLite を使用）を想定。
    - ExecutionEngine をスレッドで起動し、停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - PID ファイル管理、およびプロセス優先度を起動時に "high" に設定。
  - 監視（SystemMonitor）ポーリング起動スクリプト（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず本番用 sqlite_path を参照する挙動（監視用 DB 初期化処理を実行）。
    - 停止フラグ検知でループを終了、KeyboardInterrupt に対応。
- 環境設定関連 CLI を追加。
  - 対話式設定ウィザード（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を対話式で支援。シークレット項目マスク表示、既存値の再利用、保存前確認などを実装。
  - 設定検証 CLI（src/kabusys/validate_config.py）。
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在および YAML パース（PyYAML がある場合）などを検査。
    - 本番環境用のガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
    - --strict オプションで警告を失敗扱いにできる。
- 環境変数読み込み・管理を実装。
  - .env 自動ロード機能（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml で探索して自動的に .env / .env.local を読み込む。
    - export 構文、クォート値（バックスラッシュエスケープ対応）、インラインコメント処理などの堅牢なパーサーを実装。
    - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスで主要設定を集約（J-Quants / kabu API / DB パス / ログ設定 / 監視閾値 等）。
    - PAPER_FILL_MODE の検証、環境名（KABUSYS_ENV）・LOG_LEVEL の検証、paper_trading 用 sqlite パス等を提供。
- ポートフォリオ構築関連モジュールを追加（純粋関数群）。
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights（スコア全0時は等配分にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮したセクター除外）、calc_regime_multiplier（bull/neutral/bear の乗数）
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap（スケールダウン）処理、cost_buffer による保守見積り、ロジック内での上限チェックと残差処理
  - 上記をパッケージとしてエクスポート（src/kabusys/portfolio/__init__.py）。
- ユーティリティを追加。
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーへ統一的に設定。
    - LOG_DIR / LOG_LEVEL の解決順、ハンドラ二重設定防止のため既存ハンドラをクリアする処理を実装。
  - プロセス優先度・CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分吸収、アクセス拒否や未実装 API を安全に扱う例外処理を実装。
- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
  - 指標: 稼働率（uptime）, 注文成功率(fill_rate), 送信率(send_rate), レイテンシ (avg/max/P95)、リスク却下数 など。
  - 閾値判定による PASS/FAIL レポート出力、期間フィルタ（--from, --to）、DB パス選択（引数 / 環境変数 / デフォルト）を実装。
- リサーチ（ファクター計算）モジュールを追加の下地を導入（src/kabusys/research/factor_research.py）。
  - Momentum などのファクター設計、計算パラメータ定義（窓長等）を実装（calc_momentum の処理開始あり、未完の箇所あり）。

### Changed
- 監視・実行コンポーネントの起動フローを標準化。
  - 起動時に共通で setup_logging と set_process_priority("high") を呼び出すようにしてログ・優先度の一貫化を図った（run_execution.py, run_monitoring.py）。
- DB 接続の取り扱いを明確化。
  - 監視は環境に関係なく sqlite_path を使用する旨をドキュメント化（run_monitoring.py）。
  - 実行エンジンは paper_trading であれば paper_sqlite_path を使用して本番 DB と分離する実装（run_execution.py）。
- .env 読み込みの優先度ルールを明文化（src/kabusys/config.py）。
  - OS 環境変数 > .env.local > .env。OS の環境変数は protected として上書きされない。

### Fixed
- .env パーサーの堅牢性を向上。
  - export プレフィックス、シングル/ダブルクォートのバックスラッシュエスケープ、インラインコメントの扱いなどを考慮して不正なパースを低減（src/kabusys/config.py）。
- ログディレクトリ作成失敗時のフォールバックを明示。
  - ディレクトリ作成失敗時はファイルハンドラをスキップし、コンソール出力のみで継続するように変更（src/kabusys/utils/logging_setup.py）。
- プロセス優先度/CPU affinity の安全なフォールバックを追加。
  - 権限不足や未実装環境でもアプリが停止しないよう例外をキャッチして警告ログに留める（src/kabusys/utils/process_priority.py）。

### Security
- .env の取扱いについて注意喚起を追加（config_setup.py の出力コメント）。
  - .env を誤って Git に含めないようヘッダで明記。

### Notes / その他（推測）
- 一部モジュールは将来的な拡張を意図した TODO コメントを含む（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の価格フォールバックなど）。
- research/factor_research.py はモメンタム計算の実装が途中で切れている箇所が見られるため、今後の追加実装が想定される。

---

注: 本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノート作成時はコミットメッセージや変更履歴（Git log）を参照して正確な変更点・作業者・関連チケット等を追記してください。