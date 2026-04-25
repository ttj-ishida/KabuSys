# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマットの詳細: https://keepachangelog.com/（英語）

## [0.1.0] - 2026-04-25
Initial public release.

### Added
- 全体
  - パッケージ初期リリース。日本株自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築・ポジション計算、設定管理、検証ツール、およびペーパートレード用検証レポート生成を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による動作分岐をサポート（`paper_trading` 時は paper DB を使用、MockBrokerClient の利用を想定）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` により上書き可能。

- 設定管理・ウィザード・検証
  - config.py: .env 自動読み込み（プロジェクトルート探索）、環境変数取得ヘルパー `Settings` を追加。多数の設定プロパティ（DB パス、API トークン、監視閾値等）を提供。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（対話プロンプト、既存 .env 読み込み、ファイル書き出し）。
  - validate_config.py: 起動前に .env や config/*.yaml を検証する CLI を追加。`--strict` オプションで警告を失敗扱いに可能。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: コンソール（stdout）と日次ローテーションファイルハンドラをルートロガーに設定する共通ロギング初期化を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてフォールバック。
  - utils/process_priority.py: Windows/Linux/macOS 向けのプロセス優先度設定および CPU affinity 設定を追加。アクセス拒否や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定（ソートのタイブレークを含む）と重み計算（等配分・スコア加重）を追加。スコア合計がゼロの場合は等配分にフォールバック。
  - portfolio/position_sizing.py: 発注株数計算（allocation_method: risk_based / equal / score、lot_size 丸め、aggregate cap スケーリング・端数処理）を追加。費用バッファ（cost_buffer）や単元処理をサポート。
  - portfolio/risk_adjustment.py: セクター集中上限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。未知レジームはフォールバック（警告）。

- リサーチ
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム／ボラティリティ／流動性／ファンダメンタル等を想定）。DuckDB を用いた設計を採用（prices_daily, raw_financials を参照）。

- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を算出し PASS/FAIL 判定を行う。P95 計算ユーティリティを含む。コマンドラインから期間指定や DB パス指定が可能。

### Changed
- 起動時の DB 接続方針を明確化
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する設計を明記（run_monitoring.py）。
  - 実行エンジン（execution）は `paper_trading` 環境時に paper 用 SQLite を使用して本番 DB と分離（run_execution.py）。

- .env 読み込みの振る舞い
  - config.py: 自動ロードの優先順を OS 環境変数 > .env.local > .env に設定。`.git` または `pyproject.toml` を基準にプロジェクトルートを探索するため、CWD に依存しない実装に変更。
  - .env の解析機能を強化（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い改善）。

- ロギング
  - logging_setup: stdout を StreamHandler に使用（stderr ではなく）して、cron/Task Scheduler で stdout/stderr を一本化する運用に適合。ログレベルとログディレクトリ解決順を明文化。

- プロセス優先度
  - process_priority: OS 毎の優先度マップを用意し、アクセス権限がない場合は警告で継続する耐障害性を強化。

- ExecutionEngine の起動/停止制御
  - run_execution.py: エンジンはデーモンスレッドで run_session を実行。停止フラグ検知時に engine.stop() を呼び出して安全に終了を試みる。起動前に停止フラグが既に存在する場合は起動をスキップ。

- エラーハンドリング
  - run_monitoring.py: poll ループ中の monitor.check_once() 呼び出しで例外が発生してもログ出力のうえ次回ポーリングへフォールバックするように変更。MONITOR_POLL_INTERVAL の不正値（非正数・非整数）時のフォールバック挙動を明確化（警告ログとデフォルト値使用）。

### Fixed
- 設定・検証
  - validate_config.py: PyYAML 未インストール時に YAML 検証をスキップして警告を出すようにした（ImportError を捕捉）。config/*.yaml の存在チェックと YAML パースエラーを適切にエラー/警告へ報告するよう修正。
  - validate_config: KABUSYS_ENV の値検証で不正値をエラー化、`live` 環境時に本番ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険な設定）を警告するよう追加。

- ポートフォリオ計算
  - portfolio_builder.calc_score_weights: 全銘柄のスコア合計が 0 の場合、ゼロ割りを避けて等金額配分にフォールバックし警告ログを出力するように修正。
  - position_sizing.calc_position_sizes:
    - lot_size（単元）で正しく丸めるように実装。
    - aggregate cap を超えた際のスケーリング処理で端数配分（残余を frac の大きい順に lot 単位で追加）を実装し、投資額の再現性と安定性を向上。
    - 価格欠損（price が None/0）の銘柄をスキップして例外的なゼロ除算や過誤を防止。

- セクター制約
  - risk_adjustment.apply_sector_cap: sector_map に存在しない銘柄を "unknown" 扱いにしてセクター上限チェックから除外するようにし、未知セクターで誤ってブロックされる問題を回避。

- ロギングのフォールバック
  - logging_setup: ログディレクトリ作成やファイルハンドラ生成に失敗した場合でも、コンソール出力は継続するように安定化（例外を握りつぶさず警告出力）。

- ツール（Paper レポート）
  - paper_verification_report: DB が存在しない場合に分かりやすいエラーメッセージを出力。SQL 実行時の OperationalError を捕捉して欠損テーブルがあってもレポート生成を継続可能に。

### Security
- `.env` ファイル
  - config_setup.py の生成テンプレートに「.env は絶対に Git にコミットしないこと」という注意を明記。

### Notes / Known limitations
- research/factor_research.py はモメンタム等の計算ロジックの骨組みを追加していますが、外部要件（prices_daily テーブルスキーマ等）に依存するため運用時にデータ準備が必要です。  
- 一部のユーティリティ（process_priority.set_cpu_affinity 等）は OS の権限に依存し、環境によっては効果が限定されます。該当ケースでは警告を出してスキップします。  
- ExecutionEngine / SystemMonitor 等の本体実装（engine.run_session, monitor.check_once 等）はこのリリース時点で所定の振る舞いを仮定しており、外部ブローカー実装や DB スキーマに合わせた追加調整が必要な場合があります。

もし CHANGELOG に追記したい変更点（リリース日を別にしたい、追加の修正/バグがある等）があれば教えてください。具体的なコミット履歴があればより正確なログを作成できます。