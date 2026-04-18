CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。日付はコード内参照や本環境の想定日に基づいて推定しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-18
------------------

Added
- 初回リリース: KabuSys パッケージの主要コンポーネントを実装。
- 設定管理:
  - Settings クラスを実装。.env / 環境変数から各種設定を取得（J-Quants / kabu API / DB パス / ログ等）。
  - プロジェクトルート自動検出 (_find_project_root) により .env/.env.local の自動読み込みを提供（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサーの強化: export 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理に対応。
  - 設定値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）を実装し、不正値で例外を送出。
- CLI / ユーティリティ:
  - config_setup: 対話式ウィザードで .env を初期作成・更新する CLI を実装。シークレット項目のマスク表示、保存確認付き。
  - validate_config: .env と config/*.yaml の事前検証ツールを実装。--strict オプションで警告をエラー扱いに可能。PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を集計して PASS/FAIL 判定を行う。
- 実行／監視ランナー:
  - run_execution: ExecutionEngine 起動スクリプトを実装。KABUSYS_ENV=paper_trading 時は専用 SQLite（data/paper_trading.db）と MockBroker を使用して本番 DB と分離。プロセス優先度設定、PID ファイル、停止フラグ（data/stop_requested.flag）による安全停止対応を実装。
  - run_monitoring: SystemMonitor 起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する仕様。
- ロギング / プロセス制御:
  - utils.logging_setup: ルートロガーへ stdout 出力用 StreamHandler と日次ローテートの TimedRotatingFileHandler を設定するユーティリティを追加。ログディレクトリ作成に失敗した際はファイル出力をスキップしてコンソールのみで継続。
  - utils.process_priority: Windows / POSIX（Linux / macOS / FreeBSD）を考慮したプロセス優先度 (high/normal/low) 設定、および CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS 時には警告でフォールバック。
- ポートフォリオ構築モジュール:
  - portfolio.portfolio_builder: シグナル選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。スコア全てが 0 の場合は等配分にフォールバックして警告。
  - portfolio.risk_adjustment: セクター集中制限 apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を実装。unknown セクターは上限適用外とする等の挙動を明記。
  - portfolio.position_sizing: position sizing ロジックを実装（risk_based / equal / score）。単元株（lot_size）で丸め、per-position 上限・aggregate cap、コストバッファによる保守的見積り、スケーリングと端数処理（残余キャッシュでの優先配分）を実装。
- 研究モジュール（部分実装）:
  - research.factor_research: モメンタム等ファクター計算の骨格（定数定義、calc_momentum の導入）を配置。DuckDB 経由で prices_daily 等のテーブルを参照して計算する設計。

Changed
- ログ出力の標準ストリームを stderr ではなく stdout に統一（cron / タスクスケジューラからのリダイレクトを想定）。
- .env の読み込み優先度を OS 環境変数 > .env.local > .env の順とし、.env.local は既存 OS 環境変数を保護して上書き可能とした。

Fixed
- .env パースの堅牢化: クォート中のバックスラッシュエスケープやインラインコメントの扱いを改善し、誤った読み取りを防止。
- MONITOR_POLL_INTERVAL の取得で不正（0 以下や非数）が与えられた際にデフォルトにフォールバックし、time.sleep に不正な値を渡さないようにした。
- run_execution / run_monitoring の起動時にプロセス優先度設定を最初に行い、起動処理中のリソース競合を低減。

Security
- config_setup で生成される .env に関して明確に「.env を Git にコミットしない」旨を出力。
- 対話ウィザードではシークレット項目をマスク表示して保存確認を行う。

Notes / Known limitations
- research.factor_research の calc_momentum 実装は途中。ファクター計算は DuckDB 内のテーブル構造に依存しているため、実運用前にテーブルスキーマの整備が必要。
- position_sizing の価格欠損（price が 0.0 や未設定）の場合、現在はスキップしている。将来的に前日終値や取得原価でのフォールバックを検討する旨を TODO コメントで明記。
- process_priority / set_cpu_affinity は権限や OS に依存し、失敗時は警告でフォールバックする設計。期待どおり設定できない環境があり得る。
- validate_config は PyYAML が無ければ YAML パース検証をスキップする。厳密検証を行う場合は PyYAML をインストールすること。

Author
------
このリリースはリポジトリのコード構成およびファイル内コメント・実装から推測して作成しています。実際の変更履歴（コミット履歴）とは差異が生じる可能性があります。必要があれば実コミットログに基づく詳細な CHANGELOG 生成を支援します。