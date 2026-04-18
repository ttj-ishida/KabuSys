# Changelog

すべての変更は Keep a Changelog の形式に従います。
このプロジェクトはセマンティック バージョニングを採用しています。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（現在、未リリースの変更はありません。）

## [0.1.0] - 2026-04-18

初回リリース。主要な機能追加とツール群を含みます。

### 追加 (Added)
- 全体
  - パッケージ初期化とバージョン情報を追加（kabusys.__version__ = "0.1.0"）。
  - モジュール群を公開（data, strategy, execution, monitoring などの名前空間をエクスポート）。

- 設定管理 (src/kabusys/config.py)
  - .env / .env.local を自動読み込みする仕組みを実装（プロジェクトルートの検出は .git / pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを追加。
  - .env パースの堅牢化（export 形式、クォート内のエスケープ、インラインコメントの取り扱いなど）。
  - Settings クラスを実装し、各種環境変数アクセスをプロパティで提供：
    - J-Quants / kabuAPI / LINE / データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH） / ログ関連 / 監視しきい値など。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）を追加。
  - KABUSYS_ENV / LOG_LEVEL の有効値チェックを実装。

- 設定関連 CLI (src/kabusys/config_setup.py, src/kabusys/validate_config.py)
  - config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加。
    - シークレット項目はマスク表示、保存前の確認、.env の書式整形を行う。
  - validate_config: .env と config/*.yaml の起動前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML があれば実行）、本番環境向けガード（LINE 未設定や KILL_FLAG_CLEAR_ON_START の警告）を実装。
    - --strict オプションで警告を失敗扱いにできる。

- 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
  - ExecutionEngine 起動エントリを実装。
  - プロセス優先度を高く設定して起動（utils.process_priority を使用）。
  - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite を使用して本番 DB と分離（PAPER_TRADING_SQLITE_PATH/デフォルト data/paper_trading.db）。
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 時は MockBrokerClient を想定）。
  - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をスレッドで実行。
  - 停止フラグ (data/stop_requested.flag) の検出により安全に停止する仕組み。
  - PID ファイル（data/execution.pid）取り扱い。

- 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
  - SystemMonitor ポーリングループ起動エントリを実装。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効値はデフォルトにフォールバックして警告を出力。
  - 監視は環境にかかわらず本番 sqlite_path を使用する設計（監視 DB は本番の監視対象に紐づくため）。
  - 起動時にプロセス優先度を高く設定。
  - 停止フラグ (data/stop_requested.flag) による安全終了と KeyboardInterrupt のハンドリング。

- ロギングユーティリティ (src/kabusys/utils/logging_setup.py)
  - setup_logging を実装。アプリ共通のログ設定を提供。
  - stdout への StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30 日保持）を設定。
  - LOG_LEVEL / LOG_DIR の解決ルールを実装。ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみ継続。

- プロセス優先度・CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
  - cross-platform にプロセス優先度を設定する set_process_priority を実装（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
  - set_cpu_affinity によりプロセスを最初の N コアに固定する機能を追加。
  - 権限不足等の例外は警告ログに落として安全にスキップ。

- ポートフォリオ構築モジュール (src/kabusys/portfolio/*.py)
  - portfolio_builder:
    - select_candidates: スコア順で候補を選択（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights を実装（スコアが全て 0 の場合は等配分にフォールバックして警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中度を計算して超過セクターの新規候補を除外。unknown セクターは除外対象外。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を実装（bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 でフォールバックして警告。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じて発注株数を計算（risk_based / equal / score）。
    - 単元株丸め（lot_size）、1銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリングと残差再配分ロジック、cost_buffer を使った保守的コスト見積を実装。
    - 価格欠損や非正数価格はスキップするロジック、ログ出力を含む。

- Paper Trading 検証ツール (src/kabusys/tools/paper_verification_report.py)
  - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から統計を集計して検証レポートを生成する CLI を追加。
  - 稼働率（uptime）, 注文成功率(fill rate), 送信率(send rate), レイテンシ（avg/max/P95）等を算出し、閾値と照合して PASS/FAIL を判定。
  - P95 计算、日付フィルタ（--from/--to）、--db オプション／環境変数サポートを実装。
  - 閾値（デフォルト）:
    - 稼働率 >= 99.0%
    - 注文成立率 >= 90.0%
    - 送信率 >= 95.0%
    - P95 レイテンシ <= 200 ms

- 研究/ファクター計算モジュール (src/kabusys/research/factor_research.py)
  - ファクター計算の骨子を追加（モメンタム / MA200 / ATR / 流動性等を計算する予定）。
  - DuckDB 接続を受け取り prices_daily/raw_financials を参照して結果を返す設計を採用。
  - モメンタム計算の定数と関数シグネチャを用意（calc_momentum 実装開始）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / 既知の制限
- factor_research.py はモメンタム計算の実装が途中（ファイル末尾が未完である可能性）で、完全なファクターセットの計算は今後の実装が必要です。
- 一部の機能は外部モジュール（psutil, duckdb, PyYAML など）に依存します。これらがインストールされていない場合は該当機能が制限されます（validate_config は PyYAML 不在時に YAML チェックをスキップするなど安全策あり）。
- run_monitoring は監視用 DB に本番 sqlite_path を常に使用する設計のため、テスト環境で監視を分離したい場合は適切に SQLITE_PATH を設定してください。
- プロセス優先度や CPU affinity の設定は権限に依存し、権限不足時は警告ログを出してスキップします。

---

この CHANGELOG はソースコードから推測して作成しています。実際の変更履歴・コミット履歴と差異がある場合は適宜更新してください。