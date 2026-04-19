# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-19

Added
- 基本機能の初期実装を追加（初回リリース）。
- 実行用スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用の MockBrokerClient を利用し、SQLite は paper_trading.db（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離する。
    - 起動時にプロセス優先度を "high" に設定するフックを実装（utils.process_priority）。
    - エンジンはスレッドで実行され、data/stop_requested.flag の存在で安全に停止する。PID ファイルを data/execution.pid に書き込む（設定により上書き可能）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正な値（0以下や非整数）の場合はデフォルトにフォールバックして警告を出力。
    - 監視向け DB は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用（監視データは本番 DB に記録される想定）。
    - 起動時にプロセス優先度を "high" に設定し、stop flag でループを終了する実装を提供。
- 設定・環境管理
  - config.py: 環境変数および .env/.env.local の自動ロード機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を探索して決定（CWD に依存しない）。
    - .env パーサは export 形式、クォート、インラインコメント等に対応。
    - Settings クラスを提供し、各種設定値（J-Quants トークン、kabu API、DB パス、ログレベル、殺害フラグ関連、閾値など）をプロパティ経由で取得可能。
    - PAPER_FILL_MODE 等の検証ロジック（有効値チェック）を追加。
- 設定補助 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成・更新するツールを追加。
    - 多数の設定項目（実行環境、API トークン、DB パス、ログレベル、Kill Switch 設定など）を対話的に設定、.env に保存可能。
  - validate_config.py: 起動前に .env および config/*.yaml を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML 有無で挙動分岐）、本番向けの追加ガード（LINE 通知設定や Kill Flag の自動クリア設定の警告）を実装。
    - --strict モードで警告も失敗扱いにできる。
- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日分保持）をルートロガーに設定。
    - 既存ハンドラをクリアして二重登録を防止。LOG_LEVEL / LOG_DIR / level / log_dir 引数から解決。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py: プロセス優先度および CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する実装。優先度 "high"/"normal"/"low" をサポート。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足等は警告でスキップ）。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 小）で選別。
    - calc_equal_weights / calc_score_weights: 等分配とスコア加重配分。全スコアが 0 の場合は等分配にフォールバックして WARNING を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存ポジションのセクター比率が上限（デフォルト 30%）を超える場合、新規候補から当該セクターを除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた資金乗数を返す（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告して 1.0 を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method に応じた発注株数計算を実装（"risk_based", "equal", "score"）。
    - risk_based: risk_pct と stop_loss_pct を用いたリスクベース算出。単元（lot_size）丸め、1 銘柄上限と aggregate cap、cost_buffer による保守的見積りを実装。
    - aggregate cap を超える場合はスケーリングし、lot 単位で端数調整（残差優先分配）を行う。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数等を算出。
    - 既定の合格基準（コメント内定義）: 稼働率 >= 99.0%、fill_rate >= 90%、send_rate >= 95%、P95 レイテンシ <= 200 ms。
    - データ不足・テーブル未存在時は N/A 表示か Graceful に扱う。
- 研究用ファクタモジュール（部分実装）
  - research/factor_research.py: DuckDB を用いたモメンタム等のファクタ計算の骨格を追加（価格テーブル参照、移動平均・リターン・ATR 等を計算する設計）。（ファイルが途中まで含まれています）

Changed
- パッケージメタ
  - パッケージバージョンを __init__.py にて "0.1.0" に設定。

Fixed
- （初回リリースのため該当なし。詳細なバグ修正は以降のリリースで記録予定）

Security
- 機密情報取扱い
  - config_setup のウィザードでシークレット項目（API トークン等）はマスク表示する等の配慮を実装。.env ファイルは Git にコミットしないよう注意喚起を追記。

Notes / 補足
- 環境変数自動ロード
  - プロジェクトルートが検出できない環境や KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定した場合、自動読み込みはスキップされます（テスト時に便利）。
- ロギング
  - ログはデフォルトで logs/<app_name>.log に日次ローテートで出力されます。ログディレクトリが作成できない場合でもコンソールログは利用可能です。
- モニタリングとデータベース
  - run_monitoring は監視用テーブルの初期化を行い、duckdb も接続します。監視は本番 sqlite_path に記録する設計です（環境分離が必要な場合は設定見直しを推奨）。

今後の予定（予定機能）
- factor_research の完全実装（ファクター計算の SQL/集計実装完了）
- ExecutionEngine / BrokerClient の詳細実装とテストカバレッジ拡充
- モニタリング・アラートの LINE 連携など運用通知機能の追加

-----------------------------------------------------------------------------
参考: 主要 CLI / スクリプト
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動:          python -m kabusys.run_monitoring
- 設定ウィザード:    python -m kabusys.config_setup
- 設定検証:          python -m kabusys.validate_config [--strict]
- Paper レポート:    python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

(この CHANGELOG はコードベースから推測して記載しています。実際の運用上の挙動や追加の変更点がある場合は、適宜更新してください。)