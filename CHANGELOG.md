# Changelog

すべての変更は Keep a Changelog の形式に従い、重要度の高い変更をカテゴリ別に整理しています。

全般:
- Semantic Versioning を想定しています。
- 日付は本稿作成日（2026-04-21）を使用しています。

## [0.1.0] - 2026-04-21

### Added
- 初期リリースとして以下の主要機能を追加。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用 sqlite_path を使用する設計。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading 用 DB（data/paper_trading.db）へ記録する。本体はスレッドで実行し、停止フラグに応じて安全に停止する。
  - 設定管理・ウィザード・検証
    - config.py: 環境変数読み込み・Settings クラスを追加。プロジェクトルート自動検出や .env / .env.local 自動読み込み（OS 環境変数保護付き）、各種プロパティ（パス・閾値・フラグ等）を実装。
    - config_setup.py: .env を対話的に作るウィザード CLI を提供。シークレットマスク表示、テンプレート書き出し機能を搭載。
    - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数の存在、KABUSYS_ENV・LOG_LEVEL の妥当性、DB パス・config/*.yaml の存在と YAML パース（PyYAML あれば）をチェック。--strict オプションで警告を FAIL 扱いにできる。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール（stdout）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラの二重設定防止やログディレクトリ作成失敗時のフォールバックを実装。
    - utils/process_priority.py: プロセス優先度と CPU affinity を設定するユーティリティ。Windows/Linux/macOS に対するフォールバック処理と例外ハンドリングを実装。
  - ポートフォリオ構築関連（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定および等配分・スコア加重配分の実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based, equal, score）を実装。単元株丸め、per-stock 上限・aggregate cap によるスケールダウン、cost_buffer の考慮などを実装。
  - 分析ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（P95）などを算出し PASS/FAIL を判定する。
  - 研究・因子計算の骨子
    - research/factor_research.py: モメンタム・ボラティリティ等のファクター計算モジュールの骨組みを追加（DuckDB 接続を受け取って SQL+Python で計算する方針）。

### Changed
- 設定読み込みの挙動
  - config.py にて自動 .env 読み込みの優先順位を OS 環境変数 > .env.local > .env として実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - .env のパース機能を強化（export 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの取り扱い改善）。
- run_monitoring.py / run_execution.py
  - 起動直後に set_process_priority("high") を呼び出し、優先度設定を試行するように変更（プロセス安定性向上のため）。
  - DB 初期化: init_monitoring_db() を呼び出して監視用テーブルの存在を保証するようにした（冪等）。
  - run_monitoring は監視用 DB に常に settings.sqlite_path を使用する（環境値に関係なく本番の監視 DB を使用する意図）。
  - run_execution は paper_trading モードで専用 sqlite DB（settings.paper_sqlite_path）を使用して本番 DB と分離するように実装。
  - 停止フラグ（data/stop_requested.flag）検出時の挙動を明確化。起動時にフラグが既に立っている場合は起動を中止するチェックを追加。
- ロギング
  - logging_setup.py: stdout を StreamHandler の出力先に使用する方針に変更（cron 等で stdout/stderr を一元化しやすくするため）。既存ハンドラをクリアして二重設定を防止するようにした。
  - ファイルハンドラ作成に失敗した場合は警告を出してコンソール出力のみで継続する堅牢性を追加。
- process_priority
  - Windows と POSIX 系での優先度マッピングを実装し、例外発生時は警告ログを出して処理をスキップするようにした。

### Fixed
- エラー耐性の向上
  - run_monitoring.run_loop と run_execution の起動フローで例外発生時にログ出力しつつループ継続／クリーンアップするように実装（monitor.check_once() の例外を捕捉してループ継続）。
  - DB 接続は finally ブロックで確実に close() するようにした。
  - validate_config.py:
    - PyYAML 未インストール時に YAML 検証をスキップし、その旨を警告するようにした（設定検証が不完全でも起動時に致命的にならないように）。
    - config/*.yaml のファイルが存在しない場合は警告を出すようにした（自動生成スクリプトを案内）。
  - position_sizing.calc_position_sizes:
    - 価格欠損（price が None あるいは <= 0）をスキップしてゼロ除算や不正な株数計算を回避する処理を追加。
    - aggregate cap 適用時のスケーリング処理を改善し、lot_size 単位での再配分ロジックを追加して合計投資が available_cash を超えないようにした。
  - risk_adjustment.apply_sector_cap:
    - "unknown" セクターはセクター上限判定から除外する仕様にして誤除外を防止。既存保有の売却予定銘柄をエクスポージャ計算から除外するオプションを追加。
  - tools/paper_verification_report:
    - P95 計算を実装（空リスト時は None を返す）。期間フィルタリングと各種指標の欠損時の N/A 表示や例外耐性を追加。

### Documentation
- 各モジュールに詳細な docstring と使用例（CLI の使い方等）を追加。config_setup と validate_config の利用手順がスクリプト内で説明されている。

### Notes / Known limitations
- research/factor_research.py はモジュール骨格と設計方針が含まれるが、一部関数実装（ファクター計算の完全実装）は未完了の可能性があります（ファイル末尾が切れている旨の注記あり）。
- position_sizing の lot_size は現時点で全銘柄共通の想定。将来的に銘柄別単元対応へ拡張する旨の TODO コメントあり。
- apply_sector_cap の価格フォールバック（価格欠損時の取り扱い）に関する TODO が残っています（前日終値等のフォールバックは未実装）。
- process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでは警告を出してスキップする設計のため、期待どおりに設定されない場合がある。

---

（初期リリース）今後のリリースでは、research/factor_research の完全実装、テストカバレッジの強化、稼働監視・アラート通知周りの拡張（LINE 通知の実装や通知テンプレート整備）を予定しています。