# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルでは主要な機能追加・変更点・既知の問題を日本語でまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- なし

## [0.1.0] - 2026-04-23

初回公開リリース。KabuSys のコア機能群を実装しました。主な内容は以下の通りです。

### Added（追加）

- アプリケーション設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
  - .env 自動ロード機構を実装（プロジェクトルートを自動検出し .env / .env.local を読み込む）。
  - 環境変数パーサは `export KEY=val` 形式、クォート付き値、インラインコメントの考慮などに対応。

- 設定ツール / 検証
  - 対話式 .env 設定ウィザードを追加（src/kabusys/config_setup.py）。
    - シークレット値のマスキング、デフォルト値、選択肢サポート、保存機能を提供。
    - 保存時に .env を安全なフォーマットで出力（Git にコミットしないよう注意書き含む）。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスや config/*.yaml の存在チェック。
    - --strict オプションで警告を失敗扱いにできる。

- 実行 / 監視エントリポイント
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は専用 paper DB（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を通じて本物／Mock ブローカを切替え可能。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag による安全な停止をサポート。
    - 起動時にプロセス優先度を "high" に設定する処理を組み込む。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番の sqlite_path を参照して監視 DB を初期化する設計。
    - stop フラグ検出でループ終了、KeyboardInterrupt での終了処理、例外時のログ出力を実装。

- ロギング / プロセス設定ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log）を設定。
    - LOG_LEVEL / LOG_DIR の優先解決、既存ハンドラのクリアを行う。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux, macOS, FreeBSD）を吸収する実装。
    - psutil を使用して nice 値・priority を設定し失敗時は警告でスキップ。
    - set_cpu_affinity() によるコア固定機能を提供。

- ポートフォリオ構築ロジック（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates(): スコア順に上位 N を選択。
    - calc_equal_weights(), calc_score_weights(): 等金額 / スコア加重の重み計算（スコア全0なら等分にフォールバック）。
  - セクター上限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap(): 既存ポジションのセクター比率に基づき新規候補を除外。
    - calc_regime_multiplier(): market regime に応じた乗数（bull/neutral/bear のデフォルトを提供、未知レジームは警告とともに 1.0 を返す）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes(): allocation_method ("risk_based", "equal", "score") に対応した株数計算。
    - 単元株丸め（lot_size 単位）、max_position_pct、max_utilization、aggregate cap のスケーリング、cost_buffer による保守的見積りを実装。
    - 利用可能現金に対するスケーリングロジックと残差の分配アルゴリズムを含む。

- Paper Trading 検証ツール
  - paper_verification_report: ペーパートレード用の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）などを集計。
    - P95 計算、閾値による PASS/FAIL 判定（稼働率 99% などのデフォルト閾値を設定）。
    - コマンドライン引数 --from / --to / --db をサポート。

- 研究モジュール（着手）
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - Momentum / MA200 / ATR などの方針と定数を定義。DuckDB を利用して prices_daily / raw_financials を参照する設計。
    - （実装は一部未完。ファイル末尾が切れているため続き実装が必要。）

- パッケージ初期化
  - パッケージバージョンを定義（src/kabusys/__init__.py: __version__ = "0.1.0"）。

### Changed（変更）

- なし（初回リリースのため該当なし）

### Fixed（修正）

- なし（初回リリースのため該当なし）

### Removed（削除）

- なし

### Security（セキュリティ）

- .env の取り扱いに関する注意書きを config_setup が出力（.env を Git 管理しないことを明記）。

### Notes / 既知の問題・ TODO

- research/factor_research.py が途中で切れており実装継続が必要（ファイル末尾に不完了のコード片あり）。
- portfolio/risk_adjustment.apply_sector_cap():
  - price が欠損（0.0）の場合、エクスポージャーを過少見積もる可能性がある旨の TODO コメントが存在。将来的に前日終値等でフォールバックすることが望まれる。
- position_sizing の将来的拡張:
  - 現在 lot_size は全銘柄共通。将来的には銘柄別 lot_map の導入を検討。
- run_monitoring は監視 DB として settings.sqlite_path（本番パス）を常に使う設計になっている点に注意。必要に応じて分離を検討すること。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム依存で失敗する場合があるが、失敗時はログ警告で安全にスキップするよう実装済み。

---

以上が 0.1.0 の主要な追加・仕様・既知課題のまとめです。今後のリリースでは research モジュールの完成、テスト追加、ドキュメント充実、パフォーマンス改善や運用向けの設定拡張を予定しています。