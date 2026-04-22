# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
バージョン番号はパッケージの __version__（0.1.0）に基づきます。日付はソースコードのスナップショット作成日を使用しています。

## [Unreleased]

- 開発中のモジュール・未完成の関数についての注意を追加
  - research/factor_research.calc_momentum の実装が途中（ソースが途中で切れている）であり、完全実装は未完了。ドキュメント内に注記あり。
  - position_sizing や risk_adjustment 内に将来の拡張（銘柄単位の lot_size 管理、価格フォールバック等）を示す TODO コメントを追加。

---

## [0.1.0] - 2026-04-22

### Added
- 基本実装: 初期リリースとして以下の主要コンポーネントを追加
  - CLI / 起動スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、スレッドでのエンジン実行、停止フラグ監視、paper_trading 用の DB 分離を実装。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は常に本番 sqlite_path を使用する仕様。
  - 設定/環境管理
    - config.py: 環境変数と設定を扱う Settings クラスを追加。自動でプロジェクトルートの .env / .env.local を読み込む機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。各種閾値やパス、Paper Trading の設定を提供。
    - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。
    - validate_config.py: .env と config/*.yaml を検証する CLI を追加（--strict オプションあり）。PyYAML がない場合は YAML 検証をスキップして警告を出す。
  - ユーティリティ
    - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。stdout に StreamHandler を出力し、日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を追加。LOG_LEVEL / LOG_DIR の解決ロジックを提供。
    - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定、CPU affinity 設定を追加。Windows と POSIX(Linux/Mac/FreeBSD) を吸収する実装。アクセス拒否時は警告して継続。
  - データベース/分析
    - DuckDB と SQLite を利用する構成を追加（Settings でパス定義）。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定 select_candidates、等金額 calc_equal_weights、スコア加重 calc_score_weights を追加。
    - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap、レジームに応じた乗数 calc_regime_multiplier を追加。未知レジームはログ警告の上でフォールバック。
    - portfolio/position_sizing.py: position sizing の主要アルゴリズムを追加。risk_based / equal / score の配分方式、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積りを実装。
    - portfolio/__init__.py: 上記関数群をエクスポート。
  - 監視・ペーパートレード検証ツール
    - tools/paper_verification_report.py: ペーパートレード用の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を行う。閾値はソースで定義（例: 稼働率 >= 99% 等）。P95 計算、日付フィルタ (--from/--to/--db) をサポート。
  - パッケージメタ情報
    - __init__.py にバージョン __version__ = "0.1.0" を追加。

### Changed
- 設定読み込みの振る舞いを明文化
  - .env 自動読み込みの優先順と上書きポリシー（OS 環境変数を保護する protected 機構）を実装。
  - ログ設定の振る舞いを統一（stdout を使用、ファイル出力はログディレクトリ作成に成功した場合のみ有効）。
- 実行フロー安全性の改善
  - run_execution/run_monitoring の起動時にプロセス優先度を最初に設定するように変更（set_process_priority を実行）。
  - 停止フラグ（data/stop_requested.flag）や実行用 PID ファイルの扱いを統一。

### Fixed
- .env パーサーの堅牢化
  - config._parse_env_line: export プレフィックス、クォート文字列内のバックスラッシュエスケープ、インラインコメント処理（クォートの有無に応じた処理）などを扱うように強化。無効行のスキップ処理を明確化。
- ポジションサイズ算出の端数処理と aggregate スケーリング
  - position_sizing.calc_position_sizes: スケールダウン後の残余キャッシュでの再配分ロジック（fractional remainder による lot_size 単位の追加配分）を実装し、より再現性のある配分を確保。

### Security
- 環境変数の取り扱いにおいて .env を絶対にコミットしない旨を config_setup に明記（.env ファイルテンプレートに警告コメントを追加）。

### Documentation / Notes
- 多くのモジュール内に設計方針や参照ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）への言及を追加。実装意図や制約（例: DB を直接参照しない、純粋関数であること等）を明文化。
- validate_config.py による起動前検証を推奨（必須環境変数のチェック、KABUSYS_ENV の妥当性チェック、config/*.yaml の存在・パースチェック）。

---

## 既知の問題 / 未完事項
- research/factor_research.calc_momentum の実装が途中で終わっている（ファイルが途中で切れている）。ファクター計算ロジックの完全化が必要。
- position_sizing の将来的拡張（銘柄ごとの lot_size 管理、価格フォールバック）は TODO として残っている。
- run_monitoring の MONITOR_POLL_INTERVAL は環境変数の不正値を検出してデフォルトにフォールバックするが、より緻密な検証や監視統計の外部通知は今後の拡張予定。
- broker / execution 周り（BrokerClientFactory、ExecutionEngine、OrderManager 等）の詳細実装は本スナップショットに含まれているが、実働運用上のエッジケーステストが必要。

---

## 互換性 / Breaking Changes
- 初期リリースのため互換性の過去バージョンとの互換性問題はなし。

---

（補足）上記はソースコードの内容から推測して作成した変更履歴です。実際のコミット履歴やリリースノートを元にした正確な履歴は、Git の履歴やプロジェクトのリリース手順に基づいて更新してください。