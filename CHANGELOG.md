# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

- （現在の作業ブランチ／今後の変更点はここに記載します）

## [0.1.0] - 2026-04-17

初回リリース。自動売買システム KabuSys の基本モジュール群と CLI ユーティリティを導入しました。主な追加点は以下の通りです。

### Added
- 基本パッケージとバージョン情報
  - src/kabusys/__init__.py にバージョン `0.1.0` を追加。

- 設定管理
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルートの .env および .env.local をロード、OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 複雑な .env 行パース（export プレフィックス、クォート内のエスケープ、インラインコメント判定等）を実装。
    - Settings クラスを導入し、J-Quants / kabuステーション / LINE / DB / 監視 / システム設定等をプロパティとして提供。
    - PAPER_FILL_MODE の入力検証（有効値: instant/partial/never/reject）。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）などのプロパティを追加。

- 設定ユーティリティ / CLI
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
    - 入力項目定義、既存 .env の読み込み、確認・保存機能を実装。
  - src/kabusys/validate_config.py
    - 起動前に .env および config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベルチェック、DB パスの親ディレクトリ確認、YAML のパース検証（PyYAML がインストールされていない場合は警告）、本番用ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
    - --strict オプションで警告を失敗扱いにするモードを提供。

- 実行・監視エントリポイント
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離（Settings による切替）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository、OrderManager、RiskManager、Reconciler の組み立て。
    - RiskManager 用のデフォルト RiskConfig を導入（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等の初期値）。
    - エンジンを別スレッドで実行し、data/stop_requested.flag による停止監視、pid ファイルの扱いを実装。
    - 起動直後にプロセス優先度を "high" に設定（utils/process_priority）。

  - src/kabusys/run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0以下の無効値は安全にデフォルトへフォールバック）。
    - 監視は環境に関係なく production 用 sqlite_path を使用して監視データを記録する挙動を明示。
    - stop flag（data/stop_requested.flag）によるループ終了、例外発生時のロギングと継続、KeyboardInterrupt ハンドリングを実装。
    - 起動時にプロセス優先度を "high" に設定。

- モニタリング DB 初期化
  - src/kabusys/monitoring/monitoring_db.py（参照されている init_monitoring_db）により監視テーブルの冪等な初期化を想定（run_execution/run_monitoring で利用）。

- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - スコアが全て 0 の場合のフォールバックと警告。

  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（既存保有時価を基に上限を超えるセクターの新規候補を除外）。
    - 市場レジームに基づく資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピングと未知レジームのフォールバック）。

  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 損切り・リスク率ベースの目標株数算出、単元株（lot_size）での丸め、1銘柄上限・集計上限（available_cash）でのスケールダウン処理を実装。
    - cost_buffer を使った保守的なコスト見積もり、残差に基づく再配分ロジックを実装。

  - src/kabusys/portfolio/__init__.py に上記関数群をエクスポート。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - プロセス優先度設定（Windows と POSIX を吸収）を実装。set_process_priority(level) により high/normal/low を設定可能。
    - CPU affinity 固定用の set_cpu_affinity(cpu_count) を追加（指定が None の場合は無視）。
    - 権限不足や未サポート環境では警告ログを出して安全にスキップ。

- 研究 / ファクター計算
  - src/kabusys/research/factor_research.py
    - DuckDB を使ったファクター計算基盤（モメンタム / ボラティリティ / 流動性等）を追加。
    - calc_momentum(): 1M/3M/6M リターン、MA200 乖離率を計算（データ不足ハンドリング）。
    - calc_volatility(): ATR20、相対 ATR、20日平均売買代金、出来高比等を計算するクエリを実装。
    - DuckDB 上の prices_daily テーブルを前提とした設計。

- 検証ツール（Paper Trading 向け）
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite から稼働率・注文成功率・送信率・レイテンシ等を集計してレポート出力するスクリプトを追加。
    - 日付フィルタ（--from / --to）、DB パスのオプション（--db）をサポート。環境変数 PAPER_TRADING_SQLITE_PATH からの指定も可能。
    - P95 計算、N/A 表示、しきい値による PASS/FAIL 判定（稼働率 99%、成立率 90% 等）を実装。

- その他
  - 各 CLI スクリプトは main ガードを備え、単体で実行可能。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数ファイル (.env) は絶対に Git にコミットしない旨を config_setup の出力に明示。

### Notes / Implementation details
- run_monitoring は MONITOR_POLL_INTERVAL の不正値（非数・0 以下）を安全に扱い、デフォルト値にフォールバックして動作継続します。
- run_execution は paper_trading モード時に本番 DB と完全に分離した専用 SQLite（デフォルト data/paper_trading.db）を使用する設計です。
- Settings.env の検証で不正な KABUSYS_ENV 値が与えられた場合は ValueError を送出し、早期に設定ミスを検出します。
- position_sizing の aggregate scale-down ロジックは lot_size 単位での調整を行い、残余キャッシュを利用して再配分する仕組みを導入しています。
- process_priority 設定は権限不足などで失敗する可能性があるため、失敗時には警告を出して処理を継続します（安全優先）。

---

今後の予定:
- monitoring_db や SystemMonitor、ExecutionEngine などの詳細実装のユニットテスト追加。
- 戦略やブローカークライアントのモックを用いた統合テスト。
- ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）に基づく更なる検証ツールの整備。