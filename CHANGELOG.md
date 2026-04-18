# Changelog

すべての重要な変更履歴をここに記載します。  
本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

[0.1.0] - 2026-04-18
--------------------

### Added
- 初期リリースを追加（バージョン 0.1.0）。
- 実行用エントリポイント:
  - run_execution.py — ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使い、paper_trading 用の SQLite DB（data/paper_trading.db）と分離して動作。
  - run_monitoring.py — SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視用 DB は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定・検証用 CLI:
  - config_setup.py — 対話式ウィザードで .env を初期作成 / 更新する機能を追加（各種項目、シークレット入力、既存値の再利用、保存確認）。
  - validate_config.py — 起動前の設定検証ツールを追加（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパースなど）。`--strict` オプションで警告も FAIL 扱いにできる。
- ツール:
  - tools/paper_verification_report.py — ペーパートレード用検証レポート生成ツールを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を行う。
- 設定管理:
  - config.py — Settings クラスを実装。環境変数の自動読み込み（.env, .env.local）、.env の複雑なパース（export プレフィクス、クォート、エスケープ、インラインコメントの取り扱い）を実装。プロジェクトルート検出は .git または pyproject.toml を基準に行う。
  - settings オブジェクトをエクスポート。
- ロギング:
  - utils/logging_setup.py — 統一されたログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーへ設定。LOG_DIR / LOG_LEVEL の解決順を明記し、ログディレクトリ作成失敗時のフォールバックを実装。
- プロセス管理:
  - utils/process_priority.py — Windows/Linux/macOS を吸収するプロセス優先度設定ユーティリティを追加。set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。アクセス権限や未対応 OS 時は警告を出してスキップする。
- ポートフォリオ構築関連（純粋関数群、DB 非依存）:
  - portfolio/portfolio_builder.py — select_candidates, calc_equal_weights, calc_score_weights を追加（スコア正規化・同点タイブレーク、スコア全0時のフォールバック）。
  - portfolio/risk_adjustment.py — apply_sector_cap（セクター集中制限）と calc_regime_multiplier（市場レジームに応じた投下資金乗数）を追加。
  - portfolio/position_sizing.py — calc_position_sizes を追加（risk_based / equal / score の配分方式, lot_size 切り捨て・aggregate cap スケーリング・cost_buffer 考慮）。
  - portfolio パッケージ __all__ を整備。
- リサーチ:
  - research/factor_research.py — ファクター計算モジュールを追加（モメンタム、MA200、ATR、流動性等の計算を想定、DuckDB 接続を受ける設計）。（注: ファイルは設計・実装の骨子を含む）
- 監視 DB 初期化ユーティリティ（monitoring.monitoring_db の利用）へのフックを各起動スクリプトで呼び出し、テーブル存在を保証。

### Changed
- 実行・監視の挙動:
  - run_execution と run_monitoring は起動直後にプロセス優先度を "high" に設定するように変更（set_process_priority を最初に呼び出す）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を利用することで本番 DB と明確に分離するように設計。
  - run_monitoring は監視用の DB 接続を常に本番 sqlite_path に接続する設計（運用上の一貫性を重視）。
- ログ出力はコンソールに stdout を使用（stderr ではない）して、cron/Task Scheduler 等とのリダイレクト運用を容易にした。
- .env 自動読み込みの優先順位を明確化（OS 環境変数 > .env.local > .env）。既存の OS 環境変数は保護（上書き禁止）。
- .env パーサー:
  - export プレフィクス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、コメント処理の改善などを導入。
- validate_config のチェック拡張:
  - config/*.yaml の存在確認と PyYAML によるパースチェック（PyYAML 未インストール時は警告でスキップ）。
  - KABUSYS_ENV=live 時のガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）を追加。
- ExecutionEngine 周辺の既定値を明記:
  - RiskManager のデフォルト RiskConfig 値を実装（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。initial_portfolio_value は broker.get_available_cash() を初期値として設定。

### Fixed
- 環境変数の数値パースの堅牢化:
  - MONITOR_POLL_INTERVAL の値が不正（非数値または 0 以下）だった場合にデフォルトへフォールバックするようにし、警告を出すようにした（run_monitoring の _get_poll_interval）。
- calc_score_weights:
  - 全銘柄のスコア合計が 0.0 の場合に等金額配分へフォールバックして警告を出すようにした。
- calc_position_sizes:
  - 単元株（lot_size）で切り捨て・スケーリングする際の端数処理と aggregate cap スケーリングのアルゴリズムを整備。残余キャッシュによる追加配分ロジックを実装して投資合計が available_cash を超えないように制御。
- paper_verification_report:
  - P95 計算、日付フィルタの組み立て、DB 存在チェックとエラーメッセージを堅牢化。
- process_priority:
  - 未対応 OS や権限不足の場合に例外ではなく警告でスキップするように変更して起動の安定性を改善。

### Documentation / UX
- config_setup の対話式ウィザード:
  - 既存 .env の読み込み、シークレットのマスク表示、選択肢バリデーション、保存確認を実装。生成される .env ファイルのヘッダに注意書き（絶対に Git にコミットしない）を付与。
- utils/logging_setup:
  - 既存ハンドラを安全にクリアしてから再設定することで多重ハンドラ登録を防止。
  - ログハンドラ作成失敗時のフォールバック振る舞い（コンソール出力のみ）を文書化。

### Security
- .env の取り扱いに関する注意点を明記（.env を Git にコミットしない旨のヘッダを生成）。
- Settings._require() で必須環境変数未設定時に明確なエラーを投げることで起動時の不備を早期に検出。

### Known limitations / Notes
- research/factor_research.py はモジュール設計とモメンタム計算の骨格を含むが、一部実装がファイル末尾で途切れている（今後の実装拡張を想定）。
- apply_sector_cap は "unknown" セクターの扱いを緩めており、price_map に欠損（0.0）があるとエクスポージャーが過少見積りされる旨の TODO コメントがある。将来的に価格フォールバックの導入を検討。
- process_priority や CPU affinity の設定は OS 権限や psutil のサポート状況に依存するため、失敗時は警告でスキップする挙動にしている。

(今後はリリースごとに機能追加・修正を細かく分けて CHANGELOG を更新してください。)