# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-25
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。主な追加機能・改善点は以下の通りです。

### Added
- 全体
  - パッケージ初期バージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
- 環境・設定管理
  - Settings クラスを実装し、環境変数経由で設定値を取得可能に（src/kabusys/config.py）。
  - .env ファイルの自動ロード機能を実装（プロジェクトルート検出: .git / pyproject.toml ベース）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env パース機能を強化（export KEY=val、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - .env の対話式ウィザードを追加（src/kabusys/config_setup.py）。初期 .env の生成・更新を支援。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。必須環境変数、KABUSYS_ENV, LOG_LEVEL, DB パス、config/*.yaml の存在と YAML パース（PyYAML インストール時）をチェック。
- 起動スクリプト / 実行系
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory により実環境／モックの切替を行う設計。
    - ExecutionEngine をスレッドで起動し、stop フラグ（data/stop_requested.flag）や pid 管理をサポート。
    - 起動時にプロセス優先度を "high" に設定。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB 接続は環境にかかわらず本番 sqlite_path を使用（監視データを一元管理）。
    - stop フラグ検出でループ終了、例外発生時はロギングして次ポーリングへ続行。
- ロギング・プロセス管理ユーティリティ
  - 統一的なログ設定ユーティリティを実装（src/kabusys/utils/logging_setup.py）。
    - stdout への出力 + 日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL 環境変数に対応。ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみを使用。
  - プロセス優先度・CPU affinity ユーティリティを実装（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収し、nice / Windows priority クラスで優先度変更を試行。
    - CPU affinity 固定機能（set_cpu_affinity）を提供。権限不足時は警告を出してスキップ。
- ポートフォリオ構築（Portfolio construction）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights を実装（スコア正規化や同点ブレークの挙動を含む）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap：既存保有のセクター暴露に応じて新規候補を除外。
    - calc_regime_multiplier：market regime（bull/neutral/bear）に基づく投下資金乗数。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score の配分方式に対応。単元（lot_size）丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積り、残余の分配ロジックを実装。
- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / MA200 / ATR 等を計算するための土台を実装（DuckDB と prices_daily/raw_financials テーブル参照想定）。（ファイルは途中まで実装）
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを集計し PASS/FAIL 判定を出力する CLI。
    - P95 計算・日付フィルタ・DB 存在チェック等を備える。
- DB / その他
  - monitoring 用 DB 初期化ヘルパー呼び出しを各起動スクリプトで行う（init_monitoring_db を使用して冪等に監視テーブルを保証）。
  - DuckDB 接続の利用を起動スクリプト/リサーチでサポート。

### Changed
- .env 読み込み順序と上書きルールを明確化
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - .env.local は既存の OS 環境変数を保護しつつ上書き可能（protected set により上書きを制限）。
- validate_config の出力改善
  - PyYAML が未インストールの場合は YAML 検証をスキップして警告出力。
  - KABUSYS_ENV=live 時に本番向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START 設定の危険性）を警告。

### Fixed
- .env パースの不正な行やコメント処理に起因する誤読を修正（クォート / エスケープ / inline comment の処理を改善）。

### Documentation / CLI
- 各スクリプトに簡易な使用方法コメントを追加（run_monitoring/run_execution/config_setup/validate_config/paper_verification_report）。
- config_setup ウィザードは保存前に確認画面を表示し、.env ファイルにテンプレート形式で書き出す。

### Notes / Known issues / TODO
- apply_sector_cap の価格欠損（price == 0.0）時の過少見積り問題について TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討予定。
- position_sizing の将来的拡張: 銘柄毎に単元サイズ(lot_size)を持つ設計への対応を想定（TODO 補足）。
- research.factor_research はファクター群の計算ロジックの実装途中（ファイル末尾で途切れ）。DuckDB のテーブル定義と連携して完成予定。
- run_monitoring は監視 DB に本番 sqlite_path を使用するため、監視だけであっても本番 DB ポイントへのアクセスになる点に注意。
- process_priority / set_cpu_affinity は権限やプラットフォームによっては動作しない場合があり、その場合は警告を出してスキップする設計。

---

今後の予定:
- research モジュールの完成（Momentum 等の集計ロジック実装完了）。
- ExecutionEngine / Broker クライアント周りのテスト強化、paper/live の振る舞い確認。
- モニタリング指標のダッシュボード化・アラート連携（LINE 等）。
- サンプル config/*.yaml の生成スクリプトと CI での設定検証導入。

---
変更内容に疑問や追記希望があれば教えてください。必要に応じて日付や項目の粒度を調整して更新します。