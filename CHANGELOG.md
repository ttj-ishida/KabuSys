Keep a Changelog
=================

すべての注目すべき変更をこのファイルで記録します。  
フォーマットは「Keep a Changelog」を準拠しています。

※ この CHANGELOG はソースコードから推測して自動生成しています。実際のコミット履歴ではない点にご注意ください。

Unreleased
----------

- なし

0.1.0 - 2026-04-22
------------------

Added
- 基本アプリケーションパッケージ kabusys を追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカー抽象化、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
    - 起動前にプロセス優先度を "high" に設定。
    - 実行中は data/execution.pid に PID を書き、 data/stop_requested.flag による停止をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトへフォールバック。
    - 監視は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する設計（監視 DB は固定して扱う方針）。
    - 停止フラグ (data/stop_requested.flag) による終了、KeyboardInterrupt のハンドリングを実装。
- 設定管理
  - config.py
    - 環境変数／.env の読み込みロジックを実装（プロジェクトルートを .git / pyproject.toml で探索）。
    - .env/.env.local の自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - export KEY=val やクォート文字列、インラインコメントなどを考慮した .env 行パーサ実装。
    - Settings クラスで各種設定をプロパティとして取得可能（DB パス、KABUSYS_ENV 判定、paper_trading 用設定、監視閾値など）。
    - PAPER_FILL_MODE の検証（instant/partial/never/reject）。
- 設定補助ツール
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を実装。
    - J-Quants / kabu API 等の必須項目、DB パス、ログレベル、Kill Switch の自動クリア設定などを対話的に入力できる。
    - .env の読み書きロジック（既存値の再利用、シークレットの非表示表示、確認プロンプト）を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の設定不備を検出する CLI。
    - 必須環境変数の確認、KABUSYS_ENV の検証、DB パス親ディレクトリの存在チェック、YAML ファイルの存在とパース検証（PyYAML がない場合は警告）、
      本番環境向けの追加ガード（LINE トークン未設定や KILL_FLAG_CLEAR_ON_START の危険設定）を実装。
    - --strict オプションで警告も FAIL（exit 1）として扱う。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から検証レポートを生成する CLI。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計し PASS/FAIL を判定するしきい値を定義（デフォルト: 稼働率 >=99%、fill_rate >=90%、send_rate >=95%、P95 <=200ms）。
    - --from / --to / --db オプションに対応。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコア全てが 0 の場合のフォールバック挙動を実装（等配分 + 警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジームに応じた資金乗数（calc_regime_multiplier）を実装。
    - unknown セクターはセクター上限の対象外とする挙動。
    - レジームが未知の場合は 1.0 にフォールバック（警告ログ）。
  - portfolio/position_sizing.py
    - position size の計算（risk_based / equal / score）を実装。
    - 単元株（lot_size）丸め、1 銘柄上限・アグリゲートキャップ（available_cash）でスケールダウン、cost_buffer を用いた保守的コスト見積り、残差配分ロジック（lot 単位で再配分）を実装。
- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定関数 setup_logging を提供。
    - stdout への StreamHandler（stdout を使用）、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして console のみで継続するフォールバックを実装。
  - utils/process_priority.py
    - Windows / POSIX の差分を吸収したプロセス優先度設定（set_process_priority）を実装。psutil を使用。
    - CPU affinity を設定する set_cpu_affinity を実装（権限不足や未対応環境は警告でスキップ）。
- データ解析・研究モジュール（着手）
  - research/factor_research.py
    - ファクター計算のための設計と各種パラメータ定義（モメンタム期間、ATR 期間等）および calc_momentum の骨組みを追加（DuckDB 接続を受ける方針）。
    - （実装は継続中：ソースの途中で切れているため注意）

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Deprecated
- なし

Removed
- なし

Security
- 環境ファイル .env を Git にコミットしない旨を config_setup の出力に明記。

Notes / 実装上の注意点（既知の挙動・制約）
- .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの常識的な取り扱いに対応。ただし極端なエッジケースは未検証。
- config.py による .env 自動ロードはプロジェクトルートの検出に依存する（.git または pyproject.toml）。配布後や特殊配置では自動ロードがスキップされる可能性がある点に注意。
- run_monitoring は監視用 DB に対して常に settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計になっているため、監視データを paper_trading DB と分離したい場合は運用上の注意が必要。
- process priority / cpu affinity の変更は権限不足やプラットフォーム差により失敗する可能性があり、その場合は警告を出してスキップする実装。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力を無効化するフォールバックを行うため、ファイル出力が行われない場合は stderr に警告が出力される。
- research/factor_research.py の calc_momentum の実装が途中で終わっている（現在は骨組みと定数のみ存在）。研究系機能は今後の継続実装が必要。

今後の TODO（想定）
- research/factor_research.py のファクター計算関数の完成（Momentum / Value / Volatility / Liquidity）。
- ポートフォリオ構築関連のユニットテスト充実（edge cases の検証）。
- SystemMonitor / ExecutionEngine 周辺の統合テストおよび graceful shutdown の追加改善。
- 単元株（lot_size）を銘柄ごとに設定可能にする拡張（コメントに TODO あり）。

Contact / 開発者メモ
- この CHANGELOG はコードの状態から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。リリース作業時はコミットログに基づいた正式な CHANGELOG への置換を推奨します。