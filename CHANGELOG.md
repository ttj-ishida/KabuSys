# Changelog

すべての重要な変更は Keep a Changelog に準拠して記録します。
このファイルは後続のリリースで更新されます。

フォーマットの慣例:
- Added: 新機能
- Changed: 既存挙動の変更（互換性に注意）
- Fixed: バグ修正
- Removed, Deprecated, Security 等は必要に応じて追加

## [Unreleased]
- （今後の変更点をここに記載）

## [0.1.0] - 2026-04-18
最初の公開リリース。自動売買システムのコアユーティリティ、実行/監視ランナー、設定管理、ポートフォリオ構築、検証ツールなどを実装。

### Added
- 全体
  - パッケージ初期リリース (バージョン: 0.1.0)。
  - パッケージメタ情報を src/kabusys/__init__.py に追加。

- 設定管理
  - 環境変数・設定管理モジュール (src/kabusys/config.py)
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env/.env.local の読み込み順序と OS 環境変数保護。
    - 複数の設定プロパティを提供 (J-Quants, kabuAPI, DB パス, ログ設定, Kill Switch, 閾値等)。
    - PAPER_FILL_MODE の検証や KABUSYS_ENV / LOG_LEVEL の検証ロジック。
  - 対話式環境設定ウィザード (src/kabusys/config_setup.py)
    - .env の初期作成・更新を支援する CLI ウィザード。
    - シークレット値のマスク表示、選択肢・デフォルト対応、保存確認を実装。
  - 設定検証 CLI (src/kabusys/validate_config.py)
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証）。
    - 本番 (live) 向けの追加ガード（LINE 通知設定や Kill Switch 関連の警告）。
    - --strict オプションで警告を失敗扱いにできる。

- 実行・監視
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成（Mock 対応を想定）。
    - ExecutionEngine の組み立てとスレッド実行、停止フラグ（data/stop_requested.flag）および PID ファイル管理。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit 等）と initial_portfolio_value を broker.get_available_cash() から初期化。
  - 監視ポーリング用起動スクリプト (src/kabusys/run_monitoring.py)
    - SystemMonitor を使った定期ポーリングループ。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。
    - 監視は環境に関わらず production 用 sqlite_path を使用して監視データを一元管理。
    - 停止フラグ検知でループ終了、KeyboardInterrupt 対応。

- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ (src/kabusys/utils/logging_setup.py)
    - stdout（StreamHandler）と日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして続行。
  - プロセス優先度・CPU affinity ユーティリティ (src/kabusys/utils/process_priority.py)
    - Windows / POSIX の差異を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する機能を提供（実行環境でサポートされない場合は警告でスキップ）。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定・重み計算 (src/kabusys/portfolio/portfolio_builder.py)
    - select_candidates: スコア降順で上位 N を選択（同点時に signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコアが全て 0 の場合は等金額にフォールバック）。
  - セクターキャップ・レジーム乗数 (src/kabusys/portfolio/risk_adjustment.py)
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: market レジームに応じた資金乗数（bull/neutral/bear, 未知は 1.0 でフォールバック）。
  - 株数決定・リスク制限・ロット丸め (src/kabusys/portfolio/position_sizing.py)
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap によるスケールダウン、cost_buffer（手数料/スリッページ見積）を考慮。
    - aggregate スケールダウン時に残差を lot_size 単位で再配分するロジックを実装。

- リサーチ
  - ファクター計算モジュール (src/kabusys/research/factor_research.py) — 設計と最初の定数・calc_momentum の骨組みを追加（DuckDB 経由で prices_daily/raw_financials を参照して各種ファクターを算出する設計）。※ファイルは途中で切れているが、主要設計方針と一定の実装が含まれる。

- ツール
  - Paper Trading 検証レポート生成スクリプト (src/kabusys/tools/paper_verification_report.py)
    - ペーパートレード用 SQLite（環境変数 or --db）から稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計してレポート出力。
    - 合否判定基準（稼働率、fill/send 率、P95 レイテンシ等）の閾値を定義。
    - P95 計算、日付フィルタ、DB 存在チェックなどを実装。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / セキュリティ・運用上の注意
- .env ファイルは決してリポジトリにコミットしないこと（config_setup のヘッダに注意書きあり）。
- 本番環境 (KABUSYS_ENV=live) では LINE 通知や Kill Switch 設定を必ず確認すること（validate_config の警告を参照）。
- run_monitoring は監視データ用に常時 production sqlite_path を使用する設計。環境分離が必要な場合は運用ルールに注意。
- process priority / CPU affinity の設定は OS 権限に依存し、失敗した場合は警告ログを出してスキップする。権限の低い環境での運用に注意。

---

（将来のリリースでは各ファイルごとの変更点・修正点を上書き・追記してください。）