# Keep a Changelog
すべての重要な変更はこのファイルに記録します。  
フォーマット: https://keepachangelog.com/ (日本語要約)

## [Unreleased]
- なし

## [0.1.0] - 2026-04-24
最初のリリース。自動売買システム KabuSys のコア機能とユーティリティ群を追加。

### 追加 (Added)
- 基本構成・設定
  - Settings クラスによる環境変数ベースの設定管理を追加（src/kabusys/config.py）。
  - .env の自動読み込み機能を実装（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - .env の柔軟なパース（export プレフィックス、シングル/ダブルクォート、インラインコメント等に対応）。
  - config_setup: 対話式の .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
  - validate_config: 起動前チェック CLI（必須環境変数、パス、YAML の存在・パースなど）を追加（src/kabusys/validate_config.py）。

- 実行・監視プロセス
  - run_execution: ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（モック含む）を想定。
    - PID ファイルと停止フラグ対応を実装。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。無効値はデフォルト（60秒）にフォールバック。
    - 監視は環境にかかわらず production sqlite_path を使用する設計。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み付け: select_candidates, calc_equal_weights, calc_score_weights（src/kabusys/portfolio/portfolio_builder.py）。
  - セクター集中制限・レジーム乗数: apply_sector_cap, calc_regime_multiplier（src/kabusys/portfolio/risk_adjustment.py）。
  - ポジションサイジング: calc_position_sizes（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score の配分方式、lot_size 単位での丸め、投資合計が利用可能現金を超える場合のスケーリングロジックを実装。
    - cost_buffer（スリッページ・手数料見積り）を考慮した保守的見積りをサポート。

- ユーティリティ
  - ログ設定ユーティリティ: setup_logging（ストリーム stdout と日次ローテーションファイルハンドラ）を追加（src/kabusys/utils/logging_setup.py）。
    - LOG_DIR 指定や作成失敗時のフォールバック（ファイル出力を無効化してコンソールのみ出力）。
  - プロセス優先度設定: set_process_priority / set_cpu_affinity（プラットフォーム差分を吸収、psutil 利用）（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差を吸収し、権限不足や未対応 OS の場合は警告ログでスキップ。

- 監視・計測・レポート
  - 監視 DB 初期化ユーティリティ（init_monitoring_db）の呼び出しを各起動スクリプトで行い、監視テーブルの存在を保証。
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率、注文成立率（Fill rate）、送信率、P95 レイテンシなどの指標を集計・判定（閾値付き PASS/FAIL レポート）。
    - 日付フィルタ、DB パス指定オプションをサポート。

- リサーチ
  - ファクター計算モジュールの骨子を追加（src/kabusys/research/factor_research.py）。
    - Momentum、Value、Volatility、Liquidity 等の設計方針と定数を定義。DuckDB を用いた計算を想定。

- パッケージ情報
  - パッケージ初期バージョンを設定: __version__ = "0.1.0"（src/kabusys/__init__.py）。

### 変更 (Changed)
- ログ出力設計
  - すべての起動スクリプトで統一的に setup_logging を呼び出すことでログ管理を一元化。
  - StreamHandler は stdout を使用（cron 等で stdout/stderr を一本化する運用を考慮）。

- データベース取り扱い
  - run_execution は paper_trading モードで専用 SQLite を使い、本番データと完全分離するように設計。
  - run_monitoring は環境に依存せず本番 sqlite_path を使用して監視データの一元化を図る。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - .env 行パースにおいて export プレフィックス、クォート内のエスケープ、インラインコメント規則などに対応し、不正な行はスキップするよう改善。
- 起動時のディレクトリ/ファイル作成に失敗した場合のフォールバック処理を追加（ログディレクトリ作成失敗時はファイルハンドラを無効化して継続）。
- process_priority の実行失敗（権限不足等）時に例外を上げず警告でスキップするようにして起動失敗を防止。

### 注意事項 / 既知の制約 (Known issues)
- research/factor_research.py は計算ロジックの骨子まで実装されているが、一部実装が未完（ファイル末尾が途中で切れている状態）であり、詳細なファクター計算の完全な動作確認が必要。
- position_sizing の price フォールバック（価格欠損時の扱い）は現状簡易実装（価格が欠損するとエクスポージャーが過少見積りされる可能性がある）であり、前日終値や取得原価などのフォールバック実装がコメントで示唆されている。
- run_monitoring は監視対象 DB に production sqlite_path を使用するため、テスト環境で監視を動かす場合は注意が必要（強制的に本番 DB に記録する設計）。
- set_cpu_affinity / set_process_priority はプラットフォーム依存の挙動や権限により完全に無効化される場合がある（警告でログに記録）。

### セキュリティ (Security)
- .env は生成スクリプトで明示的に「絶対に Git にコミットしないこと」を注意書きしており、機密情報（トークン・パスワード）は secret フラグでマスクして表示する実装。
- 本番環境（KABUSYS_ENV=live）での設定警告や LINE 通知設定の未設定チェックを validate_config で行うようにしている。

---

開発・運用上のドキュメント（config/.env の作成→validate→起動の流れ）を整備すると導入がスムーズになります。必要であれば CHANGELOG に含める詳細なマイグレーション手順やサンプル .env を作成します。