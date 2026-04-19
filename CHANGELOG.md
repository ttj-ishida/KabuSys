# Keep a Changelog

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  

## [0.1.0] - 2026-04-19

概要: 初回公開リリース。自動売買システム KabuSys のコアユーティリティ、実行/監視ランナー、環境設定ツール、ポートフォリオ構築ロジック、Paper Trading 検証ツールなどを含みます。

### 追加 (Added)
- 基本パッケージ情報
  - src/kabusys/__init__.py にバージョン情報を追加 (0.1.0)。

- 環境・設定関連
  - 環境変数自動読み込み機能（.env, .env.local）を実装（src/kabusys/config.py）。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env の行パース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート）。
    - OS 環境変数を保護するための上書き制御を実装。
  - Settings クラスを実装し、アプリケーション設定を型付きプロパティで取得可能に（DB パス、API トークン、各種閾値、環境判定など）。

- 環境設定支援 CLI
  - 対話式ウィザードで .env を作成/更新する CLI を追加（src/kabusys/config_setup.py）。
    - シークレット項目のマスク表示、選択肢サポート、保存前確認。
    - .env の読み書きロジック実装。

- 設定検証 CLI
  - .env と config/*.yaml の基本検証を行う CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV の検証、ログレベル検証、DB パスの親ディレクトリ確認、YAML パース（PyYAML が無ければスキップ）、本番環境向けガード（LINE 設定、KILL_FLAG_CLEAR_ON_START）等。
    - --strict オプションで警告を失敗扱いにできる。

- 実行 / 監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は MockBroker を使用し、paper_trading 用 SQLite を利用して本番 DB と分離。
    - プロセス優先度を起動時に "high" に設定。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理。
    - Engine を別スレッドで実行し、停止フラグ検知で安全停止。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様（監視データの一元化）。
    - SystemMonitor 呼び出しの例外を捕捉してループ継続。

- ロギング・プロセス管理ユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテーション付きファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ作成失敗やファイルハンドラ作成失敗をフォールバックして安全に継続。
    - ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分吸収（psutil を利用）。失敗時は警告出力してスキップ。
    - set_process_priority, set_cpu_affinity を提供。

- ポートフォリオ構築ライブラリ（完全に純粋関数、DBアクセスなし）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順・同点タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計 0 の場合はフォールバック）を実装。
  - セクター集中・レジーム調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター上限を超える場合に候補を除外、unknown セクターは除外しない）を実装。
    - calc_regime_multiplier（レジーム毎の投資乗数、未定義レジームは警告してフォールバック）。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method として "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、ポジション上限、aggregate cap（利用可能現金を超えた場合のスケーリングと残差処理）を実装。
    - cost_buffer を考慮した保守的見積り。
    - 将来的な拡張点（銘柄別 lot_size）に関する TODO コメントを追加。

- Paper Trading 検証ツール
  - Paper Trading の検証レポートを生成するスクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - システム稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計・判定（PASS/FAIL）。
    - デフォルト閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）。
    - 日付フィルタ（--from/--to）、DB パス指定（--db）をサポート。PAPER_TRADING_SQLITE_PATH 環境変数にも対応。

- 研究用ファクター計算（骨格）
  - DuckDB を用いたファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - モメンタム／MA／ATR 等の算出方針と定数が定義されている（calc_momentum の実装途中まで含む）。

### 変更 (Changed)
- .env 自動ロードの挙動を明確化（src/kabusys/config.py）
  - ロード順: OS 環境変数 > .env.local > .env
  - OS 環境変数は protected として .env/.env.local の上書きを防止
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト等で利用）

- ログ出力先の方針
  - コンソールログを stdout に統一（cron/task scheduler のリダイレクト運用を想定）。（src/kabusys/utils/logging_setup.py）

- 実行コンポーネントの安全性・分離
  - ExecutionEngine は paper_trading 環境で専用の SQLite（デフォルト data/paper_trading.db）を使うことで本番 DB と完全分離（src/kabusys/run_execution.py）。
  - 監視は常に本番の sqlite_path を参照（監視データの中央管理を優先）（src/kabusys/run_monitoring.py）。
  - init_monitoring_db は冪等に監視テーブルを保証する呼び出しとして使用。

### 修正 (Fixed)
- 環境変数の数値パース保護
  - MONITOR_POLL_INTERVAL の不正値（0 や負、非数）に対して警告を出しデフォルトにフォールバックするようにした（src/kabusys/run_monitoring.py）。
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープや export プレフィックス、インラインコメントの扱いなどを正しく処理するよう改善（src/kabusys/config.py）。
- ログハンドラ二重登録回避
  - setup_logging が既存ハンドラを一度クリアしてから再設定するようにした（重複出力防止、src/kabusys/utils/logging_setup.py）。
- プロセス優先度設定の例外対応
  - psutil の AccessDenied 等で失敗しても安全にフォールバックし警告を出すように（src/kabusys/utils/process_priority.py）。

### 注意・既知の制約 (Known issues / Notes)
- risk_adjustment.apply_sector_cap の価格欠損時の挙動について注記あり（価格が 0.0 の場合、エクスポージャーが過少見積りされる可能性）。将来的に前日終値などでのフォールバックを検討する旨コメントあり。
- position_sizing は現状全銘柄共通の lot_size を仮定しており、将来的に銘柄別 lot_size をサポートする TODO がある。
- research/factor_research モジュールは骨格実装であり、いくつかの関数（calc_momentum 等）は実装途中でファイルが切れている。追加実装・テストが必要。
- validate_config の YAML 検証は PyYAML 非インストール環境ではスキップされる（警告を出力）。

### セキュリティ (Security)
- 機密情報（J-Quants トークン、kabu API パスワード等）は .env に記載する設計だが、.env を Git にコミットしない旨を明記。config_setup で生成される .env にも注意喚起を追加。

---

（今後のリリースでは、各モジュールのユニットテスト追加、research モジュールの完成、戦略実行フロー関連の細かな拡張および config の更なる検証強化を予定しています。）