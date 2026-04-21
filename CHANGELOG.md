# CHANGELOG

すべての注目すべき変更を時系列で記録します。  
このファイルは Keep a Changelog の様式に従っています。  

※ 以下は提示されたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-21

### Added
- 基本機能の初期実装（KabuSys v0.1.0）
  - 自動売買システムのコアユーティリティ群を実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動・監視するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）と MockBrokerClient を使用する設計を考慮。
    - 実行中の停止フラグ（data/stop_requested.flag）検出による安全停止、実行 PID 管理（data/execution.pid）。
    - スレッドで Engine を起動し、停止フラグを監視して安全に終了。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト: 60 秒）。
    - 監視は環境に関わらず本番 sqlite_path を使用する旨の実装。
    - 停止フラグを検出してループ終了、KeyboardInterrupt のハンドリング。
- 設定管理
  - config.py:
    - .env 自動読み込み機能（プロジェクトルートを .git または pyproject.toml から発見）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env 行の堅牢なパーシング（export プレフィックス、クォート内エスケープ、インラインコメント処理等）。
    - Settings クラスでアプリ設定をプロパティとして提供（パス、閾値、env 判定、PAPER_FILL_MODE の検証など）。
- 設定ツール / 検証ツール
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を実装。
    - 秘匿項目は表示をマスク、既存 .env 読み込みと Enter による既存値再利用。
    - 保存前の確認プロンプト。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性検証、DB パス親ディレクトリ存在チェック。
    - PyYAML 未インストール時は YAML 検証をスキップして警告。
    - --strict モードで警告も失敗扱いにできる。
- ポートフォリオ構築モジュール（pure function）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選定、signal_rank によるタイブレーク。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合はフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限に基づく候補除外ロジック。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数算出、単元株丸め、per-stock 上限、aggregate cap によるスケールダウンと残余の分配。
    - cost_buffer（手数料・スリッページ見積り）を考慮した保守的計算。
- 分析・検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを実装（SQLite DB を参照）。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計。閾値に基づく PASS/FAIL 判定を出力。
- ログ・プロセスユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに対して StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を統一設定。
    - 既存ハンドラをクリアして二重登録を防止。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定（Windows と POSIX の差異を吸収）。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）を提供。アクセス権限等の失敗は警告でスキップ。

### Changed
- 起動時のプロセス優先度を全スクリプトで「high」に設定するよう統一（run_execution / run_monitoring が最初に set_process_priority("high") を呼び出す）。
- logging_setup において stdout を用いるよう明示（cron 等で stdout/stderr の取り扱いを容易にするため）。
- .env 読み込みの振る舞いを改善（.env.local が .env をオーバーライドする仕組み）。

### Fixed
- MONITOR_POLL_INTERVAL の不正値に対する耐性を追加（0/負の値や非整数入力は警告を出しデフォルト 60 秒にフォールバック）。
- logging_setup: ログディレクトリ作成失敗時にプロセスが落ちないようハンドリングを追加。ファイルハンドラ生成失敗は警告で落とさない。
- process_priority / set_cpu_affinity: 権限不足や未対応 OS での例外をキャッチし、警告で継続するように改良。

### Security
- config_setup と設定表示でシークレット値（J-Quants トークン、kabu API パスワード、LINE トークン）を保存時や一覧表示でマスク表示。
- .env の自動ロードはデフォルトで有効だが、KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で無効化可能（想定外の環境変数上書きを防止）。

### Notes / Known issues
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）がある場合にエクスポージャーが過少見積もられる問題を注記（TODO: 前日終値や取得原価でのフォールバックを検討）。
- position_sizing の将来的拡張に関する TODO:
  - lot_size を銘柄別に持たせるなどの拡張を想定。
- research/factor_research.py はファイル末尾が（提示ソースの切り取りによって）一部欠けているため、実装完了が必要。
- run_monitoring は監視用 DB（sqlite）を環境にかかわらず本番 sqlite_path を使用する設計になっている点は意図的（監視データの一元管理）が想定されるが、運用上の分離が必要な場合は設定で対応する必要あり。
- validate_config の YAML 検証は PyYAML に依存。未インストール環境では YAML パース検証はスキップされる。

---

（以上）README やリリースノートに転記しやすい形でまとめました。必要であればセクションの追加・修正（日付、リリース番号、より詳細な変更点の分割）を行います。