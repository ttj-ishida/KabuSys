CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
- 初回リリースを追加。
- 実行/運用用スクリプト
  - src/kabusys/run_execution.py：ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用の専用 SQLite (data/paper_trading.db をデフォルト) を使用。
    - BrokerClientFactory により実運用 / モックブローカーの切替を実装。
    - ExecutionEngine をスレッドで起動し、 data/stop_requested.flag による停止検出、data/execution.pid での PID 管理をサポート。
    - 起動時にプロセス優先度を "high" に設定。
  - src/kabusys/run_monitoring.py：SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止フラグファイル (data/stop_requested.flag) によりループ終了。
    - Monitoring は環境に関わらず本番 sqlite_path を使用して監視データを永続化。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・セットアップ
  - src/kabusys/config.py：環境変数のロードと Settings クラスを実装。
    - .env/.env.local の自動ロード機能（プロジェクトルート判定: .git または pyproject.toml）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - .env パーサは export 構文、クオート、エスケープ、インラインコメント等を考慮した堅牢な実装。
    - Settings により各種設定をプロパティ経由で取得（DB パス、KABUSYS_ENV, PAPER_FILL_MODE 等）。
    - 環境値の妥当性検査（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
  - src/kabusys/config_setup.py：対話式ウィザードで .env を生成・更新する CLI を追加。
    - デフォルト値、選択肢表示、シークレット（マスク）入力、保存確認をサポート。

- 検証ツール
  - src/kabusys/validate_config.py：起動前に .env および config/*.yaml を検証する CLI を追加。
    - 必須/任意の環境変数チェック、パスの親ディレクトリ存在チェック、YAML パースチェック（PyYAML が存在する場合）を実行。
    - --strict モードで警告も失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - src/kabusys/utils/logging_setup.py：統一ロギング初期化ユーティリティを追加。
    - stdoutへの StreamHandler と 日次ローテートする TimedRotatingFileHandler（logs/<app>.log）を設定。
    - ログディレクトリ自動作成。失敗時はファイル出力をスキップしコンソール出力のみ継続。
    - ログローテーション保持 30 日。
  - src/kabusys/utils/process_priority.py：プラットフォーム差を吸収したプロセス優先度と CPU affinity 設定を追加。
    - Windows/Linux/macOS の差分吸収、パーミッション不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py：
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
    - スコアが全て 0 の場合は等配分へフォールバック（警告出力）。
  - src/kabusys/portfolio/risk_adjustment.py：
    - セクター集中上限チェック（apply_sector_cap）。
    - 市場レジームに応じた乗数（calc_regime_multiplier、bull/neutral/bear をサポート、未知は 1.0 にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py：
    - 各種配分方式（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株（lot_size）で丸め、最大ポジション上限・投下資金上限・コストバッファの考慮、スケーリングロジックを含む。

- 研究/分析
  - src/kabusys/research/factor_research.py：ファクター計算モジュール（モメンタム／Value／Volatility／Liquidity）を追加（DuckDB を用いた実装を想定、prices_daily / raw_financials を参照）。（一部未完）

- 運用ツール
  - src/kabusys/tools/paper_verification_report.py：Paper Trading 用検証レポート生成スクリプトを追加。
    - DB（デフォルト data/paper_trading.db）から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計。
    - 合格基準（例: 稼働率 >= 99%、注文成功率 >= 90%、P95 latency <= 200ms）に基づく PASS/FAIL 判定を出力。
    - --from / --to / --db オプションをサポート。

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- （このリリースは初版のため該当なし）

Fixed
- （このリリースは初版のため該当なし）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / 実装上の注意
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値が設定された場合にデフォルト 60 秒へフォールバックして警告を出力する実装です。
- config.py による .env 自動ロードはプロジェクトルート検出に依存しており、検出できない場合は自動ロードをスキップします。
- position_sizing / risk_adjustment の各関数は純粋関数（副作用なし）として設計され、単体テストしやすいように DB 参照は行いません。
- ログは標準出力（stdout）に出す設計のため、cron 等で stdout のリダイレクトを行う運用に適しています。

今後の予定（候補）
- factor_research の完全実装とユニットテスト追加
- ExecutionEngine / Monitoring の統合テストおよび E2E テストスイート整備
- 銘柄別 lot_size や手数料・スリッページモデルの外部化・設定化
- 既存モジュールの型注釈強化とドキュメント追加

-----