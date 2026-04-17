# Changelog

すべての変更は「Keep a Changelog」形式に準拠しています。  
リリース日: 2026-04-17

## [0.1.0] - 2026-04-17

### Added
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。engine.run_session を別スレッドで実行し、data/stop_requested.flag を検知して安全に停止。
    - デフォルトの RiskConfig 値を定義（最大ポジション比率、利用率、レートリミット、サーキットブレーカーなど）。初期利用可能現金は broker.get_available_cash() を使用。
    - PID ファイル path を引き渡す（_EXECUTION_PID）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログ警告のうえデフォルトへフォールバック。
    - 監視用途は実行環境に関わらず本番 sqlite_path を使用（Settings.sqlite_path）。
    - data/stop_requested.flag を検知してループを終了。
    - 起動時にプロセス優先度を "high" に設定（set_process_priority 呼び出し）。
    - init_monitoring_db による監視用 DB テーブルの初期化（冪等）。

- 設定・環境管理
  - config.py
    - .env の自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml から探索）。OS 環境変数を保護するため上書きロジックを実装。
    - .env 行のパーサーを強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、コメント処理の改善）。
    - Settings クラスを導入し、各種設定をプロパティ経由で取得可能に（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、PID_FILE_PATH、各種しきい値など）。
    - PAPER_FILL_MODE の検証（有効値チェック）とデフォルト値（"instant"）。
    - 環境種別（development / paper_trading / live）とログレベルの検証ロジックを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。

  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - デフォルト値や選択肢表示、シークレット入力のマスク表示、既存 .env の読み込みと Enter で再利用、最終確認後に .env を書き込み（.env 保存時のテンプレート出力）。
    - .env はコミットしないよう警告を埋め込む。

  - validate_config.py
    - 起動前の設定検証 CLI を追加。
    - 必須/任意環境変数チェック、KABUSYS_ENV の整合性チェック、LOG_LEVEL チェック、DB パス（親ディレクトリ存在）チェック、config/*.yaml の存在および PyYAML によるパース検証（PyYAML がない場合は検証スキップ）を実装。
    - --strict オプションで警告を FAIL 扱いにする。

- ポートフォリオ構築関連（純粋関数・ロジック）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順ソート（同点は signal_rank でブレーク）と上位 N 抽出。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア正規化分配（score の合計が 0 の場合は等配分にフォールバック、警告ログ）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存ポジションのセクター比率に応じて新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマップ。未知のレジームは 1.0 でフォールバック）。

  - portfolio/position_sizing.py
    - calc_position_sizes: 複数の allocation_method（"risk_based", "equal", "score"）をサポートし、各銘柄の発注株数（単元株丸め、max_position_pct による per-stock 上限、aggregate cap によるスケーリング、cost_buffer を用いた保守的見積り）を計算。
    - aggregate スケーリング時の端数処理（lot_size 単位で残差に基づき追加配分）を実装。

  - portfolio/__init__.py にて上述関数を公開。

- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX（Linux, Darwin, FreeBSD）を吸収したプロセス優先度設定ユーティリティ（権限不足等は警告でスキップ）。
    - set_cpu_affinity: 指定コア数への CPU affinity 固定をサポート（存在しない API / 権限不足は警告でスキップ）。
    - プラットフォーム差異に対するフォールバック実装。

- リサーチ（DuckDB ベース）
  - research/factor_research.py
    - calc_momentum: mom_1m/3m/6m、ma200 乖離率を計算。データ不足は None。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率等を計算（真の範囲 true_range の NULL 伝播制御などを実装）。
    - DuckDB を使った SQL + Python の混合で効率的に計算する設計。prices_daily / raw_financials のみ参照。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレードの検証レポートを生成する CLI を追加。
    - PAPER_TRADING_SQLITE_PATH / --db で DB を指定可能。日付範囲指定 (--from / --to) に対応。
    - 指標: 稼働率 (uptime)、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、平均/最大/P95 レイテンシ。
    - パス/フェイル基準をデフォルトで定義（uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200 ms）。欠損データに対する扱いを明示。

### Changed
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

### Fixed
- 環境値の堅牢性向上
  - MONITOR_POLL_INTERVAL が不正な値（非数値や 0 以下）だった場合に警告を出力しデフォルトにフォールバック（run_monitoring.py）。
  - .env パーサーの引用符とエスケープの扱いを改善し、コメント判定の誤認を抑制（config.py）。
  - validate_config.py: PyYAML が未インストールの場合に YAML 検証をスキップして適切に警告を出すようにした。

### Security
- .env の取り扱いに関する注意を追加（config_setup.py のヘッダに「.env を絶対に Git にコミットしないこと」明記）。
- 環境変数未設定時は明示的に ValueError を投げる（必須値取得時の _require）。

### Notes / Misc
- DB 初期化: init_monitoring_db を呼び出して監視用テーブルの存在を保証（冪等）。run_execution/run_monitoring で利用。
- 停止制御: data/stop_requested.flag を用いた外部停止フラグ機構を採用（両起動スクリプトで共通）。
- PID / フラグ / キルスイッチ周りの設定は Settings 経由で環境変数から上書き可能（PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）。
- 多くの箇所で権限不足や環境差異を想定して安全にフォールバックする実装（プロセス優先度、CPU affinity、DuckDB/SQLite 接続例外等）。

もしリリースノートの粒度（ファイル別、開発者向け詳細、ユーザー向けのハイライト）を調整したい場合は、どの観点にフォーカスするかを指定してください。