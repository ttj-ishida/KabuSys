CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- （現時点なし）

[0.1.0] - 2026-04-21
--------------------

Added
- 初回リリース。
- コア機能・モジュールを追加:
  - アプリケーション情報: kabusys.__version__ = "0.1.0"
  - 設定管理:
    - kabusys.config.Settings クラスを導入。環境変数から設定値を取得する統一インターフェースを提供。
    - .env 自動読み込み機構を追加（プロジェクトルートを .git / pyproject.toml で検出）。読み込み順序は OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env 解析器は export 形式・クォート（シングル/ダブル）・エスケープ・インラインコメントに対応。
    - 各種設定プロパティを実装（J-Quants、kabuステーション、LINE、DBパス、監視閾値、環境判定等）。
    - PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH 等、ペーパートレード関連の設定をサポート。
  - 起動スクリプト:
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止時は data/stop_requested.flag によって優雅に終了。
      - 監視用 DB は実行環境にかかわらず本番 sqlite_path を使用する設計。
    - run_execution: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用のペーパートレード DB（data/paper_trading.db）を使用し本番 DB と分離。停止フラグや pid ファイルをサポートし、別スレッドでエンジンを実行・監視して優雅に停止する。
  - ロギング:
    - kabusys.utils.logging_setup.setup_logging を追加。全起動スクリプトからの統一的ログ設定を提供。
      - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定。
      - 既存ハンドラの二重設定防止（既存ハンドラを flush/close してから削除）。
      - LOG_DIR/LOG_LEVEL 環境変数または引数からの解決、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - プロセス優先度 / CPU affinity:
    - kabusys.utils.process_priority を追加。psutil 経由で Windows / POSIX の差分を吸収、set_process_priority/set_cpu_affinity を提供。権限不足等の際は警告を出し処理をスキップするフェイルセーフを実装。
  - 構成管理(手動支援) / 検証 CLI:
    - kabusys.config_setup: .env を対話式に作成・更新するウィザードを追加（シークレット入力や選択肢表示、保存確認）。.env のテンプレート・書式は Git にコミットしないよう明記。
    - kabusys.validate_config: 設定検証 CLI を追加。.env や config/*.yaml の存在・妥当性、主要環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、production 時の追加ガード等を実装。--strict オプションで警告を FAIL 扱いにできる。
    - validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す。
  - ポートフォリオ構築関連（純粋関数群）:
    - kabusys.portfolio.portfolio_builder:
      - select_candidates: BUY シグナルのソートと上位 N 選抜
      - calc_equal_weights / calc_score_weights: 重み付け計算（スコア合計が 0 の場合のフォールバック）
    - kabusys.portfolio.risk_adjustment:
      - apply_sector_cap: セクター集中制限による候補フィルタ
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear; 未知は警告とフォールバック）
    - kabusys.portfolio.position_sizing:
      - calc_position_sizes: 複数の allocation_method をサポート（risk_based / equal / score）。単元株（lot_size）丸め、銘柄別上限、aggregate cap（利用可能現金へのスケーリング）、コストバッファ考慮、残差配分ロジックなどを実装。
  - ツール:
    - kabusys.tools.paper_verification_report: ペーパートレード結果の検証レポート生成ツールを追加。期間指定（--from / --to / --db）に対応。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）等を算出し PASS/FAIL を判定する閾値を定義（稼働率 >= 99%、成立率 >= 90% 等）。
  - リサーチ:
    - kabusys.research.factor_research: DuckDB 接続を受け取りファクター（Momentum, Value, Volatility, Liquidity 等）を計算するための骨組みを追加（関数・定数・説明あり）。注: ファイル末尾が途中で切れている（実装継続の余地あり）。
  - モニタリング DB 初期化ユーティリティの呼び出しを起動時に行う（init_monitoring_db を run_monitoring/run_execution から呼び出し）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Known issues / Notes
- research/factor_research.py はファイル末尾で途中までの実装となっており、いくつかの関数（例: calc_momentum の続き）が未完。今後のリリースで完成予定。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にスキップする（注記あり）。将来的に前日終値や取得原価でのフォールバックが必要。
- apply_sector_cap は "unknown" セクターを上限適用外とする設計。必要に応じて挙動を変更可能。
- set_process_priority / set_cpu_affinity は権限不足や未サポート OS の場合に設定をスキップし警告を出すフェイルセーフが入っている。
- run_monitoring は Monitoring 用 DB に常に sqlite_path（本番）を使う設計。意図的な分離が必要な場合は環境変数の見直しを検討のこと。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラを無効化して stdout のみで継続する設計。

作者・連絡
- 本リポジトリのコード構成・コメント・ドキュメントを元に変更履歴を推測して作成しました。実際のリポジトリ履歴（コミット単位）に合わせて適宜修正してください。