# Changelog

すべての重要な変更をここに記録します。本ファイルは "Keep a Changelog" の形式に従います。

- ルール: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（次回リリースでの変更をここに記載してください）

---

## [0.1.0] - 2026-04-20

初版リリース。本リポジトリに含まれる主要機能と実装上の注意点をまとめます。

### 追加 (Added)
- 環境設定／起動系
  - Settings クラスを追加（src/kabusys/config.py）。.env / .env.local 自動読み込み、環境変数の型変換・検証（KABUSYS_ENV, LOG_LEVEL 等）を提供。
  - .env のパース機能を強化（引用符・エスケープ、`export KEY=val` 形式、インラインコメント処理など）。
  - プロジェクトルート自動検出機能を追加（.git または pyproject.toml を探索）。
  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）。対話式で .env を生成・更新可能。シークレット入力・選択肢・デフォルト値をサポート。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パス、config/*.yaml の存在とパース検証（PyYAML がある場合）などをチェック。`--strict` オプションで警告を失敗扱いにできる。

- 実行／監視ランナー
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用し本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、スレッドで実行。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を利用した安全な起動・停止制御を実装。
  - SystemMonitor ポーリングランナーを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視 DB 初期化（init_monitoring_db）と DuckDB 接続を行い、停止フラグでループ終了。
    - プロセス優先度の設定（High）を起動時に実行。

- ロギング／プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler（標準出力）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - 既存ハンドラのクリア、LOG_LEVEL / LOG_DIR による設定解決、ログディレクトリ作成失敗時のフォールバックを実装。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して nice/priority を設定。psutil を用いたアクセス拒否等の例外は警告ログで無視。
    - CPU affinity を最初の N コアに固定する関数も提供。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレークに signal_rank）
    - calc_equal_weights / calc_score_weights（スコア全ゼロ時のフォールバック）
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮しセクター集中を除外）
    - calc_regime_multiplier（bull/neutral/bear に対する乗数。未知レジームは警告とフォールバック）
  - 株数決定・丸め・集約上限処理（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート
    - 単元（lot_size）丸め、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap スケーリングと残差処理

- 解析・検証ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成功率（fill_rate）、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）を SQLite から集計してレポート出力。
    - 合格判定の閾値（稼働率 99% 等）を定義し PASS/FAIL を出力。日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

- その他
  - パッケージバージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - research モジュールのファクター計算（momentum 等）の土台を追加（src/kabusys/research/factor_research.py、未完の実装を含む）。

### 変更 (Changed)
- 設定の自動読み込み動作を明確化
  - デフォルトで .env/.env.local を自動読み込みするが、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。

- ログ出力先として stdout を明示的に使用
  - StreamHandler は stderr ではなく stdout を使用する設計に変更（cron 等で stdout/stderr をまとめてリダイレクトする運用を想定）。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - クォート内のバックスラッシュエスケープやコメント処理の改善により .env の誤読を削減。

- DB 周りの防御的処理
  - report / monitoring スクリプトで DB が存在しない／テーブルがない場合でも例外でクラッシュしないよう既定値や try/except を追加。

### 注意点 / 既知の制約 (Known issues / Notes)
- research/factor_research.py は一部実装が未完（ファイル末尾で切れている）。本機能を利用する前に実装の完了が必要。
- position_sizing や risk_adjustment は単元株（lot_size）が全銘柄共通で 100 に固定されている。将来的には銘柄別 lot_size サポートを検討。
- process_priority では権限不足（psutil.AccessDenied）時に設定できないケースがあり、その場合は警告を出してスキップする仕様。
- config_setup が生成する .env は絶対にコミットしないこと（ヘッダに注意喚起あり）。

---

（以降のリリースでは、Unreleased セクションに変更を記載し、リリース時にバージョンと日付を付与してください。）