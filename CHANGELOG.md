# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
バージョン番号は semver に従います。

## [0.1.0] - 2026-04-18 (初回リリース)

### Added
- 初期リリース。日本株自動売買システム「KabuSys」の基本機能を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。環境により paper_trading 用の MockBroker を利用し、paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag により制御。
- 設定関連
  - config.py: 環境変数/`.env` の読み込み・管理を行う Settings クラスを実装。多くの設定プロパティ（DB パス、PID/Kill フラグ、しきい値、env/log_level 判定、paper_trading の設定など）を提供。
  - config_setup.py: 対話式ウィザードで `.env` を初期作成・更新する CLI を実装（シークレット入力や選択肢サポート、書き出し機能）。
  - validate_config.py: 起動前に `.env` や config/*.yaml の設定不備を検出する検証ツールを追加。`--strict` オプションで警告を FAIL 扱いにできる。PyYAML があれば YAML のパース検証も行う。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を組み合わせた統一的なロギング設定ユーティリティを追加。ログディレクトリ作成失敗時はファイル出力を無効化してもコンソール出力を継続。
  - utils/process_priority.py: Windows/Linux/macOS の差を吸収してプロセス優先度（および CPU affinity）を設定するユーティリティを追加。アクセス拒否等の失敗は警告でスキップ。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）・等金額配分・スコア加重配分の純粋関数を追加。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を追加。unknown セクターは上限適用を除外する挙動。
  - portfolio/position_sizing.py: 発注株数の決定ロジックを実装（risk_based, equal, score 対応）。単元株（lot_size）丸め、ポジション上限・aggregate cap、コストバッファ考慮等を含む。
  - portfolio/__init__.py: 上記モジュールの公開 API をまとめてエクスポート。
- 比較・検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL を判定。期間指定（--from/--to）や DB パス指定が可能。
- 研究用モジュール（骨子）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム、MA200、ATR、出来高関連などの定義と関数の設計方針を含む）。（実装の一部は継続中・ファイル末尾で切れている）

### Changed
- ログ関連の挙動を統一
  - logging_setup: 標準出力は stdout を使用するよう明示（cron/Task Scheduler からのリダイレクトに配慮）。
  - 既存ルートロガーのハンドラをクリアしてから再設定することで二重設定を防止。
- `.env` の自動ロード
  - config: プロジェクトルートを .git / pyproject.toml から検出して `.env` / `.env.local` を自動的に読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。OS 環境変数を保護する保護セットを導入して上書きの安全性を確保。
- run_monitoring / run_execution
  - 起動時にプロセス優先度を最初に "high" に設定する処理を追加。
  - DB 初期化（init_monitoring_db）を起動時に実行して必要な監視テーブルが存在することを保証（冪等）。
  - 停止フラグの検知と安全なシャットダウン処理を強化（スレッドの join とタイムアウト処理を含む）。

### Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line: export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどをサポートし、不正な .env 行の誤読を防止。
- MONITOR_POLL_INTERVAL の取り扱い
  - run_monitoring._get_poll_interval: 0 以下または不正な値が設定された場合にデフォルトへフォールバックし警告を出すよう変更（time.sleep に渡す際の ValueError 回避）。
- duckdb / sqlite のクローズを確実に実行
  - run_monitoring / run_execution: finally ブロックで接続を閉じるようにしてリソースリークを防止。
- position_sizing: aggregate cap スケーリングで端数処理と残余配分を安定化。lot_size 単位での配分と再現性を考慮。

### Security
- セキュリティ関連設定の注意喚起を追加
  - validate_config._check_live_guards: KABUSYS_ENV=live の場合に LINE 通知設定の未設定や KILL_FLAG_CLEAR_ON_START の危険設定を警告するチェックを追加。

### Documentation / UX
- CLI ヘルプおよび出力メッセージを日本語で整備（config_setup, validate_config, tools/paper_verification_report 等）。
- config_setup のウィザードは既存値の再利用・マスク表示・選択肢チェック・保存確認を実装し、誤操作による上書きを防ぐ。

---

注:
- research/factor_research.py の実装は途中で切れている箇所があるため、ファクター計算の完全実装は今後の作業予定です。README やドキュメント（PortfolioConstruction.md / StrategyModel.md を参照する旨のコメントあり）に従って追加実装を行ってください。
- 上記はソースコードから推測して作成した変更点の一覧です。実際のコミット履歴が存在する場合はそちらを優先して正確な差分・責任者・日付を記載してください。