CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に従っています。  
リリース日はコードベースのスナップショットから推測して記載しています。内容はソースコードの実装やコメントから推測した変更点／機能です。

Unreleased
----------

- 作業中 / 次回リリース候補
  - research/factor_research.py が途中（コメント末尾で切れている）であり、ファクター計算モジュールの追加・完成が予定されていることを示唆します。今後のリリースで完成・ドキュメント化される想定です。
  - position_sizing や risk_adjustment にいくつかの TODO コメント（価格フォールバック・lot_size 拡張など）があり、これらの改善・拡張が予定されています。

[0.1.0] - 2026-04-19
--------------------

Added
- 基本機能の初期実装（初回公開相当）
  - 実行・監視プロセス起動スクリプトを追加
    - run_execution.py: ExecutionEngine を起動するデーモンライクなスクリプトを実装。Paper Trading 時は専用の SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を利用する旨を明記。
  - 設定・環境管理
    - config.py: .env 自動読み込み機構を追加（プロジェクトルート検出: .git または pyproject.toml）。.env/.env.local の取り扱い（優先度、保護された OS 環境変数）や値パース（クォート・エスケープ・export プレフィックス・インラインコメント処理）を実装。
    - Settings クラスを導入し、各種設定値（J-Quants、kabu API、DB パス、PID/KILL フラグ、監視閾値、環境判定メソッド等）をプロパティとして提供。PAPER_FILL_MODE のバリデーション実装。
  - 設定系 CLI ツール
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新するツールを追加（シークレット扱い項目や選択肢対応、既存 .env の読み込み・マスク表示、保存の確認）。
    - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パス・config/*.yaml の存在確認、PyYAML があれば YAML のパース検証）。--strict オプションで警告を FAIL 扱いにできる。
  - 運用支援ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツールを追加。期間指定オプション（--from / --to / --db）に対応し、稼働率・注文成功率・送信率・P95 レイテンシ等を算出して PASS/FAIL 判定する。P95 計算、欠損テーブルの安全ハンドリングを実装。
  - ポートフォリオ構築ライブラリ (純関数群)
    - portfolio/portfolio_builder.py: シグナル選定（スコア降順、signal_rank によるタイブレーク）、等配分・スコア重み計算を実装。全スコアが 0 の場合は等配分にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、レジーム未定義時のフォールバックを明記。
    - portfolio/position_sizing.py: position size 計算（risk_based / equal / score）を実装。lot_size 単位で丸め、per-position 上限・aggregate cap（available_cash 超過時にスケールダウン）・cost_buffer を考慮。残差処理で lot 単位で追加配分するロジックを実装。
    - portfolio/__init__.py で上記 API をエクスポート。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを実装。stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを実装。
    - utils/process_priority.py: psutil を使ったプロセス優先度設定と CPU affinity 設定を実装。Windows（HIGH_PRIORITY_CLASS 等）と POSIX の nice 値を吸収する跨プラットフォーム実装。アクセス権限不足時の警告ハンドリングを追加。
  - モニタリング DB 初期化ユーティリティ呼び出し（init_monitoring_db を run スクリプトから呼ぶことで監視テーブル存在を保証）。
  - Execution 側におけるコンポーネント構築例
    - BrokerClientFactory、OrderRepository、OrderManager、RiskManager（デフォルト設定値を含む RiskConfig）、Reconciler、ExecutionEngine の組立てを run_execution で行い、スレッドで実行・停止フラグ対応を実装。起動時に停止フラグが既に立っている場合は起動を抑止。

Changed
- ログ出力の統一
  - すべての起動スクリプト・モジュールで setup_logging を呼び出して統一的にログを管理する設計に変更（StreamHandler を stdout に向けるポリシーの明示含む）。
- .env の自動読み込みポリシーを明確化
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で抑止可能。読み込み優先度: OS 環境変数 > .env.local > .env。プロジェクトルートが特定できない場合はスキップ。

Fixed
- 環境変数パースの堅牢化
  - config._parse_env_line がクォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの取り扱いなどを考慮してより正確に値を抽出するようになった。
- 実行中の安全なシャットダウン処理
  - run_monitoring と run_execution で stop フラグ（data/stop_requested.flag）を監視し、検出時に安全にループを抜ける・エンジン停止処理を呼ぶようになった。KeyboardInterrupt の捕捉により CTRL+C による終了時もリソースをクローズする。

Deprecated
- なし（初期リリース想定）

Removed
- なし（初期リリース想定）

Security
- 設定ウィザードおよび .env 書き込みではシークレット項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, LINE_TOKEN 等）をマスク表示する配慮を追加。

Notes / Known issues / TODO
- research/factor_research.py が途中で切れている（ファクター計算ルーチンの未完）。次回リリースで完成予定。
- position_sizing.calc_position_sizes の価格欠損時のフォールバック（前日終値や取得原価など）は TODO として残っているため、価格データ欠損があると想定より厳格にスキップされる可能性あり。
- risk_adjustment.apply_sector_cap は "unknown" セクターを上限チェック対象外にしているが、データ欠損の影響でセクター露出が過小評価される可能性があり将来的改善が検討されている。
- run_monitoring は monitoring の DB に常に本番 sqlite_path を使う設計（意図的）。開発時の扱いに注意。

参照
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" を初期リリースとして採用しています。