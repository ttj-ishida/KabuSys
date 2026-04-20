CHANGELOG
=========

このファイルは "Keep a Changelog" の形式に準拠しています。  
日付はコードから推測できる最終更新日（本ファイル作成日: 2026-04-20）を使用しています。  
（コードベースの内容から機能追加・振る舞いを推測して記載しています。）

Unreleased
----------

- 開発中の変更点や未リリースの修正・機能をここに記載します。

[0.1.0] - 2026-04-20
--------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - 実行系 / 監視系の起動スクリプト
    - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用の SQLite DB に分離して記録する挙動をサポート。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ（data/stop_requested.flag）で安全に停止可能。
  - 設定管理
    - config.py: .env 自動読み込み（.env, .env.local の優先順）・環境変数取得ラッパー。PAPER_FILL_MODE の検証、DB パス・ログレベルの取得などを提供。
    - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - validate_config.py: .env および config/*.yaml の検証 CLI。--strict フラグで警告を FAIL 扱いにできる。
  - ポートフォリオ構築ライブラリ（純粋関数群、メモリ内計算）
    - portfolio.portfolio_builder: 候補選定 (select_candidates)、等配分 / スコア加重の重み計算 (calc_equal_weights, calc_score_weights)。
    - portfolio.position_sizing: 発注株数算出ロジック (calc_position_sizes)。risk_based / equal / score の allocation_method をサポートし、単元株（lot_size）丸め・aggregate cap スケーリングを実装。
    - portfolio.risk_adjustment: セクター集中制限 (apply_sector_cap)、レジーム乗数 (calc_regime_multiplier)。
  - ツール
    - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプト。稼働率、注文成功率、送信率、レイテンシなどを集計して PASS/FAIL を判定。
  - 研究用モジュール
    - research.factor_research: Momentum / Value / Volatility / Liquidity 等のファクター計算（DuckDB 接続を受けて prices_daily / raw_financials を参照する方針）。
  - ユーティリティ
    - utils.logging_setup: stdout ストリームハンドラと日次ローテーションのファイルハンドラをルートロガーに設定するユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - utils.process_priority: Windows/Linux/Mac の差を吸収してプロセス優先度（および CPU affinity）を設定するユーティリティ。アクセス権限や未対応 OS の場合は警告を出してスキップ。
  - DB 統合
    - SQLite（監視用/ペーパートレード用）と DuckDB（分析用）の両方を使用する設計を導入。paper_trading の実行は本番 SQLite と分離して専用ファイルを使用。
  - プロセス管理 / 制御
    - PID ファイル、停止フラグ（stop_requested.flag）、Kill Switch のパラメータ化（KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）を追加。
  - バージョン情報
    - パッケージバージョンを __version__ = "0.1.0" として定義。

Changed
- （初期リリースのため該当なし）

Fixed / Hardened behavior
- 環境変数パースの堅牢化
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントの取り扱いに対応。
  - 自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入し、.env.local の上書き挙動を制御。
- 設定の不正値に対するフォールバックと警告
  - MONITOR_POLL_INTERVAL が不正（整数でない、0以下など）の場合、デフォルト (60秒) にフォールバックして警告を出力。
  - calc_score_weights: 全銘柄のスコアが 0.0 の場合は等金額配分にフォールバックして warning を出す。
  - calc_regime_multiplier: 未知のレジーム値は 1.0 にフォールバックして warning を出力。
  - logging_setup: ログディレクトリ作成やファイルハンドラ作成失敗は捕捉され、コンソール出力のみで継続するように堅牢化。
  - process_priority: 権限不足や未サポート環境での失敗を捕捉して警告を出力し、処理をスキップ。
- ExecutionEngine と Monitoring の安全停止
  - 起動時・実行中に stop flag が立っている場合の早期終了や、監視ループ内での例外捕捉により次ポーリングまで継続する挙動を実装。KeyboardInterrupt のハンドリングも追加。

Security
- 機密情報の取り扱い
  - config_setup の対話ではシークレット項目（J-Quants リフレッシュトークン、kabu API パスワード、LINE トークン等）をマスクして表示。
  - .env の説明に「.env は絶対に Git にコミットしないこと」を明記。

Notes / その他
- DuckDB / SQLite を併用する設計により、分析・集計処理（research, tools）と運用向け監視・注文履歴（SQLite）を分離。
- PAPER_FILL_MODE の有効値制約（instant, partial, never, reject）を導入し、不正値は ValueError で検出。
- validate_config.py は PyYAML が無ければ YAML ファイル検証をスキップし、インストール状況を警告する。
- paper_verification_report は期間指定（--from, --to）および DB パス指定（--db / 環境変数）に対応。P95 計算や N/A 表示などを実装。

Acknowledgements / TODO（コード内コメントより）
- position_sizing の lot_size 固定設計は将来的に銘柄別拡張（stocks マスタに lot_size を持たせる）を検討する旨が記載されている。
- apply_sector_cap の価格欠損（price == 0.0）の取り扱いに改善余地がある旨の TODO コメントあり。
- research.factor_research モジュールは詳細実装（ファクター計算の続き）が未完の箇所がある（ファイル末尾が途中で切れているように見える）。将来的に完成予定。

References
- この CHANGELOG はコードから推測して作成しています。実際のリリースノートや変更履歴とは差異がある可能性があります。実リリース用にはコミット履歴やリリース担当者の意図を基に修正してください。