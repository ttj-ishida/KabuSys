# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

NOTE: コードベースから推測して作成しています。実際のリリースノート作成時は差分やコミット履歴に基づいて調整してください。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-23

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装・追加しました。

### Added
- 基本メタ情報
  - パッケージバージョンを追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 設定管理
  - Settings クラス（src/kabusys/config.py）
    - 環境変数取得やバリデーションを集中管理（KABUSYS_ENV, LOG_LEVEL, DB パス, 各種 API キー等）。
    - .env 自動ロード機能（.env / .env.local）をプロジェクトルート検出に基づいて実装。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - PAPER_FILL_MODE の妥当性チェック、paper_trading 用 SQLite パスなどペーパートレード向け設定を追加。
  - 環境設定ウィザード CLI（src/kabusys/config_setup.py）
    - .env を対話式に生成・更新するウィザード。既存 .env 読み込み／シークレットマスク表示／保存機能を備える。
  - 設定検証ツール（src/kabusys/validate_config.py）
    - 必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在や Yaml パース（PyYAML が利用可能な場合）などをチェックする CLI。--strict オプションをサポート。

- 実行系起動スクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - 起動時にプロセス優先度を調整、paper_trading 環境では MockBroker を利用して paper_trading 用 DB に分離して記録。停止フラグ（data/stop_requested.flag）と PID ファイルの取り扱いを実装。
  - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）
    - 監視ループ（デフォルト 60 秒、MONITOR_POLL_INTERVAL で上書き可）、停止フラグ検知、監視 DB 初期化（init_monitoring_db）、DuckDB 接続などを実装。Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。

- 監視・レポート
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード用 SQLite から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計して PASS/FAIL を判定する CLI。日付範囲フィルタ、DB パスの引数/環境変数サポート。明確な閾値と判定ロジックを実装。

- ポートフォリオ構築モジュール（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレーク処理）、calc_equal_weights、calc_score_weights（全スコア 0 の場合のフォールバック）を提供。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（セクター集中制限、売却予定銘柄の除外、"unknown" セクターの扱い）を実装。
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数。bull/neutral/bear をサポート、未知レジームは警告してフォールバック）。
  - ポジションサイジング（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes：risk_based / equal / score の割付方法を実装。単元株（lot_size）丸め、1銘柄上限・aggregate cap・コストバッファの考慮、スケーリングと残余配分ロジックを備える。

- リサーチ（部分実装）
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）
    - Momentum 等のファクター計算方針と定数を追加（モメンタム期間・MA200・ATR 等）。DuckDB を経由した prices_daily / raw_financials ベースの計算を想定。関数 calc_momentum の冒頭実装（未完の可能性あり）。

- ユーティリティ
  - ロギングセットアップ（src/kabusys/utils/logging_setup.py）
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保存）をルートロガーに設定。LOG_LEVEL / LOG_DIR の解決順、ログディレクトリ作成失敗時のフォールバック動作を実装。
  - プロセス優先度 / CPU affinity（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収する set_process_priority（high/normal/low）と set_cpu_affinity を実装。psutil の例外を丁寧に扱う。
  - パッケージエクスポート（src/kabusys/portfolio/__init__.py、src/kabusys/tools/__init__.py など）を整備。

- DB 関連
  - DuckDB と SQLite の併用を想定した接続処理（run_* スクリプトやツール類で使用）。
  - 監視 DB の初期化呼び出し（init_monitoring_db）を複数エントリポイントで冪等に実施。

### Changed
- .env パーサの強化（src/kabusys/config.py）
  - export KEY=val 形式に対応。
  - クォート文字（' "）内のバックスラッシュエスケープ処理を実装。
  - クォートなしの値におけるインラインコメント判定の細かな扱いを実装。
  - プロジェクトルート探索を __file__ 起点で行うようにしてパッケージ配布後でも CWD に依存しない読み込みを目指す。

- 実行・監視の運用仕様（推定）
  - 起動時にプロセス優先度を "high" に設定することで、監視・実行スクリプトのレスポンス向上を図る。
  - 停止制御はプロジェクトルート下の data/stop_requested.flag をチェックするシンプルなファイルフラグ方式を採用。
  - paper_trading 環境では発注系を本番 DB と分離（PAPER_TRADING_SQLITE_PATH、MockBrokerClient を利用）。

### Fixed
- 複数箇所での堅牢性向上
  - ログディレクトリ作成失敗時に StreamHandler のみで継続可能にするなど、IO エラーに対してフォールバックする実装を追加。
  - process priority / cpu affinity 設定時の権限不足や未サポート環境での例外をキャッチして警告を出し処理を続行するよう改善。
  - ポジションサイジングで価格欠損時にスキップする等、不整合データに対する安全弁を追加。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

---

今後の提案（参考）
- factor_research の完実装（SQL クエリと例外ハンドリング、テスト追加）
- 単体テスト・統合テストの追加（特にポジション計算と risk_manager 周辺）
- ドキュメント（PortfolioConstruction.md など参照箇所の整備）をリリースノートや README に反映

以上。