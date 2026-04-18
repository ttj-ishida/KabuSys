# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
日付はリリース日を示します。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 初期リリース: KabuSys 基本モジュール群を追加。
- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、PID ファイル管理、停止フラグ監視、スレッド実行フローを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は本番 sqlite_path を使用する設計。
- 設定管理 / ユーティリティ
  - config.py: Settings クラスを追加し、環境変数アクセスのラッパーとバリデーションを提供。自動 .env ロード（.env, .env.local）を実装。PAPER_FILL_MODE の検証等の各種プロパティを提供。
  - config_setup.py: 対話式 .env 作成 / 更新ウィザードを追加。シークレット入力や既存値の再利用、.env の書き出しをサポート。
  - validate_config.py: 起動前の構成検証 CLI を追加。必須環境変数、パス、config/*.yaml の存在や YAML パース検証、KABUSYS_ENV による本番ガードなどをチェック。--strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス制御
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール(stdout) 出力と日次ローテート (TimedRotatingFileHandler) のファイル出力を設定。ログディレクトリ作成失敗時はファイル出力をスキップ。
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加（Windows / POSIX に対応）。set_process_priority と set_cpu_affinity を提供。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
  - portfolio/risk_adjustment.py: セクター集中制限の apply_sector_cap、レジーム乗数 calc_regime_multiplier を追加。
  - portfolio/position_sizing.py: 発注株数計算 calc_position_sizes を追加。risk_based / equal / score の配分方式、単元株丸め (lot_size)、aggregate cap によるスケールダウンロジックを実装。
- 解析 / ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。稼働率・注文成功率・送信率・P95 レイテンシなどを計算し PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH を参照可能。
- 研究用モジュール
  - research/factor_research.py: ファクター計算モジュールの骨組み（モメンタム等）を追加（DuckDB を利用する設計）。

### 変更 (Changed)
- DB 分離ポリシーの明確化:
  - 実行系 (run_execution) は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（data/paper_trading.db 既定）を使用して本番 DB と分離するよう実装。
  - 監視系 (run_monitoring) は環境に依存せず本番 sqlite_path を使用する旨を明記。
- .env の自動読み込み:
  - config.py でプロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動読み込み。OS 環境変数は保護（override の制御）されるよう変更。
- ログの標準出力先を stdout に統一:
  - logging_setup により、StreamHandler は stdout を使うようにし、cron 等からのリダイレクト運用を想定。
- プロセス優先度設定を起動直後に実行:
  - run_execution と run_monitoring の両方で起動直後に set_process_priority("high") を呼び出すようにした。
- validate_config のチェック追加:
  - config/*.yaml の存在チェックおよび（PyYAML が有効な場合）パース検証を行うようにした。
  - KABUSYS_ENV=live に対する追加注意（LINE 設定や KILL_FLAG_CLEAR_ON_START のチェック）を追加。

### 修正 (Fixed)
- .env パーサの改善:
  - export KEY=val 形式、シングル/ダブルクォートされた値（エスケープ対応）、行内コメントの扱い、キーのトリム等に対応する堅牢なパーサを実装。
  - _load_env_file で既存 OS 環境変数を保護する protected 引数を導入し、意図しない上書きを防止。
- calc_score_weights のゼロスコア対処:
  - 全銘柄のスコア合計が 0 の場合は等金額配分にフォールバックし WARNING を出力するよう修正。
- calc_position_sizes のスケールダウンアルゴリズム:
  - aggregate cap 超過時のスケールダウン処理を実装。lot_size 単位での切り上げ配分（残余キャッシュを fractional 残差順に割り当て）を行い、再現性のためソート基準を安定化。
- run_execution / run_monitoring の停止フラグ挙動:
  - data/stop_requested.flag を検知して安全に停止するロジックを追加（既に停止フラグがある場合は起動をスキップする挙動を含む）。
- logging_setup のハンドラ重複防止:
  - 既存ハンドラを一度 flush/close のうえ削除してから新しいハンドラを設定するようにして二重設定を防止。

### ドキュメント (Documentation)
- 各モジュールに docstring と使用例、設計メモ（PortfolioConstruction.md / StrategyModel.md 参照箇所）を追加。config_setup と validate_config に利用手順を記載。

### その他 (Other)
- DuckDB / SQLite を組み合わせた設計を採用。monitoring 用テーブル初期化 (init_monitoring_db) を idempotent に呼び出すことで DB スキーマの保証を実現。
- パッケージ __version__ を 0.1.0 に設定。

---

参考: 実装ファイルの主な場所
- スクリプト: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- 設定: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- ログ/プロセス: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py
- ポートフォリオ: src/kabusys/portfolio/*
- ツール: src/kabusys/tools/paper_verification_report.py
- 研究用: src/kabusys/research/factor_research.py

今後の TODO（実装予定・検討事項の抜粋）
- position_sizing: 銘柄ごとの lot_size をマスタから取得する拡張。
- apply_sector_cap: price 欠損時のフォールバック価格 (前日終値など) の導入。
- factor_research: 各ファクターの完全実装とテスト追加。
- 監視・実行のユニット/統合テスト整備とデバッグ運用の向上。