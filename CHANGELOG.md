CHANGELOG
=========

すべての重大な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- （なし）

[0.1.0] - 2026-04-22
--------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - 実行／監視ランチャー
    - run_execution.py
      - ExecutionEngine を起動する CLI スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離する挙動を実装。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository／OrderManager／RiskManager／Reconciler の組み立てを行い、エンジンをバックグラウンドスレッドで実行。
      - 停止制御に data/stop_requested.flag を監視し、停止時は Engine.stop() を呼び出して安全終了。
      - PID ファイルのパス管理（data/execution.pid）。
    - run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
      - 監視用 DB は KABUSYS_ENV に依らず本番 sqlite_path を使用する設計。
      - 停止フラグ（data/stop_requested.flag）でループ終了。
  - 設定・環境管理
    - config.py
      - Settings クラスを追加。環境変数や .env/.env.local の自動読込（プロジェクトルート検出に .git / pyproject.toml を利用）。
      - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
      - .env パース機能を実装（export 形式、クォート文字列・バックスラッシュエスケープ、インラインコメントの扱い等を考慮）。
      - 各種設定値のバリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
  - 設定支援ツール
    - config_setup.py
      - 対話式ウィザードで .env を初期作成・更新する CLI を追加（項目、ヒント、シークレットマスク表示、確認保存）。
    - validate_config.py
      - 起動前に .env と config/*.yaml を検査する CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML パース検証、KABUSYS_ENV=live 時の追加ガード等を実装。
      - --strict オプションで警告も失敗扱いに可能。
  - ポートフォリオ構築（純粋関数群）
    - portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights）を追加。
    - portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を追加。
    - portfolio/position_sizing.py
      - position sizing ロジックを追加（risk_based / equal / score の割当方式、単元株丸め、単銘柄上限・総投下上限スケーリング、cost_buffer による保守的見積り、残差の分配アルゴリズムなど）。
    - portfolio/__init__.py によるエクスポートを追加。
  - 研究用ファクター計算
    - research/factor_research.py（モメンタム等の計算基盤を追加、DuckDB を利用する設計。）
      - （注）ファイル末尾が途中まで含まれており、モメンタム計算実装の続きを想定。
  - ユーティリティ
    - utils/logging_setup.py
      - 統一的なロギング設定ユーティリティを追加。
      - stdout (StreamHandler) と 日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを実装。
      - 日次ローテーション保持日数は 30 日。
    - utils/process_priority.py
      - psutil を用いたプロセス優先度設定ユーティリティを追加（Windows/Linux/macOS を吸収）。
      - CPU affinity を N コアに固定する機能も提供。権限不足時は警告を出してスキップ。
  - モニタリング DB 初期化
    - monitoring.monitoring_db.init_monitoring_db が起動時に呼ばれ、監視テーブルの存在を保証（冪等）。
  - ペーパートレード検証ツール
    - tools/paper_verification_report.py
      - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から期間フィルタで集計し、稼働率、注文成功率、送信率、レイテンシ（P95 等）を算出して PASS/FAIL 判定するレポートを追加。
      - 各種閾値（稼働率 99%、成立率 90% など）を定義、欠損データに対する N/A 出力や例外耐性を実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし、ただし各モジュール内で入力値のバリデーションや例外ハンドリングを強化）

Security
- 環境変数ファイル（.env）に関する注意
  - config_setup で生成される .env は「絶対に Git にコミットしないこと」を明記。

Notes / Usage Highlights
- MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔を秒単位で指定可能（不正値はデフォルト 60 秒にフォールバックして警告）。
- KABUSYS_ENV による挙動差分:
  - development: 開発用（既定）
  - paper_trading: 発注を仮想化（専用 DB を使用）
  - live: 本番（実際の発注が行われるため設定を厳重に確認すること）
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われる。必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存される。ログディレクトリ作成失敗時はコンソール出力のみとなるが、動作は継続する。

Acknowledgements / TODO
- research/factor_research.py など一部ファイルは続き実装を想定しており、データ取得や追加正規化処理（Z-score 等）の統合が今後の作業となります。
- 将来的な拡張として、銘柄ごとの lot_size をマスタで管理する設計変更や、価格欠損時のフォールバックルールの追加を検討中。

----