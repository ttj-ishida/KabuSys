# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。

注: 本 CHANGELOG はソースコードから推測して作成しています（実際のコミット履歴ではありません）。

## [Unreleased]

### Added
- docs/運用メモ（推定）
  - いくつかの未実装・改善予定箇所や TODO を明記（factor_research の未完実装、position_sizing の lot_size 拡張案、apply_sector_cap の価格フォールバック等）。

### Changed
- 設定検証・ウィザードの挙動改善予定
  - validate_config に --strict モードの取り扱い改善や YAML パースの安定化を検討。

### Fixed / Planned fixes
- factor_research モジュールの関数途中での切断（ソースが途中で終了しているため完全実装および追加のユニットテストが必要）
- 監視（monitoring）・実行（execution）プロセス周りの運用上の微調整（ログローテーション設定、停止フラグの取り扱い等）

---

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーションと CLI
  - kabusys パッケージの初期リリース。バージョンは __version__ = "0.1.0"。
  - 起動スクリプト:
    - run_monitoring.py — SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル検知による安全停止を実装。
    - run_execution.py — ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB と MockBroker を使用して本番 DB と分離。停止フラグによる停止制御、PID ファイル管理を実装。
  - 設定関連 CLI:
    - config_setup.py — .env を対話式に作成・更新するウィザードを提供。
    - validate_config.py — .env と config/*.yaml の簡易検証ツール。--strict オプションで警告を失敗 (exit 1) 扱いにできる。
  - ツール:
    - tools/paper_verification_report.py — Paper Trading 用の検証レポート生成スクリプト。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを算出し PASS/FAIL 判定を行う。期間指定や DB パス指定が可能。

- 設定・環境変数管理
  - config.py:
    - プロジェクトルートの自動検出機能（.git または pyproject.toml を探索）を実装し、.env/.env.local の自動ロードを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - 複数の設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別 等）。
    - PAPER_FILL_MODE に対するバリデーション（instant/partial/never/reject）を実装。
    - paper_trading 用の paper_sqlite_path を分離して提供。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates — BUY シグナルをスコア降順で選別。
    - calc_equal_weights / calc_score_weights — 等配分・スコア加重計算（スコアがすべて 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap — セクター別エクスポージャーを計算し、上限超過セクターの候補銘柄を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier — 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0、警告ログを出力）。
  - portfolio/position_sizing.py:
    - calc_position_sizes — allocation_method("risk_based"/"equal"/"score") に応じた発注株数計算、単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）に基づくスケーリングと端数処理を実装。
    - cost_buffer によりスリッページ・手数料を保守的に見積もるオプションを提供。
    - TODO を残しつつ（銘柄別 lot_size 情報の将来的導入など）、現時点で実用的なロジックを実装。

- 監視 DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等処理）。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30 日保持）を設定するユーティリティを提供。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続するフォールバック実装。
    - LOG_LEVEL / LOG_DIR の解決順を実装。
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度（nice / Windows priority class）を設定するユーティリティを提供。
    - CPU affinity 設定ヘルパー（最初の N コアに固定）を実装。権限不足など失敗時は警告ログでスキップ。

- 研究用ファクター計算（骨格実装）
  - research/factor_research.py:
    - モメンタム・移動平均・ATR 等を計算するための設計と定数を導入。calc_momentum の骨格が実装済（ただしソースが途中で終わっている箇所あり、完全実装は今後の課題）。

### Changed
- 複数の起動スクリプトでプロセス優先度を起動直後に "high" に設定するよう統一。
- run_monitoring と run_execution の DB 接続ポリシー:
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計（運用上の監視データは本番 DB を参照する想定）。
  - run_execution は paper_trading 時に paper_sqlite_path を使用し DB を分離。

### Fixed / Robustness
- .env パーサ:
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、クォートなしのコメント処理等に対応し、実運用 .env を比較的堅牢に読み込めるよう実装。
- logging_setup:
  - ハンドラ二重登録を防ぐため既存ハンドラをクリアしてから再設定する実装を導入。
  - 権限やファイルシステムエラー時のフォールバックを追加。
- process_priority:
  - 対応 OS を判定し、未対応 OS や権限不足時には安全にスキップしてログ出力するようにして安定性を向上。

### Documentation / UX
- config_setup の対話式ウィザード:
  - 各設定項目に説明、デフォルト、シークレットマスク表示、Enter で既存値再利用などを実装し初期セットアップを支援。
  - 保存前に確認プロンプトを表示。

### Removed / Deprecated
- なし（初期リリース）

### Known issues / Notes
- research/factor_research.calc_momentum の実装がソース途中で切れているため、ファクター計算の一部は未完成。ユニットテストと完成実装が必要。
- portfolio.apply_sector_cap は price が欠損（0.0）時にエクスポージャーが過小見積りされる可能性がある旨の TODO コメントあり。前日終値や取得原価を使うフォールバックの検討を推奨。
- position_sizing は将来的に銘柄別 lot_size をサポートする設計上の TODO がある。
- run_monitoring が本番 sqlite_path を参照する仕様は運用上の意図的選択だが、誤った環境設定時にデータを汚してしまうリスクがあるため運用手順の周知を推奨。

---

（追記・運用メモ）
- 実行コマンド例:
  - 監視起動: python -m kabusys.run_monitoring
  - エンジン起動: python -m kabusys.run_execution
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。README やリリースノートの整備、ユニットテストの追加、factor_research の完成を次のタスクとして推奨します。