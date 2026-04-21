# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-04-21

### 追加
- 基本パッケージ初回リリース。
- 起動用スクリプトを追加:
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行する起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下 data/stop_requested.flag ファイルで検知。
    - 監視は KABUSYS_ENV に関わらず本番用の sqlite_path を使用する設計（意図的な分離）。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と完全分離。
    - 停止は data/stop_requested.flag を監視し、実行中スレッドに対して engine.stop() で安全停止を行う。
- 設定管理・自動ロード:
  - config.py
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パースの堅牢化（export プレフィックス、クォート文字列、インラインコメントなどに対応）。
    - Settings クラスを提供し、J-Quants / kabu ステーション / DB /監視閾値 などの設定をプロパティ経由で取得。
    - PAPER_FILL_MODE の検証（有効値: instant, partial, never, reject）。
    - 環境チェック用プロパティ: is_live / is_paper / is_dev など。
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。
    - シークレット値は入力時にマスク表示・保存ファイル生成の際は注意書き出力。
- 設定検証 CLI:
  - validate_config.py
    - .env および config/*.yaml の設定検証ツールを追加。
    - 必須環境変数の有無、KABUSYS_ENV の妥当性、LOG_LEVEL の妥当性、DB パス親ディレクトリの存在、YAML ファイルの存在とパース（PyYAML がある場合）を検査。
    - --strict オプションで警告を失敗扱いにできる。
- ロギングユーティリティ:
  - utils/logging_setup.py
    - ルートロガーを統一的に設定する setup_logging() を追加。
    - stdout 出力の StreamHandler（stderr ではなく stdout を利用）と、日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）を設定。
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
- プロセス優先度ユーティリティ:
  - utils/process_priority.py
    - set_process_priority(level) により Windows / POSIX を吸収して優先度設定を試行。
    - set_cpu_affinity(cpu_count) により最初の N コアにピニング可能（未指定なら変更しない）。
    - 権限不足や未対応 OS の場合は警告を出し安全にスキップする実装。
- Portfolio 構築モジュール:
  - portfolio/portfolio_builder.py
    - select_candidates(): スコア降順で候補選定。
    - calc_equal_weights(), calc_score_weights(): 重み算出。スコア全てが 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中チェックと候補除外ロジック（unknown セクターは制限対象外）。
    - calc_regime_multiplier(): market レジームに応じた投下資金乗数（bull/neutral/bear のマッピングと未知レジームのフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method（risk_based / equal / score）に基づく株数計算、lot_size（単元）で丸め、per-stock と aggregate のキャップ処理、コストバッファ考慮、スケーリング時の残差配分ロジックを実装。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py
    - ペーパートレード SQLite（デフォルト data/paper_trading.db）を読み取り検証レポートを生成。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - CLI で期間指定 (--from, --to) および --db 指定が可能。
- 研究向けファクター計算基盤:
  - research/factor_research.py
    - DuckDB を利用したファクター計算モジュールの骨組み（モメンタム・移動平均乖離等の計算ロジックを実装予定）。（モジュールの一部は継続実装が想定される）

### 変更
- ルートパッケージのバージョンを __version__ = "0.1.0" に設定。
- run_monitoring と run_execution の起動時にプロセス優先度を最初に High に設定するよう統一。

### 修正（挙動上の注意／仕様）
- .env のパース挙動を強化:
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント判定ルールに対応。
  - 自動ロード時の上書きルール: OS 環境変数は保護され、.env.local は .env の上位（override=True）で読み込まれる。
- LOG ハンドラ設定:
  - 既存ハンドラがある場合は一度全ハンドラを flush/close してから再設定し、二重出力を防止。
- Process priority / CPU affinity は権限不足や非対応環境でも例外を投げず警告ログでスキップ。

### 既知の制限 / 注意点
- run_monitoring は「監視用途の DB」として常に settings.sqlite_path（デフォルト data/monitoring.db）を使用する設計になっており、KABUSYS_ENV による DB 切り替えは行わない点に注意してください（これは意図的な設計であり、本番監視 DB を一意に保つ目的によるものです）。
- portfolio.position_sizing.calc_position_sizes:
  - price が欠損（0 や None）の場合は銘柄をスキップするため、価格データの完全性が必要。
  - 将来的に銘柄ごとの単元情報（lot_size）やフォールバック価格を導入する余地あり（TODO コメントあり）。
- research/factor_research.py はファイル末尾が部分的に未完（続きの実装が必要な箇所あり）。研究用モジュールとして追加済みだが、完全な機能化は今後の作業予定。

### ドキュメント / 開発者向けメモ
- .env の初期化には config_setup.py の対話式ウィザードを使用推奨。生成後は validate_config.py で設定検証を行ってください。
- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます。LOG_DIR 環境変数または setup_logging の引数で変更可。
- Paper Trading の検証は tools/paper_verification_report.py を利用。P95 計算や閾値はスクリプト内の定数で管理。

---

今後の予定:
- research/factor_research の完全実装（ファクター計算の SQL 実装と Z スコア正規化連携）。
- 単元数や銘柄別メタ情報（lot_size 等）をデータマスタ化して position_sizing を拡張。
- 監視・実行コンポーネントの統合テストとドキュメント整備。