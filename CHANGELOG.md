# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」準拠の形式を採用しています。

最新リリース: 0.1.0（初版）

## [0.1.0] - 2026-04-18

### 追加
- 実行用スクリプト
  - run_execution.py を追加。
    - ExecutionEngine をスレッドで起動・監視するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を用い、本番 DB と分離して動作。
    - BrokerClientFactory を使ってブローカークライアントを生成（paper_trading では MockBrokerClient を想定）。
    - Engine の PID ファイル管理（data/execution.pid）および停止フラグ（data/stop_requested.flag）による安全停止処理を実装。
    - RiskManager / Reconciler / OrderManager / OrderRepository の組み立てとデフォルト設定（RiskConfig の各種しきい値、rate_limit、circuit breaker 等）。

  - run_monitoring.py を追加。
    - SystemMonitor を定期実行するポーリングループ。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満や不正値は無効扱い）。
    - 監視は KABUSYS_ENV にかかわらず production の sqlite_path（data/monitoring.db 等）を使用して監視データを記録。
    - プロセス優先度を起動時に "high" に設定する処理を組み込み（set_process_priority を利用）。

- 設定・環境管理
  - config.py を追加。
    - .env ファイルの自動読み込み機構（プロジェクトルートを .git または pyproject.toml から探索）を実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパースは export プレフィックス・クォート・インラインコメント等に対応する堅牢な実装。
    - Settings クラスを提供。J-Quants / kabuAPI / LINE / DB / 監視しきい値 / ログ等の設定プロパティを一元管理。
    - PAPER_FILL_MODE のバリデーション（有効値: instant, partial, never, reject）を実装。
    - KABUSYS_ENV, LOG_LEVEL 等の妥当性チェックとヘルパーメソッド（is_live / is_paper / is_dev）を提供。

  - config_setup.py を追加（対話式ウィザード）
    - `.env` の作成・更新を対話的に支援する CLI。
    - 各設定項目の説明、デフォルト、シークレット入力サポートを実装。
    - 保存時に .env をテンプレート形式で出力（コミットしない旨の注意書き付き）。

  - validate_config.py を追加（設定検証 CLI）
    - .env と config/*.yaml の基本的な妥当性チェックを行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリチェック、YAML パース（PyYAML が無ければ警告）などを実装。
    - `--strict` オプションで警告も失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py を追加。
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定する共通ユーティリティ。
    - ログレベル・ログディレクトリの解決順序（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしコンソールのみで継続。
  - utils/process_priority.py を追加。
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定する関数 set_process_priority を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity も提供。
    - 権限不足や未対応 OS に対する安全なフォールバックとログ出力を実装。

- Portfolio 構築ライブラリ
  - portfolio/portfolio_builder.py を追加。
    - BUY シグナルの候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装。
  - portfolio/risk_adjustment.py を追加。
    - セクター集中制限をかける apply_sector_cap、マーケットレジームに応じた資金乗数 calc_regime_multiplier を実装。
    - 未知レジームに対するフォールバックやログ出力を追加。
  - portfolio/position_sizing.py を追加。
    - position size（発注株数）算出ロジックを実装。
    - allocation_method に "risk_based"/"equal"/"score" をサポートし、lot_size による丸め、max_position_pct や max_utilization、cost_buffer を考慮した aggregate キャップとスケーリング処理を含む。
    - 価格欠損時のスキップやログ出力、スケーリング後の端数配分アルゴリズムを実装。

- モニタリング・検証ツール
  - monitoring DB 初期化のヘルパー（init_monitoring_db）を参照して各スクリプトから呼び出し。
  - tools/paper_verification_report.py を追加。
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）から統計を抽出し、稼働率・注文成功率・送信率・P95 レイテンシ等を計算して人間向けレポートを出力。
    - デフォルトの合格閾値（稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200ms）を設定し、PASS/FAIL を判定。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

- research/factor_research.py（ファクター計算の骨組み）
  - モメンタム等のファクター計算（calc_momentum）や定数群を追加。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。※ファイル末尾で未完（途中）な実装箇所あり。

### 変更
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を設定し、主要サブパッケージ名を __all__ に列挙。

### 注意事項 / ドキュメント的な記載（Breaking / Important）
- run_monitoring の挙動
  - 監視プロセスは KABUSYS_ENV にかかわらず Settings.sqlite_path（監視 DB 想定）を使用して監視データを書き込みます。必要に応じて設定を確認してください。
- .env と自動ロード
  - プロジェクトルートの検出は .git または pyproject.toml を基準に行います。配布後や特殊配置では自動ロードがスキップされることがあります。
  - 自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PAPER_TRADING 分離
  - ペーパートレード時の DB は本番 DB と切り離されます（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。紙上検証と実運用のデータ混在を避けるための設計です。
- 権限・環境依存の操作
  - プロセス優先度設定・CPU affinity・ログディレクトリ作成など一部操作は権限不足や OS により失敗する可能性があります。失敗時は警告を出して処理を継続する安全設計です。

### 既知の未実装 / TODO
- research/factor_research.calc_momentum の実装がファイル末尾で途中（start_da で中断）になっています。ファクター計算の完全実装は今後のタスク。
- position_sizing の lot_size を銘柄別に対応する拡張（stocks マスタ化）などの改善予定。
- ロギングまわりの更なる微調整・テストカバレッジの拡充。

---

今後のリリースではテスト、ドキュメント、ファクター計算の完成、ExecutionEngine の詳細な挙動に関する拡張・安定化を予定しています。