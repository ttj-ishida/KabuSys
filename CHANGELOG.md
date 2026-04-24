CHANGELOG
=========
すべての変更は Keep a Changelog 準拠の形式で記載しています。
タグ付けや日付はリポジトリの実際の履歴に合わせて調整してください。

バージョン一覧
--------------
- Unreleased
- [0.1.0] - 2026-04-24

[Unreleased]
------------
（現時点のスナップショットから推測される変更点は特にありません。将来の変更はここに記載してください）

[0.1.0] - 2026-04-24
-------------------
Added
- 初期リリース: KabuSys 自動売買フレームワークのベース実装を追加。
- 起動スクリプト:
  - run_execution.py: ExecutionEngine 起動ロジックを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用して本番 DB と分離。停止フラグ検知、スレッド実行、PID ファイル管理、プロセス優先度設定を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ実装を追加。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能。停止フラグ検知と例外ハンドリングを備える。
- 設定・環境管理:
  - config.py: .env 自動ロード機能を実装（.env, .env.local）。OS 環境変数の保護（上書き禁止）に対応。環境変数パーサ（クォート、export 形式、インラインコメント処理）を実装。Settings クラスで主要設定をプロパティとして提供（DB パス、paper_trading 用パス、閾値、KABUSYS_ENV 判定等）。
  - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。デフォルト値、選択肢、シークレット項目のマスク表示、保存確認を実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数チェック、パスの存在確認、YAML ファイルのパース確認（PyYAML の有無に応じてスキップ）、本番環境向けのガードチェック（LINE 通知設定、Kill Switch 設定等）。--strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ:
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。コンソール（stdout）出力と日次ローテーションのファイル出力を root ロガーに設定。ログディレクトリ作成失敗時はファイルハンドラをスキップしてフォールバックする。
  - utils/process_priority.py: プラットフォーム差分（Windows / POSIX）を吸収するプロセス優先度設定と CPU affinity 設定関数を追加。アクセス権限エラーなどは警告でスキップ。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）と等配分・スコア加重配分の計算を実装。スコア合計が 0 の場合のフォールバックを実装。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（risk_based / equal / score モード）。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer（手数料・スリッページ保守見積り）を考慮。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知レジームとスコア 0 の扱いについてのフォールバック動作を定義。
  - portfolio/__init__.py: 上記モジュールをパッケージとしてエクスポート。
- 監視・モニタリング:
  - run_monitoring.py と各モジュールの連携により、monitoring DB の初期化（init_monitoring_db）、SystemMonitor の check_once 呼び出しループを追加。MONITOR_POLL_INTERVAL の不正検出とフォールバック挙動を実装。
- Execution 周辺コンポーネント骨格（組み立て済み）:
  - BrokerClientFactory、ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の組み立て・起動フローを run_execution にて接続。RiskConfig にデフォルト値を与え、初期ポートフォリオ値を broker.get_available_cash() から取得する流れを導入。
- Paper Trading 向けツール:
  - tools/paper_verification_report.py: ペーパートレードの検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）を算出し、パス/フェイル判定を行う。日付フィルタ（--from / --to）と DB 指定オプションをサポート。
- 研究用モジュール（骨格）:
  - research/factor_research.py: DuckDB を使ったファクタ計算モジュールの骨格を追加（Momentum/Value/Volatility/Liquidity 設計方針、定数、calc_momentum の冒頭実装）。DuckDB 接続を受け取る設計。

Changed
- 設計上の注意点やデフォルト動作を明示:
  - .env 自動ロードはデフォルトで有効だが KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（monitoring.db）を使用するように明記。
  - run_execution は paper_trading 環境時に専用 DB（data/paper_trading.db）を使用して本番 DB と分離する設計。

Fixed
- ログ出力周りの堅牢性向上:
  - ログディレクトリ作成に失敗した場合にファイルハンドラ作成をスキップし、コンソール出力のみで継続するフォールバックを実装。
- process_priority 設定の例外処理強化:
  - プラットフォーム未対応や権限不足時に警告を出してスキップするように改善。

Notes / Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、現状ではエクスポージャーが過少見積もられる可能性あり。将来的に前日終値や取得原価等のフォールバック導入を検討中（TODO コメントあり）。
- portfolio/position_sizing:
  - lot_size は現状全銘柄共通のパラメータ。将来的には銘柄別 lot_map のサポートを検討（TODO コメントあり）。
- research/factor_research.py:
  - ファイルは計算方針と一部実装（calc_momentum の冒頭）を含むが、完全実装は未完（スナップショットが途中で切れているため、詳細実装は今後追加予定）。
- validate_config.py:
  - PyYAML 未インストール時は YAML の内容チェックをスキップする（警告を出す）。CI などでは PyYAML の有無を意識すること。
- その他:
  - 一部モジュールは外部実装（BrokerClientFactory、ExecutionEngine の内部実装等）に依存しているため、実運用前にそれらのユニットテストと実運用検証が必要。

作者注
- この CHANGELOG は与えられたコードスナップショットから推測して作成したもので、実際のコミット履歴や意図したリリースノートと差異がある可能性があります。必要に応じて日付・セクション・詳細をリポジトリの実際の履歴に合わせて調整してください。