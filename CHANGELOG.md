CHANGELOG
=========
（このファイルは Keep a Changelog の形式に準拠しています。すべての重要な変更をここに記録してください。）

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-19
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加しました。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine の起動スクリプトを追加。プロセス優先度設定、高速起動のための PID 管理、スレッド実行と停止フラグ監視、paper_trading 環境時の専用 SQLite DB 分離を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - 設定関連
    - config.py: .env の自動ロード（.env, .env.local、OS 環境変数優先）を実装。環境変数のパーシング、必須チェック用 _require、Settings クラスを提供。
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。
    - validate_config.py: 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加（--strict オプションあり）。PyYAML 未インストール時は YAML 検証をスキップして警告。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定、等金額配分、スコア配分を実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - portfolio/position_sizing.py: 地位サイズ算出ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケーリングを実装。
    - portfolio/__init__.py: 上記 API をエクスポート。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。コンソール（stdout）と日次ローテートファイル出力を設定。LOG_DIR / LOG_LEVEL の解決順を実装。
    - utils/process_priority.py: Windows/Linux の差分を吸収したプロセス優先度・CPU affinity 設定ユーティリティを追加。アクセス権限や未対応 OS は警告でスキップ。
  - モニタリング／レポート
    - monitoring 側 DB 初期化のための init_monitoring_db 呼び出し箇所を各起動スクリプトに追加（冪等）。
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 含む）などを集計し PASS/FAIL を判定するしきい値を定義。
  - リサーチ（骨組み）
    - research/factor_research.py: ファクター計算モジュールの枠組み（モメンタム、ボラティリティ、バリュー等）を追加。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。モメンタム計算関数 calc_momentum の実装を開始（スキャン範囲や定数を定義）。

Changed
- なし（初期リリースのため）

Fixed
- なし（初期リリースのため）

Notes / 実装上の注意
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。プロジェクトルートが特定できない場合は自動ロードをスキップします。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
- config.Setup と validate_config は .env ファイル・config/*.yaml に関する便利ツールですが、.env は機密情報を含むため Git 等へは絶対にコミットしないでください（config_setup のヘッダにも注意書きあり）。
- run_monitoring は MONITOR_POLL_INTERVAL が 0 以下や不正な値の場合にフォールバックしてデフォルト 60 秒を使用します。
- run_execution は paper_trading モード時に MockBroker を利用して data/paper_trading.db に記録する設計（実運用 DB と分離）。
- process_priority の設定は実行環境の権限に依存します。権限不足や未サポートの OS では警告を出して処理を継続します。
- portfolio/position_sizing のスケーリングや単元丸めロジックは保守的設計（cost_buffer 等）を取り入れています。lot_size は将来的に銘柄別対応の余地があります（TODO コメントあり）。
- research/factor_research.py はフレームワークが整備されていますが、一部実装が継続中です（calc_momentum 等の詳細実装に注意）。

セキュリティ
- 環境変数（API トークンやパスワード）は .env を通じて管理します。.env を Git に含めないことを強く推奨します。

参考
- パッケージバージョン: __version__ = "0.1.0" (src/kabusys/__init__.py)

---
今後の予定（例）
- research モジュールのファクター実装完了（Momentum の実装継続、Value/Volatility/Liquidity の実装）
- ExecutionEngine / BrokerClient のテストカバレッジ強化と paper/live 動作確認
- モニタリング・アラート（LINE 通知など）の追加強化