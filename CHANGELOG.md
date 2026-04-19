CHANGELOG
=========

All notable changes to this project will be documented in this file.
このファイルは Keep a Changelog 準拠で記載されています。
リリース日はコミット時点の日付を推定して記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

追加 (Added)
- 全体
  - 初期公開リリース。パッケージバージョンは kabusys.__version__ = "0.1.0"。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の data/stop_requested.flag で検知。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、本番 DB と分離。
    - ブローカークライアントの生成は BrokerClientFactory 経由で切替可能（Mock と実ブローカーの切替想定）。
    - 実行はデーモンスレッドで行い、stop フラグでエンジン停止を行う。PID ファイル作成をサポート。
- 設定関連
  - config.py: Settings クラスによる環境変数中心の設定管理を追加。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により .env 自動読み込みを行う（無効化可能）。
    - .env/.env.local の読み込み順・保護（OS 環境変数の保護）を実現。
    - 各種設定プロパティ（DB パス、PID パス、監視閾値、env 判定、paper_trading 用設定など）を提供。
    - PAPER_FILL_MODE の入力検証を実装（valid 値チェック）。
- 設定支援 / 検証ツール
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 初期項目（KABUSYS_ENV、J-Quants / kabu API トークン、DB パス、LOG_LEVEL、Kill Switch など）をサポート。
    - 既存 .env の読み込み・Enter で既存/デフォルトを再利用、最終的に .env を書き出す。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数や KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がある場合）を行う。
    - --strict オプションで警告を FAIL 扱いにできる。
- ロギング / プロセス操作ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - ログレベル / ログディレクトリの解決順を明確化。ディレクトリ作成失敗時はファイル出力をスキップして継続。
  - utils/process_priority.py: プロセス優先度設定ユーティリティを追加。
    - Windows / POSIX の差分吸収（nice 値 / HIGH_PRIORITY_CLASS 等の扱い）。
    - set_process_priority(), set_cpu_affinity() を提供。アクセス拒否や未対応 OS は警告ログでスキップ。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・等配分/スコア加重重み計算を実装。
    - select_candidates(), calc_equal_weights(), calc_score_weights() を提供。スコア全0時のフォールバック挙動あり。
  - portfolio/risk_adjustment.py: セクターキャップ適用・レジーム乗数を実装。
    - apply_sector_cap(): 既存ポジションを考慮したセクター上限適用（"unknown" セクターは無視）。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に基づく乗数。未知レジームはフォールバックで 1.0。
  - portfolio/position_sizing.py: 株数計算（risk_based / equal / score）・単元丸め・集計キャップスケーリングを実装。
    - lot_size 単位で丸め、コストバッファを考慮したスケールダウンと端数配分ロジックを実装。
  - portfolio/__init__.py: 上記関数群をパッケージ公開。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - データベース（PAPER_TRADING_SQLITE_PATH）から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計してレポート出力。
    - 閾値を定義して PASS/FAIL 判定を行う（稼働率、成功率、送信率、P95 レイテンシ）。
    - 日付フィルタ（--from / --to）と --db オプションをサポート。
- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨組みを追加。
    - Momentum / Value / Volatility / Liquidity の算出方針、DuckDB を用いた計算設計方針を記載。モメンタム計算関数の実装が開始。

変更 (Changed)
- run_monitoring.py / run_execution.py
  - 起動時に set_process_priority("high") を呼んで優先度を上げるようにした（重要処理優先のため）。
- config.py
  - .env 読み込みの挙動を OS 環境変数保護を考慮して実装（.env.local は override=True で上書き可だが OS env は保護）。
- logging_setup.py
  - 標準出力は stdout を使用する仕様に統一（cron / Task Scheduler からの取り扱いを想定）。

修正 (Fixed)
- config._parse_env_line の実装
  - シングル/ダブルクォート内のバックスラッシュエスケープやインラインコメントの扱いを考慮して .env のパースを堅牢化。
- run_monitoring._get_poll_interval
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）の場合にデフォルトへフォールバックし、警告ログを出すようにした。

注意 / 既知の制限 (Known issues)
- research/factor_research.py の calc_momentum などファクター計算の実装が途中で終わっている箇所がある（モジュールは骨組みと定数を用意済み）。実運用前に完全実装と検証が必要。
- position_sizing.calc_position_sizes の価格欠損時の挙動に TODO コメントあり（price が 0.0 の場合のフォールバック価格を将来的に検討）。
- .env ファイルは機密情報を含むため、生成された .env を Git にコミットしないよう注意喚起を表示する実装になっている（config_setup.py の出力に明記）。

セキュリティ (Security)
- 機密情報（API トークン等）は .env に保持することを前提としているため、リポジトリへコミットしないよう注意喚起を追加。

注記
- 本 CHANGELOG は提供されたコードを基に推測して作成しています。実際のコミット履歴・リリースノートがある場合はそれに従って調整してください。