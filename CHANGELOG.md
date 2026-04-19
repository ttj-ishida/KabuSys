CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

追加予定 / 今後の改善（ソースコード内の TODO / コメントから推測）
- position_sizing:
  - 銘柄ごとの単元（lot_size）を将来的に銘柄マスタから読み込む拡張を予定。
- risk_adjustment:
  - price が欠損（0.0）の場合のフォールバック（前日終値や取得原価など）を検討中。
- utils:
  - process priority / cpu affinity のさらなるテストとプラットフォーム対応の強化。
- research.factor_research:
  - 実装途中のモジュールが存在（モメンタム等の計算ロジックの完成化が必要）。

[0.1.0] - 2026-04-11
--------------------

追加 (Added)
- 実行 / 監視スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し MockBrokerClient 経由で分離されたペーパートレード実行が可能。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグファイルによる安全停止に対応。

- 設定管理・CLI を追加
  - config.py: 環境変数 / .env の自動読み込み機能を実装。Settings クラスで各種設定（DB パス、API トークン、監視閾値等）をプロパティとして提供。PAPER_FILL_MODE のバリデーション等を実装。
  - config_setup.py: 対話式の .env 作成ウィザードを追加（既存 .env の読み取り・更新対応）。
  - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数や config/*.yaml の存在・パースチェック、KABUSYS_ENV の安全性チェック等を行い --strict モードをサポート。

- モニタリング・DB 初期化
  - monitoring.monitoring_db の初期化呼び出しを追加し、監視テーブルが存在することを保証（冪等に実行）。

- ポートフォリオ構築関連（純粋関数群）を追加
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等分配 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。スコアが全て0の際のフォールバック動作を定義。
  - portfolio.risk_adjustment: セクター集中制限を行う apply_sector_cap と市場レジームに応じた乗数 calc_regime_multiplier を実装。
  - portfolio.position_sizing: allocation method（risk_based / equal / score）に応じた株数算出ロジックを実装。単元丸め（lot_size）・max_position_pct・max_utilization・aggregate cap（利用可能現金に合わせたスケールダウン）・cost_buffer を考慮。

- ユーティリティを充実
  - utils/logging_setup.py: 統一的なログ初期化を提供。コンソール出力（stdout）と TimedRotatingFileHandler（日次、30日保持）をルートロガーに設定。LOG_DIR 作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: psutil を用いたプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows / POSIX の差分を吸収する API を提供。権限不足時は警告を出してスキップ。
  - utils.__init__.py を追加。

- Paper Trading 向け検証ツールを追加
  - tools/paper_verification_report.py: ペーパートレード DB から稼働率、注文成功率、送信率、P95 レイテンシ等を集計し PASS/FAIL を判定してレポート出力する CLI を実装。期間フィルタ (--from / --to) と DB 指定オプションをサポート。

- 研究用モジュール（骨格）を追加
  - research/factor_research.py: DuckDB を用いて価格テーブルからモメンタム等のファクターを計算するための骨格を実装（モメンタム期間定数や P95 等のユーティリティを含む）。（一部実装が継続中）

- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

変更 (Changed)
- DB 分離の挙動
  - run_execution は KABUSYS_ENV によって paper_trading 用の専用 SQLite(DB) を使用するように分離（settings.paper_sqlite_path）。一方、run_monitoring は環境にかかわらず本番用 sqlite_path を使用する旨を明示（監視データは本番 DB に記録する運用前提）。

修正 (Fixed)
- .env パーサの強化
  - config._parse_env_line において、export プレフィックスのサポート、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどを実装し、より堅牢にパースするようにした。

- validate_config の堅牢化
  - YAML パーサが存在しない場合は警告を出しパースチェックをスキップする安全策を導入。

既知の問題・注意点 (Notes)
- run_monitoring は説明文に「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」とあるため、監視データが paper_trading と本番で混ざらないよう運用上の注意が必要。
- KILL_FLAG_CLEAR_ON_START を本番で 1 に設定すると危険である旨を validate_config で警告する（デフォルトは 0 推奨）。
- PAPER_FILL_MODE の値は限定された有効値のみ受け入れる（instant / partial / never / reject）。不正値は ValueError を投げる。
- ログディレクトリの作成やプロセス優先度設定は権限やプラットフォームによって失敗する可能性があり、その場合は警告を出してスキップするデグレード挙動を取る。
- position_sizing の価格欠損時の取り扱いや銘柄別単元対応は将来的な改善対象。

ライセンス等
- 本 CHANGELOG はソースコード内のドキュメント・コメント・実装から推測して作成したものです。リリース日や項目の細部は実際のリリース履歴と異なる可能性があります。必要であればリリース実行者が日付・範囲を確定のうえ更新してください。