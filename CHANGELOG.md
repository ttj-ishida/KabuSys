# CHANGELOG

すべての注目すべき変更点を記録します。本プロジェクトは Keep a Changelog の形式に従います。

フォーマット:
- 目的別にカテゴリを分けています（Added / Changed / Fixed / Deprecated / Removed / Security）。
- 日付はリリース日です。

## [0.1.0] - 2026-04-23
初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。以下はコードベースから推測してまとめた主要な追加・改善点です。

### Added
- コア設定/起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用 SQLite（data/paper_trading.db を既定）に記録して本番 DB と分離する仕組みを実装。
    - ストップフラグ（data/stop_requested.flag）検知による安全停止、PID ファイル管理、スレッドでのエンジン実行管理を導入。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するエントリポイントを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知でループ終了、check_once() の例外を捕捉して次回ポーリングへ継続。

- 設定関連ユーティリティ
  - config.py: 環境変数 / .env 自動読み込み機能、.env パース（コメント、クォート、export 形式の対応）、「Settings」ラッパーを実装。
    - 自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行う。無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
    - 各種設定プロパティ（DB パス、paper_trading 用パス、PID/kill flag パス、閾値等）を提供。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を実装。
    - 入力時にシークレットマスク、選択肢、既存値の再利用などをサポート。
    - .env を書き出す際のテンプレート注記（Git にコミットしない旨）を挿入。
  - validate_config.py: 起動前に .env と config/*.yaml の設定検証を行う CLI を実装。
    - 必須環境変数チェック、パスの存在チェック、YAML パーサがある場合は YAML のパース検証、KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や Kill Switch 設定の警告）などを行う。
    - --strict モードで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順（同点時 signal_rank）で候補選定。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコア全0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（sell予定銘柄は除外、"unknown" セクターは上限適用外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた株数算出、単元株丸め（lot_size）、per-position / aggregate 上限、available_cash に基づくスケールダウン（端数処理で残余を再配分）などを実装。
    - cost_buffer（スリッページ・手数料見積り）を考慮した保守的なコスト計算をサポート。

- 研究/分析ユーティリティ
  - research/factor_research.py（ファクター計算モジュール）を追加（モメンタム / MA200 / ATR / 流動性 等の計算を想定）。（注: ファイル末尾が切れている箇所あり。実装中の可能性あり）

- その他ユーティリティ
  - utils/logging_setup.py: 統一的ログ設定ユーティリティ。
    - コンソール出力（stdout）と日次ローテートファイル出力（TimedRotatingFileHandler、30日保持）をルートロガーに設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみ継続する安全な挙動。
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でプロセス優先度設定、CPU affinity 設定を提供。例外時は警告ログでスキップ。
  - tools/paper_verification_report.py: Paper Trading 用 SQLite DB から検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）等を算出し、閾値に基づく PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db、コマンドラインで期間や DB を指定可能。

- パッケージ基本情報
  - __init__.py にバージョン 0.1.0 を付与。

### Changed
- 環境変数読み込みの振る舞い
  - 自動ロードの優先順位は OS 環境変数 > .env.local > .env。OS 環境変数は保護され、.env.local で上書き可能。
  - .env のパースは export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応して堅牢化。

- ログ設定
  - stdout を StreamHandler に利用（stderr ではなく stdout）。ログディレクトリ作成失敗時はフォールバックでコンソールのみ出力。

- 実行時の優先度設定
  - 起動スクリプト（execution / monitoring）は最初に set_process_priority("high") を呼び、可能ならプロセス優先度を引き上げる動作を行う（失敗時は警告で継続）。

### Fixed
- 複数の場所で例外安全化を実施：
  - run_monitoring.py のポーリング内で monitor.check_once() が例外を投げてもログを出して次のポーリングに継続するようにした。
  - logging_setup: 既存ハンドラの flush/close を試みた後に削除して二重登録を防止。
  - process_priority / set_cpu_affinity: 権限や未実装機能への例外を捕捉してワーニングでスキップ。

### Known issues / Notes（コードコメントからの推測）
- research/factor_research.py の末尾が切れている / 実装途中の可能性がある（calc_momentum が途中で終わっている）。実運用前に完成とテストが必要。
- position_sizing.calc_position_sizes:
  - price が 0.0 の場合にエクスポージャーや上限計算が過少見積りになる旨の TODO コメントあり（前日終値等をフォールバックする改善が検討対象）。
  - 単元サイズ（lot_size）の将来的な拡張（銘柄別 lot_map のサポート）を検討中。
- run_monitoring.py は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明記されている。paper_trading と monitoring DB を明確に分離したい場合は設定見直しが必要。
- validate_config の YAML 検証は PyYAML 未インストール時はスキップされるため、YAML 検証を有効にするには PyYAML をインストールする必要がある。

### Deprecated
- なし（初回リリースのため該当なし）。

### Removed
- なし（初回リリースのため該当なし）。

### Security
- なし（公開コードからは特段のセキュリティ修正は推測できません。API トークン等は .env に保存する想定のため .env を Git にコミットしない旨をドキュメントに明記済み）。

---

注: 本 CHANGELOG は与えられたソースコード（コメント・実装内容）から推測して作成したものであり、実際のリリースノートは開発者の意図・リリース履歴に基づいて調整してください。必要であれば、リリース日やカテゴリ分けの修正、より詳細な変更説明（例: 各関数のインターフェース変更点、既知のバグと回避策）を追加できます。