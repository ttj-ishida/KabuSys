CHANGELOG
=========

すべての重要な変更点はここに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

変更履歴はコードベースの内容から推測して作成しています。

[0.1.0] - 2026-04-20
-------------------

Added
- 基本アプリケーション構成を追加（初期リリース）
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 環境設定管理
  - .env の自動読み込み機能を実装（プロジェクトルートの .env / .env.local を優先的に読み込む）。(src/kabusys/config.py)
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントを考慮して安全に読み込むよう実装。
  - Settings クラスを追加し、環境変数への安全なアクセスと型変換（Path, float, bool 等）を提供。必須値取得時に未設定なら例外を投げる _require() を実装。 (src/kabusys/config.py)
  - 環境（KABUSYS_ENV）、ログレベル、データベースパス、Paper Trading 用 DB パス、監視閾値などの設定プロパティを提供。
  - PAPER_FILL_MODE の検証（有効値チェック）を実装。
- 環境設定ウィザード CLI を追加
  - src/kabusys/config_setup.py: 対話式ウィザードで .env を初期作成/更新する機能。秘密値のマスク表示、選択肢、デフォルト値、保存確認などを実装。
- 設定検証 CLI を追加
  - src/kabusys/validate_config.py: .env と config/*.yaml の検証ツールを提供。必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリチェック、YAML パースチェック（PyYAML がない場合は警告）、本番用ガードなど。--strict オプションで警告を FAIL として扱える。
- 起動スクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py を追加。プロセス優先度設定、DB 接続、BrokerClientFactory によるブローカクライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てと実行ループ、停止フラグによる安全停止、Paper Trading の場合は paper_trading.db を使用して本番 DB と分離する挙動を実装。
  - 監視ポーリング起動スクリプト: src/kabusys/run_monitoring.py を追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（不正値は警告してデフォルト 60 秒へフォールバック）、Monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
- ロギング基盤
  - src/kabusys/utils/logging_setup.py: ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler (日次ローテーション、30日保持) を設定するユーティリティを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する。ログレベル・保存先の優先解決順を実装。
- プロセス制御ユーティリティ
  - src/kabusys/utils/process_priority.py: Windows / POSIX の差分を吸収するプロセス優先度設定と CPU affinity 固定機能を追加。権限エラーや未対応 OS では警告を出して安全にフォールバックする。
- ポートフォリオ構築モジュール
  - 選定・重み付け:
    - src/kabusys/portfolio/portfolio_builder.py: select_candidates（スコア降順、同点は signal_rank でタイブレーク）、calc_equal_weights、calc_score_weights（スコア総和が 0 の場合は等配分にフォールバックし警告）を実装。
  - セクター制限・レジーム乗数:
    - src/kabusys/portfolio/risk_adjustment.py: apply_sector_cap（既存保有のセクター別時価を計算して上限を超えるセクターの新規候補を除外。'unknown' セクターは制限を適用しない）、calc_regime_multiplier（"bull"/"neutral"/"bear" に対する乗数）を実装。未知のレジームは警告の上で 1.0 へフォールバック。
  - 株数決定・リスク制限:
    - src/kabusys/portfolio/position_sizing.py: allocation_method に応じた株数計算を実装（"risk_based" / "equal" / "score"）。単元株（lot_size）で丸め、portfolio/value ベースの per-position 上限や aggregate cap によるスケールダウン（残差を評価して lot 単位で追加配分）を実装。価格欠損時のスキップやログ出力、cost_buffer の考慮などを含む。
  - モジュールエクスポートを提供（src/kabusys/portfolio/__init__.py）。
- リサーチ / ファクター計算（着手）
  - src/kabusys/research/factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールの骨組みを追加。DuckDB 接続を受け prices_daily / raw_financials テーブルを参照して計算する設計。モメンタム計算の定数と calc_momentum のインターフェイスが定義された（実装の一部あり）。
- Paper Trading 検証レポートツール
  - src/kabusys/tools/paper_verification_report.py: paper_trading.db を対象に稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計してレポートを出力する CLI を実装。閾値 (稼働率 99%, fill 90%, send 95%, P95 200ms) に基づく Pass/Fail 判定を行う。日付フィルタ (--from/--to) と DB パス指定 (--db) をサポート。
- その他ユーティリティ
  - SQLite / DuckDB の接続初期化に関連する監視 DB 初期化関数呼び出し（init_monitoring_db 呼び出し）が起動スクリプトに統合されている（存在しなければ作成）。

Changed
- ログ出力先の標準ストリームとして stdout を採用（stderr ではなく）。これにより cron / Task Scheduler 等で stdout/stderr を一本化して扱いやすくする意図を明記。 (src/kabusys/utils/logging_setup.py)
- 環境変数読み込みの優先順位を明確化: OS 環境 > .env.local > .env。OS 環境変数は protected として上書きされない。 (src/kabusys/config.py)

Fixed
- MONITOR_POLL_INTERVAL の不正値（0 や文字列など）に対して警告を出しデフォルトにフォールバックするように修正。これにより time.sleep への不正値渡しでの例外を回避。 (src/kabusys/run_monitoring.py)
- calc_score_weights: 全銘柄スコアが 0 の場合に正しく等金額配分へフォールバックし警告を出すように修正。 (src/kabusys/portfolio/portfolio_builder.py)
- process_priority / set_cpu_affinity: 未対応プラットフォームや権限エラーを安全に扱うようにし、例外で停止しないように改善。 (src/kabusys/utils/process_priority.py)

Security
- .env を絶対に Git にコミットしない旨の注意を config_setup の書き出しテンプレートに明記。 (src/kabusys/config_setup.py)

Notes / Implementation details
- run_execution の挙動:
  - KABUSYS_ENV=paper_trading の場合は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離することを明記。
  - 起動時に stop フラグ（data/stop_requested.flag）が存在すればエンジンを起動せず終了する安全措置を実装。
  - Engine は別スレッドで run_session を実行し、停止フラグ検知時に engine.stop() を呼んで安全に停止する。
- run_monitoring の挙動:
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化・記録する仕様（monitoring は本番状態の監視が目的のため）。
- DuckDB は分析用 DB（paths via Settings）として複数モジュールで利用される（factor_research、execution 等）。
- validate_config は config/*.yaml の存在チェックを行い、PyYAML が無ければパース検証をスキップして警告する。
- 一部モジュール（factor_research の calc_momentum 等）は実装途中の記述がある（今後の拡張予定）。

未解決 / TODO（今後の改善点）
- position_sizing の価格欠損（price == 0.0）の扱い: 前日終値や取得原価でのフォールバックを検討中（コメントあり）。
- 各戦略・リスク設定の動的読み込み（config/*.yaml）の運用とバリデーション強化。
- factor_research の完全実装（各ファクター計算ロジックの完成）。
- BrokerClientFactory / ExecutionEngine 等の外部依存（ブローカー API）に対するモック・テストカバレッジの整備。

ライセンスと注意
- .env は機密情報を含むためリポジトリにコミットしないでください（config_setup のヘッダにも注記済み）。

--- 
この CHANGELOG はソースコードの現在の状態から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース方針に基づき追記・整理してください。