# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

リリース日付はコードから推測できる情報に基づき設定しています。

## [0.1.0] - 2026-04-18 (初回公開)

### Added
- プロジェクト初期実装を追加。
  - パッケージメタ情報
    - `kabusys.__version__ = "0.1.0"` を設定。
  - 環境設定・ロード
    - `.env` ファイル自動読み込み機能を追加（プロジェクトルートを `.git` または `pyproject.toml` で検出）。
    - 独自の `.env` パーサを実装し、クォートやエスケープ、`export KEY=...` 形式、インラインコメントへの対応を実装（`kabusys.config`）。
    - 環境変数の自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 設定取得用 `Settings` クラスを提供（J-Quants / kabuステーション / DB / モニタリング等のプロパティを提供）。
    - Paper Trading 用の設定（`PAPER_FILL_MODE`、`PAPER_TRADING_SQLITE_PATH`）をサポート。
  - 設定ウィザード CLI
    - `.env` を対話的に作成・更新する `kabusys.config_setup` を実装。
    - デフォルト値、選択肢、シークレット入力の扱い、保存確認を実装。
  - 設定検証 CLI
    - 起動前に `.env` と `config/*.yaml` を検証する `kabusys.validate_config` を実装。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベル確認、DB パス親ディレクトリ確認、YAML パース（PyYAML 未導入時は警告）などを実行。
    - `--strict` オプションで警告をエラー扱いにする機能を追加。
  - 実行系スクリプト
    - ExecutionEngine 起動スクリプト `run_execution.py` を追加。
      - `KABUSYS_ENV=paper_trading` の場合は Paper Trading 用 DB（`data/paper_trading.db` デフォルト）を使用して本番DBから分離。
      - ブローカークライアント生成（factory 経由）、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止フローを実装。
      - 実行中の停止制御に `data/stop_requested.flag` を利用し、`data/execution.pid` に PID を書く仕組みをサポート（Engine 側で pid_file を使用）。
    - Monitoring 起動スクリプト `run_monitoring.py` を追加。
      - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト：60秒、負値など無効値はデフォルトにフォールバック）。
      - Monitoring は環境にかかわらず本番の `sqlite_path` を使用する旨のポリシーを明示。
      - 停止フラグ `data/stop_requested.flag` を検知してループを終了。
  - 監視 DB 初期化
    - `init_monitoring_db`（監視テーブル保証）を参照して各スクリプトが DB を確実に準備する流れを追加。
  - ログ設定ユーティリティ
    - `kabusys.utils.logging_setup.setup_logging` を追加。
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30日保持）をルートロガーへ設定。
      - ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決順を実装。
  - プロセス優先度 / CPU affinity ユーティリティ
    - `kabusys.utils.process_priority` を追加。
      - Windows / POSIX の差を吸収して `set_process_priority(level)`（high/normal/low）を実装。
      - `set_cpu_affinity(cpu_count)` でプロセスを最初の N コアにピン留めする機能を追加。
      - 権限不足や未対応 OS の場合は警告を出してスキップする安全設計。
  - ポートフォリオ構築ライブラリ
    - `kabusys.portfolio` モジュールを追加（純粋関数群）。
      - 候補選定: `select_candidates`（スコア降順・タイブレークロジック）。
      - 重み計算: `calc_equal_weights`, `calc_score_weights`（全スコア 0 の場合は等分配にフォールバック）。
      - リスク調整: `apply_sector_cap`（セクター集中上限）、`calc_regime_multiplier`（market regime に応じた乗数: bull/neutral/bear）。
      - ポジションサイズ算出: `calc_position_sizes`（risk_based / equal / score の割当、lot 単位丸め、aggregate cap スケーリング、cost_buffer 対応）。
  - リサーチ / ファクター計算（骨組み）
    - `kabusys.research.factor_research` の骨格を追加（モメンタム・ATR・出来高等の計算方針・定数を定義）。一部関数（例: calc_momentum）が実装途中である旨の痕跡あり。
  - Paper Trading 検証ツール
    - `kabusys.tools.paper_verification_report` を追加。
      - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計して PASS/FAIL 判定付きレポートを生成。
      - コマンドライン引数で期間指定および DB パス指定をサポート。
      - 判定閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
  - DB 統合
    - SQLite（監視/ペーパートレード）と DuckDB（分析用）を併用する設計を採用。多くのコンポーネントが両者のパスを `Settings` 経由で取得する。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- （初版のため該当なし）

## 既知の注意点 / 運用メモ
- .env ファイルは絶対にリポジトリへコミットしないこと（`config_setup` 生成時にも明記）。
- `run_monitoring` は常に本番用の `sqlite_path` を使用する設計のため、ペーパートレード DB と混同しないよう注意すること。
- `run_execution` は KABUSYS_ENV=paper_trading のときに paper DB を使用して本番 DB と分離する実装になっている。
- `KILL_FLAG_CLEAR_ON_START` が本番 (`live`) で `1` に設定されていると危険な動作（Kill Switch 自動クリア）となるため、`validate_config` は警告を出す。
- `PAPER_FILL_MODE` は `"instant"|"partial"|"never"|"reject"` のいずれかでなければ ValueError を送出するため、設定ミスに注意。
- `process_priority.set_process_priority` / `set_cpu_affinity` は権限やプラットフォームに依存するため、権限不足時には警告が出て処理は継続される（失敗は致命的にならない設計）。

## Migrating / Upgrade notes
- なし（初回リリース）

---

今後の追加予定（想定）
- research モジュール内のファクター計算の完全実装（duckdb SQL 実行部分の完成）。
- ExecutionEngine / OrderManager 等の詳細実装とテスト、ドキュメント化。
- 単体テスト・CI の導入、自動リリースワークフロー。