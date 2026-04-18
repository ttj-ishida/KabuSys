# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベースの内容から推測して作成した変更履歴です。

フォーマット:
- Unreleased: 今後の変更（このスナップショットでは未使用）
- 各リリース: 日付はこのスナップショットの作成日（2026-04-18）

## [Unreleased]
- なし

## [0.1.0] - 2026-04-18
初回公開リリース。

### Added
- コアアプリケーションと起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時にペーパートレード用の専用 SQLite DB を使用（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）。
    - ブローカークライアントのファクトリを使用して環境に応じた BrokerClient を生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine をスレッドで実行。停止フラグ（data/stop_requested.flag）による安全な停止をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。
- 設定管理・ウィザード・検証
  - config.py
    - .env 自動ロード機能を実装（.env → .env.local、OS 環境変数優先）。プロジェクトルートは .git または pyproject.toml 基準で探索。
    - 複雑な .env 行のパース（export プレフィクス、シングル/ダブルクォート、エスケープ、インラインコメントの扱い）に対応。
    - Settings クラスを追加し、環境変数から型変換された設定値をプロパティ形式で提供（DB パス、paper_trading 用パス、閾値、ログレベル、env 判定等）。
    - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを追加。既存 .env の読み込み、秘密値マスク、選択肢・デフォルト対応、保存機能を実装。
  - validate_config.py
    - 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在チェック（PyYAML がない場合は警告）、本番時のガード（LINE 設定や KILL_FLAG_CLEAR_ON_START の注意喚起）。
    - --strict モードで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日分保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順に対応、既存ハンドラの安全なクローズ／差し替え処理を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソールのみで継続。
  - utils/process_priority.py
    - プラットフォーム差を吸収したプロセス優先度設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）の優先度設定を抽象化。psutil を用いて nice や priority class を設定。権限不足や未対応環境では warning を出力して安全にスキップ。
    - CPU affinity を最初の N コアに固定するユーティリティも提供（設定省略可）。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py
    - シグナルの候補選定（スコア順／タイブレーク）select_candidates。
    - 等金額配分 calc_equal_weights、スコア重み calc_score_weights（スコアが全て 0 の場合は等分にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率が閾値超過のとき新規候補を除外、unknown セクターは除外対象外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数算出 calc_position_sizes を実装（allocation_method: risk_based / equal / score）。
    - 単元株丸め、per-position 上限（max_position_pct）、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残差分を lot 単位で再配分するロジックを実装。
    - 価格欠損時のスキップやログ出力を考慮。
  - portfolio/__init__.py で主要関数を再エクスポート。
- 研究・ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り、momentum/value/volatility/liquidity 等のファクターを計算する設計を追加。
    - モメンタム計算（calc_momentum）の骨組みと定数を実装（1M/3M/6M、MA200、ATR など）。（注: ファイル末尾で calc_momentum の実装が途中のスニペットを含むため、追加実装の余地あり）
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを追加。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計して PASS/FAIL 判定を出力。
    - --from / --to / --db オプションで期間・DB を指定可能。PAPER_TRADING_SQLITE_PATH 環境変数対応。
    - P95 計算、欠損時（テーブルが無い等）のフォールバック処理を実装。
- パッケージ設定
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- なし（初回リリースのため全て追加扱い）

### Fixed
- なし（初回リリース）

### Notes / Implementation details（コードから推測される挙動）
- .env の自動読み込みはプロジェクトルートが検出できない場合にスキップされ、安全設計（テスト時などに KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- run_monitoring/run_execution は起動直後にプロセス優先度を "high" に設定しようとする（権限がない場合は警告でフォールバック）。
- run_execution は paper_trading モードで本番 DB と完全に分離された DB を使う設計（安全性重視）。
- ログ出力は標準出力を優先して使用する（cron/スケジューラ向けに stdout に出す設計）。
- position_sizing の aggregate cap スケーリングは端数の処理（lot 単位）と残余キャッシュへの追加配分を考慮しており、実運用での安定性を意識した実装。

### Known / Potential Improvements
- research/factor_research.calc_momentum が途中で終わっているため、完全実装が必要（ファクター計算のデータ取得・ウィンドウ処理等）。
- price が欠損（0.0） の場合のエクスポージャーや position_sizing の扱いに関する改善点（例: 前日終値やマスタからのフォールバック）がコメントで示されているため、将来的な拡張候補。
- logging_setup のファイルハンドラ作成失敗時の代替処理はあるが、もっと詳細な障害通知（例えば EMAIL/LINE）を組み込む余地あり。

---

今後のリリースでは、research モジュールの完成、テストカバレッジの追加、監視・実行の耐障害性強化（再試行・メトリクス出力等）を想定しています。もし変更履歴に特定の項目（例: 過去のリリースやコミット単位）を反映したい場合は、さらに詳細なコミットログやバージョン管理履歴を提供してください。