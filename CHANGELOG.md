# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このプロジェクトのバージョンは src/kabusys/__init__.py の __version__ に合わせて v0.1.0 としています（リリース日: 2026-04-19）。

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション構成と起動スクリプトを追加
  - 実行系エントリ:
    - run_execution: ExecutionEngine 起動用スクリプト。KABUSYS_ENV=paper_trading 時は専用の paper_trading SQLite を使用し、MockBroker を介してペーパートレードを行う（src/kabusys/run_execution.py）。
    - run_monitoring: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用（src/kabusys/run_monitoring.py）。
- 設定管理・ウィザード・検証ツールを追加
  - Settings クラス: 環境変数のラップ（必須チェック・デフォルト・型変換・検証ロジック）（src/kabusys/config.py）。
  - config_setup: .env の対話式ウィザード（作成/更新）を提供、シークレット入力のマスク、デフォルト表示など（src/kabusys/config_setup.py）。
  - validate_config: 起動前に環境変数や config/*.yaml の存在・基本妥当性を検証する CLI。--strict オプションで警告を失敗扱いにできる（src/kabusys/validate_config.py）。
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）検出に基づいて .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）（src/kabusys/config.py）。
  - .env パーサ: export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント対応など堅牢なパース機能を実装（src/kabusys/config.py）。
- ロギング・プロセス制御ユーティリティを追加
  - setup_logging: stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler、30日保持）を統一して設定。ログディレクトリの自動作成失敗時はファイル出力をスキップするフォールバックを実装（src/kabusys/utils/logging_setup.py）。
  - process_priority: Windows/Linux/macOS に対応したプロセス優先度設定（高/通常/低）と CPU affinity 設定ユーティリティ。権限不足や未対応 OS は安全にスキップ（src/kabusys/utils/process_priority.py）。
- ポートフォリオ構築（純関数群）
  - portfolio_builder: 候補選定（スコア降順、タイブレーク）、等金額配分、スコア重み配分（スコア全0 のとき等配分へフォールバック）（src/kabusys/portfolio/portfolio_builder.py）。
  - risk_adjustment: セクター集中上限適用（当日売却予定の銘柄を除外可）、市場レジームに応じた投下資金乗数の計算（bull/neutral/bear）（src/kabusys/portfolio/risk_adjustment.py）。
  - position_sizing: 発注株数計算（risk_based / equal / score）。単元株（lot_size）丸め、ポジション上限・集計上限（aggregate cap）に基づくスケールダウンや残余配分ロジック、コストバッファ考慮を実装（src/kabusys/portfolio/position_sizing.py）。
  - portfolio パッケージのエクスポート整理（src/kabusys/portfolio/__init__.py）。
- 分析 & 検証ツール
  - tools/paper_verification_report: ペーパートレード用 SQLite を読み、稼働率・注文成功率・送信率・レイテンシ（P95 など）を集計して PASS/FAIL 判定する CLI。期間指定(--from/--to) と DB 指定(--db) に対応（src/kabusys/tools/paper_verification_report.py）。
- 研究用ファクター計算モジュール（着手）
  - research/factor_research: DuckDB 接続を用いたファクター計算の枠組み（モメンタム・MA200 乖離・ATR などを想定）。設計方針と定数を定義（src/kabusys/research/factor_research.py）。※実装は継続中（ファイル末尾に未完の箇所あり）。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- なし

### Notes / Known issues / TODO
- position_sizing: 将来的には銘柄毎の lot_size を受け取る設計（現在は全銘柄共通の lot_size）。コメントに拡張 TODO を残しています（src/kabusys/portfolio/position_sizing.py）。
- risk_adjustment.apply_sector_cap: price が 0.0 の場合にエクスポージャーが過少評価される可能性があり、前日終値や取得原価でのフォールバックを検討する TODO が残っています（src/kabusys/portfolio/risk_adjustment.py）。
- factor_research モジュールは設計と定数の定義を含みますが、モメンタム計算関数の実装が途中で終了しているため実運用前に実装完了とテストが必要です（src/kabusys/research/factor_research.py）。
- run_monitoring は監視用 DB に常に settings.sqlite_path（本番パス）を使う設計です。開発環境で分離したい場合は設定を変更してください（src/kabusys/run_monitoring.py）。
- run_execution は paper_trading 用に DB を分離しますが、本番運用時は設定（KABUSYS_ENV など）と validate_config のチェックを忘れずに行ってください。

---

今後のリリースで予定している主な改善点:
- factor_research の完全実装とユニットテスト
- Strategy/Execution の統合テストと BrokerClient のモック整備
- 銘柄単位の lot_size サポート、手数料・スリッページのより正確なモデル化

変更内容に不明点や追記希望があれば教えてください。