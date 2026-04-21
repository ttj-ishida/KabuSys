# Changelog

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

※ この CHANGELOG はコードベースから実装内容を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-21
初回リリース。

### Added
- 基本アプリケーションパッケージを追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）
    - .env 自動読み込み機能（プロジェクトルートの検出: .git または pyproject.toml）
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - 詳細なプロパティ群: J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境種別・ログレベル判定など
    - 環境値の検証（有効値チェックや必須変数の要求）
  - settings インスタンスのエクスポート

- 対話式設定ウィザード CLI（src/kabusys/config_setup.py）
  - .env の初期作成・更新をガイドするウィザードを提供
  - 秘匿値のマスク表示、選択肢サポート、既存 .env の読み込み・再利用
  - .env 書き出しテンプレートを整備

- 設定検証 CLI（src/kabusys/validate_config.py）
  - .env と config/*.yaml を起動前に検証
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パス親ディレクトリ確認
  - PyYAML が無い場合は YAML 検証をスキップし警告を出力
  - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定、Kill Flag の自動クリア設定等）
  - --strict モードで警告を FAIL 扱いにできる

- 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
  - ExecutionEngine 起動フロー
  - paper_trading 環境時は専用の SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と分離
  - BrokerClientFactory によるブローカークライアント生成（Mock / 本番の分岐を想定）
  - OrderRepository, OrderManager, RiskManager, Reconciler の組み立て
  - RiskManager のデフォルト設定を実装（max_position_pct、max_utilization、rate_limit 等）
  - Engine を別スレッドで実行し、 data/stop_requested.flag による停止監視
  - PID ファイル管理（data/execution.pid）

- 監視起動スクリプト（src/kabusys/run_monitoring.py）
  - SystemMonitor のポーリングループ開始スクリプト
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視テーブルを初期化
  - data/stop_requested.flag による停止検知

- ロギングユーティリティ（src/kabusys/utils/logging_setup.py）
  - setup_logging 関数を提供
  - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app>.log）を設定
  - LOG_LEVEL / LOG_DIR の優先解決、既存ハンドラの一度クリア処理
  - ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみ継続

- プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
  - set_process_priority(level) で Windows / POSIX を吸収して優先度設定
  - set_cpu_affinity(cpu_count) によるコア固定（未サポート時や権限不足は警告でスキップ）
  - psutil を利用し、アクセス権限や非対応 OS に対する堅牢なハンドリング

- ポートフォリオ構築ライブラリ（src/kabusys/portfolio/）
  - portfolio_builder.py
    - select_candidates(): スコア降順・タイブレークロジック
    - calc_equal_weights(), calc_score_weights(): 等金額・スコア加重配分（スコアが全て 0 の場合のフォールバック）
  - risk_adjustment.py
    - apply_sector_cap(): 同一セクター集中制限（売却予定銘柄除外、"unknown" セクターは除外対象外）
    - calc_regime_multiplier(): market regime に基づく投下資金乗数（bull/neutral/bear のマッピング）
  - position_sizing.py
    - calc_position_sizes(): risk_based / equal / score の allocation_method をサポート
    - lot_size による丸め、max_position_pct・max_utilization による上限、aggregate cap 時のスケールダウンロジック
    - cost_buffer を考慮した保守的コスト見積り、残余キャッシュでの再配分（fractional remainder による安定的配分）

- ポートフォリオモジュールのパブリックエクスポート（src/kabusys/portfolio/__init__.py）

- 研究用ファクター計算モジュール（src/kabusys/research/factor_research.py）
  - Momentum / MA200 / ATR / Liquidity 等のファクター計算を想定した設計
  - DuckDB 接続を受け取り SQL/Python 混在で計算する方針
  - （実装途中でファイルが一部まで存在）

- ツール: Paper Trading 検証レポート（src/kabusys/tools/paper_verification_report.py）
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から統計を集計してレポート生成
  - 稼働率 / 注文成功率 / 送信率 / レイテンシ（avg/max/P95） / リスク却下数 等を算出
  - PASS/FAIL の判定閾値を定義（稼働率 99% など）
  - 日付フィルタ、P95 計算、欠損時の N/A 表示などを実装

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数の秘匿値はウィザードでマスク表示。`.env` を Git にコミットしない旨を README/ヘッダに明記。

---

開発・運用に関する補足（実装から推測）
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定するため、権限不足時は警告が出て継続する設計。
- 監視・実行は stop flag（data/stop_requested.flag）により外部から安全に停止可能。
- paper_trading 環境は本番環境と DB を完全に分離する想定（paper_trading 用 SQLite を使用）。
- ロギングやファイル作成処理は失敗しても致命的にならないようにフォールバックを実装（堅牢性重視）。

もし特定の変更点（コミット単位や追加のリリース番号）を反映したい場合は、該当の差分や目的のバージョン情報を教えてください。