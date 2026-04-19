# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。慣例により「Added / Changed / Fixed / Deprecated / Removed / Security」のカテゴリーで記載しています。

なお、この CHANGELOG は提供されたコードベースから推測して作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーション骨格を追加
  - パッケージメタ情報にバージョンを追加（src/kabusys/__init__.py）。
- 環境設定・読み込み機能を追加
  - .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準として行う。
    - 読み込み優先度は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - 複雑な .env 行のパース対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理等）。
  - Settings クラスを追加し、環境変数から設定を安全に取得（必須項目の検証、各種デフォルト、Paper Trading 用 DB パスや閾値設定など）。
  - PAPER_FILL_MODE の有効値制約（instant/partial/never/reject）を実装。
- 設定ウィザード CLI を追加（src/kabusys/config_setup.py）
  - 対話的に .env を生成・更新するウィザード。
  - J-Quants / kabu API 等の必須項目、ログレベル、DB パスなど主要設定をサポート。
- 設定検証 CLI を追加（src/kabusys/validate_config.py）
  - 必須環境変数の未設定チェック、KABUSYS_ENV の妥当性、DB パスの存在可能性チェック、config/*.yaml の存在と（PyYAML がある場合は）パース検証、本番環境向けガードチェック等を実装。
  - --strict オプションで警告を失敗扱いにできる。
- 実行・監視用エントリスクリプトを追加
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - プロセス優先度を高に設定してから起動。
    - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler/ExecutionEngine の組み立てを行う。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止。
    - PID ファイル出力をサポート。
  - 監視（SystemMonitor）起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、1 秒未満や不正値はデフォルトにフォールバック）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用（監視 DB は共通の想定）。
    - 停止フラグ検知でループ終了。例外はログ出力して次ループへ継続。
- ロギングユーティリティを追加（src/kabusys/utils/logging_setup.py）
  - setup_logging(app_name, log_dir, level) を提供。
  - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続するフェールセーフ。
  - 既存ハンドラの二重登録防止のため一度クリアしてから再設定。
- プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) による Windows/Linux/Mac の差分吸収（psutil ベース）。
  - set_cpu_affinity(cpu_count) によるプロセスの CPU ピニング機能。
  - 権限不足や未サポート OS では警告ログを出して安全にスキップ。
- ポートフォリオ構築関連の純関数群を追加（src/kabusys/portfolio/*）
  - 候補選定: select_candidates（score 降順、同点は signal_rank でタイブレーク）。
  - 重み付け: calc_equal_weights, calc_score_weights（スコア合計 0 の場合は等分配にフォールバックして警告）。
  - セクター集中制限: apply_sector_cap（既存保有のセクター比率が閾値を超えるセクターの新規候補を除外。unknown セクターは適用除外）。
  - レジーム乗数: calc_regime_multiplier（bull/neutral/bear をマッピング、未知の値は 1.0 でフォールバックし警告）。
  - ポジションサイズ計算: calc_position_sizes（risk_based / equal / score の割当方式、lot_size 単位丸め、aggregate cap によるスケールダウンと残余配分ロジック、cost_buffer による保守的見積）。
- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
  - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計してレポート出力。
  - デフォルト閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
  - 日付フィルタ（--from / --to）と DB パス指定（--db / 環境変数）をサポート。
  - P95 計算の実装とデータ不足時の N/A 表示。

### Changed
- ログ出力の標準出力先を stderr ではなく stdout に変更（setup_logging）。cron/Task Scheduler 等で stdout/stderr を一元化しやすくするため。
- .env のパース仕様を堅牢化（クォート内エスケープ、コメントルールの調整など）。これにより複雑な値やコメント付き行にも対応。
- 設定検証の挙動改善: PyYAML がない場合は YAML 検証をスキップして警告を出す。

### Fixed
- 実行/監視スクリプトでの DB 接続後の初期化処理を明確化（init_monitoring_db を呼んで監視テーブル存在を保証）。これにより初回起動時のテーブル未作成によるエラーを低減。

### Deprecated
- なし

### Removed
- なし

### Security
- Secrets（J-Quants トークン / kabu API パスワード 等）は .env に保存する想定。config_setup の出力ヘッダで .env を Git にコミットしないよう明示。

### Notes / Known limitations
- apply_sector_cap の注記: price_map に価格が欠損（0.0）だとエクスポージャーが過小見積りされ除外が行われない可能性がある（該当箇所に TODO コメントあり）。将来的に前日終値や取得原価等のフォールバック価格導入を検討。
- calc_regime_multiplier は未知のレジームを 1.0（Bull 相当）でフォールバックするが、generate_signals 側の仕様により Bear では BUY シグナルが発生しない前提がある（コード内コメント参照）。
- process_priority / set_cpu_affinity は権限不足や未サポート環境ではスキップされ、警告ログにより通知される。
- Paper Trading と本番 DB は分離される設計だが、運用時は環境変数・パス設定を慎重に確認すること（validate_config の live ガード参照）。

--- 

以上がコードベースから推測して作成した CHANGELOG.md です。必要であればカテゴリの追加・文言の修正や、リリース日・バージョンの調整を行います。