Keep a Changelog に準拠した CHANGELOG.md を日本語で作成しました。コードの内容から推測して記載しています。必要に応じて日付や細部を調整してください。

----------------------------------------
Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/
----------------------------------------

Unreleased
---------


[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース: 基本的な自動売買フレームワークを追加。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV による paper_trading 切替（paper_trading 時は専用 SQLite を使用）やスレッドでの engine.run_session 実行、停止フラグ／PID ファイル処理を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能、停止フラグ検知で優雅に終了。
- 設定管理
  - config.py: Settings クラスを追加。環境変数の取得、値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）、自動 .env 読み込み（.env, .env.local、OS 環境優先）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - config_setup.py: 対話式 .env ウィザードを追加（.env の生成・更新）。秘密項目のマスク表示、保存前の確認、.env のテンプレートでの書き出しをサポート。
  - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、DB パスや config/*.yaml の存在確認、KABUSYS_ENV=live のガード（LINE 通知設定や Kill Switch の扱い）を実施。--strict オプションで警告をエラー扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログセットアップ関数を提供。StreamHandler を stdout に出力し、TimedRotatingFileHandler（日次ローテーション／30日保持）をファイル出力に追加。LOG_DIR / LOG_LEVEL の解決ロジックと既存ハンドラのクリア処理を実装。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを追加。psutil を使い権限不足等を安全にハンドリング。
- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等重み・スコア重み算出（calc_equal_weights, calc_score_weights）を追加。スコア全て 0 の場合のフォールバック警告あり。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターの扱いやフォールバック挙動を明示。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）を実装。allocation_method（risk_based / equal / score）に対応、単元株（lot_size）で丸め、aggregate cap（available_cash）超過時のスケーリングおよび残差分の配分ロジックを実装。cost_buffer による保守的見積りもサポート。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（P95 等）などの指標を集計し PASS/FAIL 判定を出力。P95 計算や期間フィルタ（--from / --to / --db）をサポート。
- 研究モジュール（初期）
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加（モメンタム、MA200 乖離、ATR、流動性等を想定）。DuckDB 接続を想定した設計。calc_momentum などの関数を配置（将来的な実装継続を前提）。

Changed
- 設計上の決定
  - 監視（monitoring）は KABUSYS_ENV に関わらず production 想定の sqlite_path を使用する、という意図がコードに反映（run_monitoring.py）。
  - run_execution.py は paper_trading 用 DB を本番 DB から物理的に分離（settings.paper_sqlite_path）することで paper/live の混同を防止。
  - ログのコンソール出力は標準エラーではなく標準出力（stdout）を使用するポリシーに統一（cron / タスクスケジューラでの扱いを考慮）。

Fixed
- 環境変数・ファイル処理での堅牢化
  - MONITOR_POLL_INTERVAL のパースで不正な値（非数値・0以下）を検出した場合は警告ログを出してデフォルト（60秒）にフォールバック（run_monitoring.py）。
  - .env パーサ（config.py）でシングル／ダブルクォートとバックスラッシュエスケープ、export プレフィックス、インラインコメントの扱いを強化。空行やコメント行を無視。
  - validate_config.py は PyYAML が未インストールでも動作し、YAML 検証をスキップして警告出力するように安全化。
  - utils/logging_setup.py: ログディレクトリ作成失敗時にファイルハンドラをスキップし、標準出力のみで継続するフォールバックを実装。

Security
- .env の取り扱いに関する注意書きを config_setup.py に追加（.env を Git にコミットしないよう明示）。

Notes / Known issues / TODO
- research/factor_research.py の実装が途中（スニペット末尾で calc_momentum の実装が途切れている）。ファクター計算の完全実装は継続予定。
- position_sizing.calc_position_sizes の一部（価格欠損時のフォールバック等）は TODO コメントで改善方針が残っている（前日終値などのフォールバックを検討）。
- apply_sector_cap は "unknown" セクターを現在は上限適用対象外としているが、将来的なポリシー見直しが必要な場合がある。
- process_priority / set_cpu_affinity は権限不足や非対応 OS での例外をログに落としてスキップする設計。実行環境での動作確認を推奨。

----------------------------------------
リリース注記はコードから推測したものです。追加したい変更点（実際のコミット履歴やリリース日、細かな修正履歴等）があれば追記します。