# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

- ドキュメントの補完やテスト追加、ファクター計算モジュールの完成などを予定しています。
- 既知の TODO／注意点の解消（価格フォールバック、lot_size の銘柄別対応等）を次期リリースで対応予定。

## [0.1.0] - 2026-04-19

初回リリース。プロジェクトの基本機能（設定管理、起動スクリプト、ポートフォリオ構築ロジック、ユーティリティ、運用用スクリプト等）を実装。

### Added
- 基本パッケージ
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）を実装（src/kabusys/config.py）。
  - .env ファイルの堅牢なパーサ実装（クォート、エスケープ、export プレフィックス、インラインコメント処理に対応）。
  - Settings クラスで環境変数をラップ（各種パス、閾値、運用モードフラグ等をプロパティで提供）。
  - paper_trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）をサポート。
- 設定関連 CLI
  - 対話式の環境設定ウィザードを実装（src/kabusys/config_setup.py）。.env を初期作成／更新するためのガイド付きプロンプト。
  - 設定検証 CLI 実装（src/kabusys/validate_config.py）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース確認、live 守りのチェックを行う。--strict オプションをサポート。
- 起動スクリプト（運用プロセス）
  - 監視プロセス起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）の検知、例外ハンドリング、DB 接続（sqlite3, DuckDB）。
    - プロセス優先度を High に設定して起動。
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - ExecutionEngine をスレッドで実行。停止フラグの検知で安全に停止。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の SQLite を使用して本番 DB と分離（MockBrokerClient 利用想定）。
    - PID ファイル管理、監視テーブル初期化（init_monitoring_db）などを担保。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 参照なし）
  - 候補選定・重み付け（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレーク: signal_rank）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化、全スコア0時は等金額にフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮してセクター上限を超える候補を除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier（regime label に基づく乗数。'bull','neutral','bear' を定義。未知レジームはフォールバックで 1.0）
    - ログ出力で詳細情報を提供（遮断理由等の debug ログ）。
  - ポジションサイズ算出（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" をサポート）
    - 単元株（lot_size）丸め、max_position_pct、max_utilization、cost_buffer（手数料・スリッページ見積）を考慮したスケーリングロジックを実装。
    - aggregate cap 超過時のスケールダウンと残余キャッシュを用いた端数配分アルゴリズムを実装。
- 運用ユーティリティ
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - LOG_LEVEL/LOG_DIR の解決順を実装。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows/Linux/macOS の差分吸収。psutil を使い nice 値／Windows 優先度クラスを設定。
    - set_process_priority と set_cpu_affinity を提供。権限不足等は警告でフォールバック。
- ペーパートレード検証ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定（閾値はソース内定義）。
    - P95 計算、日付フィルタ、テーブル欠如時のフォールバックを実装。コマンドライン引数で期間／DB 指定可能。
- 研究用モジュール（構成開始）
  - ファクター計算モジュールの骨子を追加（src/kabusys/research/factor_research.py）。DuckDB 接続を受け prices_daily / raw_financials テーブルを用いる設計。モメンタム等の指標定義と定数を導入（実装は継続中）。
- その他
  - monitoring_db 初期化フック（init_monitoring_db の利用）を各起動スクリプトで呼び出し、監視テーブルの存在を保証。

### Changed
- 本体設計
  - 起動時にプロセス優先度を "high" に設定する方針を採用（run_monitoring/run_execution）。
  - 監視プロセスは KABUSYS_ENV に関係なく本番 sqlite_path を使用する（監視の一貫性確保）。
  - paper_trading モードでは専用 SQLite を使用して本番とデータ分離。
- ログ出力
  - ログは stdout に出力する設計（cron/タスクランナーでの扱いを考慮）。

### Fixed
- 環境読み込みの堅牢性向上
  - .env 読み込み時にファイルアクセス失敗時の警告（warnings.warn）を追加し、処理を継続するように改善。
  - .env パーサで不正行やコメント混入ケースを適切に扱うように実装。

### Security
- .env の取り扱いに関する注意を明記（config_setup にて .env を絶対に Git にコミットしない旨のヘッダを出力）。
- シークレット値は対話ウィザードおよび表示時にマスク表示を行う（config_setup）。

### Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の注釈あり。将来的に前日終値や取得原価をフォールバックとして利用する検討が必要（src/kabusys/portfolio/risk_adjustment.py）。
- calc_regime_multiplier:
  - 未知のレジームに対しては警告を出して 1.0 にフォールバックする実装。要運用上の確認。
- research/factor_research.py:
  - ファクター計算モジュールは実装途中（ファイル末尾が未完）。追加実装とテストが必要。
- テストスイートは未同梱（ユニット／統合テストの追加推奨）。

---

変更点の詳細は各ファイルの docstring / コメントを参照してください。リリース以降の改善点やバグ修正は Unreleased セクションに追記していきます。