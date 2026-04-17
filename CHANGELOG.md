# CHANGELOG

すべての変更は「Keep a Changelog」形式に従って記載しています。セマンティックバージョニングを想定しています。

現在のパッケージバージョン: 0.1.0

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-17

Added
- 基本アプリケーション基盤を追加
  - パッケージ初期バージョンとして、監視・実行・設定管理・ポートフォリオ構築・リサーチ・ユーティリティ群・ツールを含む主要モジュールを追加。
- 実行エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。paper_trading 環境時には MockBrokerClient を利用して data/paper_trading.db に記録する仕組みをサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視 DB は環境にかかわらず本番 sqlite_path を使用する実装。
- 設定管理・ウィザード・検証
  - config.py: .env 自動ロード（.env, .env.local）機能を実装。環境変数のパースは引用符とエスケープに対応し、`export KEY=val` 形式もサポート。Settings クラスで各種設定値（DB パス、PID ファイル、KABUSYS_ENV、各種閾値など）をプロパティとして提供し、妥当性チェックを実施。
  - config_setup.py: 対話式ウィザードで .env の初期作成・更新を行う CLI を追加。秘密値はマスク表示、選択肢やデフォルトをサポート。
  - validate_config.py: 起動前に .env および config/*.yaml の存在・基本妥当性を検証する CLI を追加。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築機能
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。スコア全0 の場合は等配分へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた投下資金乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" をサポート、未知のレジームはフォールバック）。
  - portfolio/position_sizing.py: position sizing ロジックを実装。allocation_method に応じた株数計算（risk_based / equal / score）、単元株丸め、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer を考慮した保守的見積り、残差分の lot 単位での再配分ロジックを実装。
- リサーチ（ファクター計算）
  - research/factor_research.py: DuckDB を用いて momentum（1M/3M/6M、MA200 乖離）や volatility（ATR20、出来高指標等）を計算する関数を追加。prices_daily テーブル参照で、データ不足時の None 処理やスキャン期間のバッファを実装。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）向けにプロセス優先度設定と CPU affinity 設定を実装。psutil によるアクセス失敗時は警告を出すフェイルセーフを用意。
- 監視・検証ツール
  - monitoring モジュールの DB 初期化（init_monitoring_db）や SystemMonitor を利用する run_monitoring スクリプトを追加。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を出力。

Changed
- （初回リリース）設計上の決定点をドキュメント化
  - Monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明確化（run_monitoring）。
  - Paper Trading は本番 DB と明確に分離される（PAPER_TRADING_SQLITE_PATH を使用、run_execution の接続分岐）。
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化できる仕組みを追加（テスト等のため）。

Fixed
- .env パーシングの堅牢化
  - config._parse_env_line: シングル/ダブルクォート内のバックスラッシュエスケープと対応する閉じクォートの処理、インラインコメントの扱いなどを実装し、より現実的な .env 設定に耐えうるよう改良。

Security
- 秘密情報の取り扱いに配慮
  - config_setup の表示では秘密値をマスクし、README/ウィザードの案内で .env を Git にコミットしないよう注意喚起を出力。

Notes / Behaviors
- プロセス優先度は起動直後に "high" にセットされることを意図している（set_process_priority を run_* の最初で呼び出す）。
- run_execution は実行中に data/stop_requested.flag を監視し、検知時にエンジン停止を試みる。PID ファイル（data/execution.pid 等）を利用。
- 設定の妥当性チェック（validate_config）は PyYAML が未インストールの場合、YAML の検証をスキップして警告を出す。
- PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL などの環境変数は設定値チェックを行い、不正値時に明示的なエラー（または ValueError）を投げる。
- DuckDB と SQLite の混在利用を前提としており、分析（DuckDB）と運用（SQLite）の役割を分離。

既知の限定事項 / TODO
- position_sizing の lot_size は全銘柄共通で固定（将来的に銘柄別単元サイズ対応を予定）。
- apply_sector_cap の exposure 算出で price が欠損（0.0）の場合に過少見積りになる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討中。
- research/factor_research の一部（ファイル途中）が現時点で未公開の補助関数を含む可能性があり、さらなるテストとチューニングが必要。

----

この CHANGELOG は、提供されたコードベース（src/kabusys 以下）から推測して作成した初版リリースノートです。詳細なリリース日や追加の変更履歴がある場合は、適宜更新してください。