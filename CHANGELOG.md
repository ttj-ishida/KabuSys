KEEP A CHANGELOG 準拠の CHANGELOG.md（日本語）

注意: 以下は提示されたコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴ではなく、機能追加・改善点・設計方針をまとめたものになります。

Unreleased
---------
- （今後のリリースに向けた項目をここに記載してください）

[0.1.0] - 2026-04-19
-------------------
Added
- 基本コア機能を実装し初期リリースを作成。
- 起動スクリプト:
  - run_execution.py: 実行エンジン起動スクリプトを追加。KABUSYS_ENV=paper_trading 時はペーパートレード用の MockBrokerClient を利用し、data/paper_trading.db に記録することで本番 DB と分離。
  - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止は data/stop_requested.flag の存在で判定。
- 設定管理:
  - config.py: .env 自動ロード（.env, .env.local）機能、環境変数パースロジック（クォート／エスケープ／コメント対応）、Settings クラスによる型付き設定アクセスを追加。環境切替（development / paper_trading / live）と多数の設定プロパティを提供。
  - config_setup.py: 対話式 .env 作成ウィザードを追加（項目の説明、既存 .env 読み込み、シークレットマスク表示、保存機能）。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数・KABUSYS_ENV 検証・ログレベルチェック・DB パス確認・config/*.yaml の存在/パースチェック・本番環境向けの注意喚起（LINE 通知設定や Kill Switch の挙動）を実施。--strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス管理ユーティリティ:
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。コンソール（stdout）と日次ローテーションファイル（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時のフォールバック処理あり。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収し、安全にフォールバック。権限不足など失敗時は警告でスキップ。
- ポートフォリオ構築ライブラリ（純粋関数）:
  - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を実装。スコア全ゼロ時のフォールバックとログ警告あり。
  - portfolio/risk_adjustment.py: セクター上限適用 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。未知レジーム時はフォールバック（1.0）して警告。
  - portfolio/position_sizing.py: 発注株数計算 calc_position_sizes を実装。allocation_method（risk_based / equal / score）に対応、単元株（lot_size）丸め、1 銘柄上限・aggregate cap（利用可能現金に対するスケーリング）、cost_buffer による保守的見積り、残余キャッシュの配分ロジックを実装。
  - portfolio/__init__.py で上記関数群を公開。
- リサーチ / ユーティリティ:
  - research/factor_research.py: ファクター計算モジュール骨格（Momentum / Value / Volatility / Liquidity）を追加。DuckDB 接続を受ける設計。モメンタム計算関数等の実装開始（未完の箇所あり）。
- 監視・検証ツール:
  - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を集計し PASS/FAIL を判定。閾値や P95 計算ロジックを実装。
- DB / 分析統合:
  - DuckDB との統合を想定（duckdb 接続の受け渡し）をコード内でサポート。monitoring 用 sqlite と分析用 duckdb を併用する設計。
- その他:
  - パッケージ初期化: __init__.py に __version__ = "0.1.0" を設定。
  - 実行/監視での PID/stop フラグ管理（pid_file, execution.pid, stop_requested.flag）を導入。

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Notes / 補足
- 設計上の注意:
  - 設定の自動ロードはプロジェクトルートを .git または pyproject.toml から探索して行うため、配布後の環境でも CWD に依存せず動作するよう配慮されています。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - run_monitoring は KABUSYS_ENV にかかわらず「監視 DB（sqlite_path）」を本番設定（デフォルト data/monitoring.db）で使用する挙動を持ちます。一方 run_execution は paper_trading 時に paper_sqlite_path を使用して DB を分離します。
  - process_priority / CPU affinity 設定は OS ごとに限定的な実装をしており、権限不足・未サポート環境では安全にスキップします。
  - 一部のモジュール（例: research/factor_research.py の一部）は計算ロジックが続く設計になっており、今後の実装（完成）が予定されることを示唆しています。

ライセンス、貢献方法、リリース手順などのメタ情報は別途ドキュメント（README 等）に記載することを推奨します。