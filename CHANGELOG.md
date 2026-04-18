# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
リリース日はソースコードから推測した時点（このドキュメント作成日: 2026-04-18）を使用しています。

全般的な注意
- このリポジトリはバージョン 0.1.0（src/kabusys/__init__.py）として初回の機能群を実装しています。
- .env の自動読み込みはデフォルトで有効です（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- .env パースは export 形式やクォート、インラインコメント等に対応しています。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成
  - パッケージエントリポイントおよびバージョン: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を使用）。
    - 停止フラグ (data/stop_requested.flag) を監視して安全停止を行う。
    - 実行時の PID を data/execution.pid に記録する仕組み（pid_file を受け渡す）。
  - run_monitoring.py
    - SystemMonitor をポーリングする監視ループのエントリポイント。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒、不正値はデフォルトにフォールバック）。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path（data/monitoring.db 等）を使用する仕様。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
- 設定管理
  - Settings クラス（src/kabusys/config.py）
    - 環境変数の取得ラッパーを提供し、必須変数未設定時は ValueError を投げる _require() を実装（J-Quants / kabu API のトークン等）。
    - デフォルト値、パス解決（Path.expanduser）、Paper Trading 用の別 sqlite パス、閾値設定（CPU/MEM/DISK）などを管理。
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許容）。
    - PAPER_FILL_MODE（paper trading の fill モード）に対する検証。
  - .env 自動読み込み
    - プロジェクトルート検出は .git または pyproject.toml を基準に行うため、CWD に依存しにくい実装。
    - .env と .env.local の読み込み順序（OS 環境変数 > .env.local > .env）、既存 OS 環境変数の保護機構を実装。
    - .env のパーサは export 形式・引用符・エスケープ・コメントの扱いを考慮。
- 設定関連 CLI
  - config_setup.py
    - .env を対話的に生成・更新するウィザード。デフォルト値、選択肢、シークレット入力（マスク表示）に対応。
    - 生成された .env は Git にコミットしないようヘッダを付与して保存。
  - validate_config.py
    - 起動前の設定検証ツール（必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在とパース検証）。
    - --strict オプションにより警告も失敗扱いにできる。
    - PyYAML がない場合は YAML 検証をスキップして警告を出す。
- ロギング・ユーティリティ
  - utils/logging_setup.py
    - setup_logging() を提供。全起動スクリプトで共通のログ設定をできるようにした。
    - コンソールは stdout に出力（StreamHandler）。ファイル出力は TimedRotatingFileHandler により日次ローテーション（デフォルト logs/<app_name>.log、30 日分保持）。
    - ログレベル解決順とログディレクトリ解決順を定義。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス優先度・CPU affinity
  - utils/process_priority.py
    - set_process_priority()：Windows（HIGH_PRIORITY_CLASS 等）と POSIX（nice）の差分を吸収して優先度設定。
    - set_cpu_affinity()：指定コア数に固定する機能（利用不可時は警告を出してスキップ）。
    - 権限不足や未対応 OS の場合は安全にスキップする実装。
- ポートフォリオ構築ライブラリ（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - select_candidates(): スコア降順＋タイブレークにより候補選定。
    - calc_equal_weights(), calc_score_weights(): 重み計算、スコア合計が 0 の際は等配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap(): セクター集中上限チェック（既存ポジションのセクター別時価を計算し、超過セクターの新規候補を除外）。"unknown" セクターは上限判定から除外。
    - calc_regime_multiplier(): market regime に応じた投下資金乗数（bull/neutral/bear）。未知のレジームは 1.0 でフォールバック（警告）。
  - portfolio/position_sizing.py
    - calc_position_sizes(): allocation_method（"risk_based" / "equal" / "score"）に応じた株数計算。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超えた場合はスケールダウンと残差再配分）を実装。
    - cost_buffer を考慮した保守的な投資額見積もり。
    - TODO や注釈（銘柄別 lot_size 拡張や価格欠損時のフォールバック）を残す。
- Research / ファクター計算
  - research/factor_research.py（設計・一部実装）
    - Momentum 等のファクター計算機能（DuckDB 接続を受け prices_daily / raw_financials を参照）。
    - 定数（窓幅等）定義と calc_momentum の API が存在（実装は続くことを示唆）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツール。期間指定 (--from / --to)、DB パス指定 (--db) に対応。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出して PASS/FAIL 判定を行う。
    - 既定の閾値（稼働率 99%、fill rate 90%、send rate 95%、P95 レイテンシ 200ms）を定義。
    - P95 計算ロジックや、テーブル欠損時の安全ハンドリング（OperationalError を捕捉）を実装。

### Changed
- （初回リリースのため履歴的変更はなし。ただし設計上のデフォルト挙動を明記）
  - 監視（monitoring）は常に本番用 sqlite_path を参照する設計になっている点を明確化（run_monitoring.py）。

### Fixed
- （初回リリース）いくつかの堅牢性向上:
  - .env 読み込み失敗時に警告を出して処理を継続する（config._load_env_file）。
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗を想定してコンソール出力のみで継続する（logging_setup）。
  - プロセス優先度 / CPU affinity の設定で権限不足や未対応 API に対して警告でスキップ（process_priority）。

### Removed
- なし

### Security
- 必須シークレット（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）未設定時はアプリ起動前に検出・例外化するため、誤った起動を防止する仕組みを導入（config._require / validate_config）。

### Notes / Breaking changes / Caveats
- Settings.env の値検証は厳格で、不正な KABUSYS_ENV や LOG_LEVEL を設定すると ValueError を送出します。運用環境に適切な環境変数を設定してください。
- .env の自動読み込みはデフォルトで有効です。テストや特別な実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑止できます。
- run_monitoring は「監視用 DB として本番 sqlite_path を使用する」ため、paper_trading 環境においても監視データが本番 DB に向いてしまう点に注意してください（設計上そうなっています）。
- Paper Trading と Live の DB は分離するよう設計されていますが、設定ミスでパスが重複するとデータが混在する恐れがあります。validate_config で DB パスの親ディレクトリ存在チェックや警告を出しますが、運用時には明示的にパスを確認してください。
- 一部モジュール（research/factor_research.calc_momentum 等）は実装中・継続実装を想定しています。詳細実装は今後のリリースで追加予定です。

---

今後の予定（例）
- factor_research の完全実装（全ファクターと正規化ユーティリティの統合）。
- ExecutionEngine / Broker クライアントのユニットテスト強化およびモックの整備。
- position_sizing の lot_size を銘柄別にサポートする拡張。
- 監視（monitoring）と実行（execution）の運用監視ルール・アラート連携（LINE 通知等）の追加強化。