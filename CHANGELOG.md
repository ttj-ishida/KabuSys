Keep a Changelog に準拠した形式で、コードベースから推測した変更履歴を日本語で作成しました。リリースはパッケージの __version__ (0.1.0) に合わせて初回公開の記録としてまとめています。

CHANGELOG.md
=============

すべての変更は "Unreleased" → リリースごとに移動してください。  
日付は YYYY-MM-DD 形式です。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-19
--------------------

Added
- 初回リリース: KabuSys 基本モジュール一式を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
- 起動スクリプト / 実行系
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）の検出で安全にループ終了。
    - Monitoring は KABUSYS_ENV にかかわらず production の sqlite_path を使用する（監視 DB を環境に依存させない設計）。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（BrokerClientFactory により生成）を使用し、paper_trading 用の専用 SQLite（data/paper_trading.db、環境変数で上書き可能）に記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理（data/execution.pid）に対応。
    - スレッドで Engine を起動し、停止フラグ/スレッド終了を監視して安全にシャットダウン。
- 設定管理 / ユーティリティ
  - config.py
    - 環境変数アクセスをラップする Settings クラスを実装。
    - .env 自動読み込み機構を追加（プロジェクトルートを .git / pyproject.toml により探索）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 複数の設定プロパティを提供（J-Quants、kabuステーション、LINE、DB パス、監視閾値、環境判定など）。不正な値は ValueError で通知。
    - PAPER_FILL_MODE の検証や paper_sqlite_path 等、paper_trading 用設定を明示。
  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを追加。秘密値はマスク表示。デフォルト/既存値を再利用可能で .env を安全に生成。
  - validate_config.py
    - 起動前チェック CLI を追加。必須環境変数の有無、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ存在、config/*.yaml の存在と YAML パース（PyYAML があれば内容検証）などを実行。
    - --strict オプションで警告を FAIL として扱う。
- ポートフォリオ構築モジュール（純粋関数群、DB 参照なし）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で上位 N を選択する関数。
    - calc_equal_weights / calc_score_weights: 等分配・スコア正規化配分。スコア全てが 0 の場合は等分配へフォールバックして警告を出力。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限に基づいて新規候補を除外する関数。既存保有や売却予定の考慮、"unknown" セクターの扱いを実装。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）ごとの投下資金乗数を返す。未知レジームはフォールバック（1.0）して警告。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数決定ロジックを実装。
    - lot_size（単元）考慮、max_position_pct / max_utilization / cost_buffer を反映した aggregate cap（スケーリング）や端数処理、残余キャッシュ配分ロジックを実装。
- モニタリング / ペーパートレード検証ツール
  - tools.paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH 指定可）から稼働率、注文成功率、送信率、レイテンシ指標（avg/max/P95）等を集計するレポート生成スクリプトを追加。
    - Pass/Fail の閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義して総合判定を出力。
    - 日付フィルタ（--from / --to）および DB パス指定（--db）に対応。
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup
    - 統一的な logging 設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数 override に対応。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力にフォールバック。
  - utils.process_priority
    - set_process_priority(level) を追加（"high"/"normal"/"low"）。Windows / POSIX（Linux/Mac/FreeBSD）に対応し、psutil 経由で優先度を設定。アクセス拒否等は警告してスキップ。
    - set_cpu_affinity(cpu_count) を追加。利用コア数指定で CPU affinity を設定（権限不足等は警告してスキップ）。
- monitoring.monitoring_db の初期化用 init_monitoring_db 関数が呼び出されるよう起動スクリプトに組み込み（冪等に監視テーブルを確保）。
- research.factor_research（ファクター計算の骨組み）
  - momentum 等の計算ロジックを準備（DuckDB 接続を受け prices_daily/raw_financials を参照する設計）。（ファイル末尾はコード切れのため実装継続が想定される）

Security
- .env に関する注意書き: config_setup で生成される .env は絶対に Git にコミットしない旨を明記。

Notes / Design decisions
- Monitoring と Execution の DB 取り扱いは分離設計:
  - 監視（monitoring）は常に production 用 sqlite_path を参照（運用監視の一貫性を確保）。
  - Execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 sqlite を使用して本番 DB と分離。
- .env 自動読み込みはプロジェクトルート検出に基づく。配布後やテストで自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用。
- ロギングは stdout を基準にしつつファイル出力を行うため、cron 等で stdout を一括管理する運用に親和性あり。
- 例外や権限不足に対してはログ出力で安全にフォールバックする方針（サービス停止を避ける）。

Known issues / TODO
- portfolio.position_sizing:
  - price が欠損（0 や None）の場合のフォールバック価格（前日終値・取得原価など）は未実装。将来的に stocks マスタから lot_size やフォールバック価格を取得する計画あり（TODO コメントあり）。
- research.factor_research はファイル末尾が切れているため、完全な実装は継続が必要。
- config/*.yaml の自動生成スクリプトや具体的な YAML 内容チェックはプロジェクトの別スクリプト（generate_config.py 参照の記述）に依存しており、その設置が必要。

---

この CHANGELOG は提供されたソースコードの内容から推測して記載しています。実際のリリースノートや変更履歴と差異がある可能性があるため、必要に応じてプロジェクトの責任者による確認・補足をおすすめします。