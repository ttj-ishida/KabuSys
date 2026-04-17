# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、慣例に従ってカテゴリ別に整理しています。以下の内容は提示されたソースコードから推測して作成した変更履歴です。

## [0.1.0] - 2026-04-17

### Added
- 基本リリースとして以下の主要機能を追加：
  - 実行スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検出による安全終了、起動時にプロセス優先度を High に設定。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時に専用のペーパートレードDBを使用する分離設計、BrokerClientFactory 経由のブローカー切替、スレッドでのエンジン実行と停止フラグ検出による安全停止、PID ファイル管理。
  - 設定管理
    - config.py: .env 自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を基準）、高度な .env パーサ（export, 引用符、インラインコメント対応）、環境変数アクセス用 Settings クラス（型チェック・デフォルト値・バリデーション）。
    - config_setup.py: 対話式ウィザードで .env を作成/更新する CLI を追加。秘密値のマスク表示、既存値の読み込み、書き込みテンプレートを提供。
    - validate_config.py: 起動前検証用 CLI を追加。必須環境変数、KABUSYS_ENV、DB パス、config/*.yaml の存在と YAML パース検証（PyYAML が無ければ警告）などをチェック。--strict による警告を失敗扱いのオプションを追加。
  - ポートフォリオ構築ライブラリ（純関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等金額配分、スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）。
    - portfolio/risk_adjustment.py: セクター上限適用（既存保有を考慮して当日売却予定銘柄を除外）、市場レジームに基づく乗数計算（bull/neutral/bear のマッピング）。
    - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score 対応）、単元株丸め（lot_size）、1銘柄上限・集計キャップ・スケーリングロジック、cost_buffer による保守的コスト見積り、残差分の lot 単位での再配分。
  - 研究用モジュール
    - research/factor_research.py: DuckDB を用いたファクター計算（モメンタム、MA200乖離、ATR, 流動性等）を追加。営業日窓・欠損データ処理を考慮した実装。
  - ユーティリティ
    - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。失敗時は警告を出してフォールバックする。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を行う。閾値は定数で定義（稼働率 99% など）。
  - パッケージ情報
    - __init__.py にパッケージのバージョン（0.1.0）とエクスポート一覧を追加。

### Changed
- データベース設計（起動時の振る舞い）
  - 監視（monitoring）は KABUSYS_ENV にかかわらず本番 sqlite_path を使用し、監視テーブルの初期化を保証（init_monitoring_db の呼び出し）。
  - run_execution は paper_trading 環境向けに settings.paper_sqlite_path を使用して本番 DB と完全分離するように実装。
- .env 自動読み込みの優先順位を明確化：OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Settings クラスで各種閾値やパス・フラグの取得処理を追加し、値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を実施。
- position_sizing のスケールダウン処理において、lot 単位での丸めおよび残余キャッシュでの追加配分ロジックを導入（再現性を保つため安定ソートを採用）。

### Fixed
- .env パーサの改善：export プレフィックス、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメントの取り扱いを正しく処理するよう修正。これにより複雑な値の取り込みが安定化。
- process_priority/set_cpu_affinity において、未対応 OS や権限不足時に例外で落ちないよう例外ハンドリングを追加し、警告ログでフォールバックするように修正。
- run_monitoring での MONITOR_POLL_INTERVAL のパースを堅牢化（0 以下や非整数をデフォルトにフォールバックし、警告を出力）。

### Security
- .env の取り扱いに関する注意点を config_setup の出力テンプレートに明示（.env を Git にコミットしない旨の警告を追加）。

### Documentation / UX
- config_setup の対話ウィザードで秘密値をマスク表示する等、ユーザビリティ向上。
- validate_config の出力で INFO / WARNING / ERROR を整備し、--strict オプションで警告を失敗扱いにできるようにして起動前チェックを強化。
- paper_verification_report にて日付レンジ指定オプション（--from/--to）と DB パス指定（--db）をサポート。

### Notes / Implementation details
- 多くのモジュールは「副作用なしの純粋関数」設計（ポートフォリオ・ポジションサイズ等）を採用し、ユニットテストがしやすい構成にしている点を意識して実装。
- DuckDB を分析用データベースとして採用（duckdb_path を設定で指定）。prices_daily / raw_financials テーブルへの依存を想定。
- Execution 側の RiskManager 設定にデフォルト値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10, circuit_breaker_window_sec=60, max_drawdown=0.20）を導入し、初期化時に broker.get_available_cash() を初期ポートフォリオ値として使用。

## 既知の制約（注意事項）
- 一部の機能（YAML 設定ファイルの検証）は PyYAML に依存。未インストール時はスキップされ警告となる。
- position_sizing の価格フォールバック（価格欠損時の扱い）は TODO コメントあり — 価格欠損でエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値等のフォールバックを追加予定。
- process_priority / cpu_affinity の設定は環境（権限・OS）に依存し、失敗時はログで通知するのみ。

---

もし特定の変更点（コミット単位・作者情報・リリース日）や追加のバージョン化ポリシーが必要であれば、その情報をいただければ CHANGELOG をさらに詳細化します。