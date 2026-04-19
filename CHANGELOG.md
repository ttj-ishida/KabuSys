CHANGELOG
=========

すべての日付はリリース日を示します。  
この変更履歴はソースコードの内容から推測して作成しています。

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

Unreleased
----------

- ドキュメントや小さな改善、未完の研究モジュール補完などの作業が進行中です。
- research/factor_research.py の一部が未完（ファイル末尾で切れている）ため、追加実装やテストが必要です。
- その他、ログ出力やエラーハンドリング、環境変数の取り扱いに関する小幅改善を予定。

[0.1.0] - 2026-04-19
--------------------

Added
- 基本的な自動売買フレームワークを初期実装。
  - エントリポイント / 起動スクリプト:
    - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用（Mock）DB を使用して本番 DB から分離する振る舞いを実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可能。
  - 設定・環境管理:
    - config.py: 環境変数読み込み・ラップを実装。プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を提供。複数の便利プロパティを追加（duckdb/sqlite パス、paper_trading 用 DB パス、各種閾値、環境判定など）。
    - config_setup.py: .env を対話式に生成/更新するウィザードを実装。
    - validate_config.py: .env と config/*.yaml の事前検証用 CLI を実装。--strict モードで警告を FAIL 扱いにできる。
  - 監視・ペーパートレード解析:
    - monitoring 側初期化用ユーティリティ（init_monitoring_db 呼び出し）を各スクリプトに統合。
    - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計し PASS/FAIL 判定を出力。
  - ポートフォリオ構築関連（純粋関数群、DB 参照なし）:
    - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights、スコアが全て 0 の場合は等分配にフォールバック）を実装。
    - portfolio/risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知のレジームでは 1.0 にフォールバックし警告を出力。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score の各方式）、単元株丸め、ポートフォリオ全体の aggregate cap によるスケーリング、コストバッファ考慮などを実装。
  - ユーティリティ:
    - utils/logging_setup.py: 統一的ログ設定ユーティリティを実装。stdout 出力用 StreamHandler と 日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーへ設定。ログディレクトリ作成失敗時はファイル出力をスキップして継続。
    - utils/process_priority.py: psutil を用いたプラットフォーム非依存のプロセス優先度設定（Windows / POSIX）と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS の場合は警告を出してスキップ。

Changed
- ログの標準出力先を stdout に統一（cron/スケジューラでの扱いやすさ向上）。
- run_monitoring/run_execution の起動時にプロセス優先度を "high" に設定してから主要初期化を行うようにし、起動時の安定性を優先。

Fixed
- .env パーサーの堅牢化（config._parse_env_line）:
  - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理などに対応し実運用での互換性を向上。
- .env の自動読み込みで OS 環境変数（既存の値）を保護できる仕組みを導入（protected set）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションも提供。
- validate_config による起動前チェックを実装し、必須環境変数未設定や config/*.yaml の欠損・パースエラー等を事前検出可能にした。

Security
- 機密値（J-Quants トークン、kabu API パスワード、LINE トークン）は .env ウィザードでシークレット扱いにし、表示時にマスクする機能を導入。
- .env を絶対に Git にコミットしないことを README/ヘッダコメントで明示（config_setup の書き込みテンプレートに記載）。

Known Issues
- research/factor_research.py が途中で切れており、モメンタム計算の一部が未完です。ニューラルや因子集約の追加実装が必要です。
- position_sizing の価格欠損時の挙動に関する TODO コメントあり（価格が欠損するとエクスポージャーが過少見積りになる可能性）。前日終値や取得原価でのフォールバックが未実装。
- 一部の外部依存（psutil、duckdb、PyYAML）が環境にない場合に処理をスキップする設計だが、インストールガイドでの依存明記が必要。

Notes
- 本バージョンは初期リリース相当の機能群を含むため、運用前に validate_config、config_setup による設定チェック、paper_trading DB を用いた動作確認を推奨します。
- 将来的な 0.2.0 以降では、research モジュールの完成、単体テスト整備、銘柄別単元対応、より詳細な運用監視・アラート（LINE 通知統合）などを予定。