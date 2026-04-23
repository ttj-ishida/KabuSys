# Changelog

すべての変更は Keep a Changelog の形式に準拠して記載しています。日付・内容はソースコードから推測して記載しています。

## [0.1.0] - 2026-04-23

### Added
- 基本リリースとして初期機能を追加
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。
- 実行用エントリポイント
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動するランナーを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用するよう分離（本番 DB とは完全に分離）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止処理を実装。
    - 実行中の PID を data/execution.pid に書き出す仕組みを想定（pid_file）。
    - Thread を使ったエンジン実行ループと停止監視。
- 監視用エントリポイント
  - src/kabusys/run_monitoring.py
    - SystemMonitor を用いたポーリング監視ループを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計（意図的な動作）。
- 設定管理・初期化ツール
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルートを .git / pyproject.toml で検出）を実装。
    - .env/.env.local の読み込み順と上書き・保護（protected）仕様を実装。
    - 環境変数のパースが堅牢化（export プレフィックス、クォート内のエスケープ、インラインコメント処理など）。
    - Settings クラスを実装し、各種設定プロパティ（DB パス、LINE トークン、KABUSYS_ENV 検証、paper_trading 用設定、監視しきい値など）を提供。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加（秘密値はマスク、デフォルト・選択肢対応）。
- 設定検証ツール
  - src/kabusys/validate_config.py
    - 起動前に .env と config/*.yaml の基本チェックを行う CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML の存在/パース検証（PyYAML が無ければ警告）を実装。
    - `--strict` オプションで警告を FAIL 扱いにするモードを追加。
    - live 環境用の追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の危険性警告等）。
- ロギング・プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション・30日保持）を設定する共通ユーティリティを追加。
    - ログディレクトリ作成失敗時はファイルロギングをスキップしてコンソールのみで継続する堅牢な実装。
    - ログレベル・ログディレクトリの解決ロジック（引数 > 環境変数 > デフォルト）。
  - src/kabusys/utils/process_priority.py
    - プロセス優先度（high/normal/low）をクロスプラットフォームで設定するユーティリティを追加（Windows/Linux/macOS を考慮、psutil 使用）。
    - CPU アフィニティを最初の N コアに固定する set_cpu_affinity() を追加。
    - 権限不足や未対応環境では警告を出して安全にフォールバックする実装。
- ポートフォリオ構築ライブラリ
  - src/kabusys/portfolio/
    - portfolio_builder.py
      - シグナル選定（score 降順、同点は signal_rank でタイブレーク）、等金額配分、スコア加重配分（スコア全て 0 の場合は等配分にフォールバック）を実装。
    - risk_adjustment.py
      - セクター集中上限チェック（apply_sector_cap）を実装。既存ポジションのセクター別エクスポージャ算出・超過セクター除外ロジック。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear を想定、未知レジームは 1.0 にフォールバック）。
    - position_sizing.py
      - allocation_method（"risk_based"/"equal"/"score"）に基づく株数算出ロジックを実装。
      - 単元株（lot_size）丸め、ポジション上限・利用率上限、コストバッファ考慮、aggregate cap によるスケーリングと残差補正の実装。
- 研究・ファクター計算基盤（部分実装）
  - src/kabusys/research/factor_research.py
    - モメンタム／MA200乖離／ATR／流動性等のファクター計算を行う設計で、DuckDB 接続を受けて prices_daily / raw_financials を参照する実装を開始（calc_momentum 等の関数設計と定数を定義）。
- ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - SQLite（paper_trading DB）から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - CLI 引数 `--from` / `--to` / `--db` をサポート。環境変数 PAPER_TRADING_SQLITE_PATH による DB 指定も可能。
- パッケージ初期化
  - src/kabusys/__init__.py に公開モジュール一覧とバージョンを追加。

### Changed
- アプリケーション全体のログ設定を centralize（setup_logging を全起動スクリプトで利用することを想定）。
- .env 読み込みの挙動を厳密化:
  - .env/.env.local の読み込み順と override のルールを明確化（OS 環境変数を保護）。
  - export プレフィックス・クォート・コメントをサポートするよう改善。

### Fixed
- run_monitoring と run_execution における DB 初期化/接続の堅牢化（monitoring 用テーブルの初期化を保証する init_monitoring_db 呼び出しを含む）。
- ログディレクトリ作成失敗時にアプリケーションが停止しないように修正（ファイルハンドラ作成失敗時はコンソール出力のみで継続）。

### Notes / Remarks
- run_monitoring は設計上「監視は常に本番 sqlite_path を使用する」振る舞いになっています。意図的かどうかは運用方針に依存するため導入時に注意してください（テスト環境で別 DB を使いたい場合はコード/設定の調整が必要）。
- factor_research.py はファイル末尾が途中で切れている（calc_momentum の実装が未表示）。実装の続き・テスト整備が必要と推測されます。
- 実運用では psutil を使ったプロセス優先度設定やファイル書き込み（PID/ログ等）は権限やプラットフォーム依存のため、デプロイ環境での動作確認を推奨します。
- config_setup の対話ウィザードは秘密項目をマスク表示しますが、.env ファイルは平文で保存されるため .gitignore 等での管理を厳重に行ってください。

---

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノート作成時はコミット履歴や issue/PR 情報に基づく補足を加えることを推奨します。）