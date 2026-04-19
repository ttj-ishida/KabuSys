# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在の初回リリースは 0.1.0 です。

## [Unreleased]

## [0.1.0] - 2026-04-19

### Added
- 初期リリースとして以下の主要コンポーネントを追加。
  - 実行用スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動するエントリポイント。KABUSYS_ENV による paper_trading 分離（専用 SQLite DB）をサポート。
      - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て起動。
      - デーモンスレッドでエンジンを実行し、外部停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応。
  - 監視用スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視 DB は環境にかかわらず本番 sqlite_path を使用する設計。
      - 停止フラグ検知、例外ハンドリング、KeyboardInterrupt による安全終了を実装。
  - 設定管理
    - src/kabusys/config.py
      - .env 自動ロード機能（プロジェクトルート検出：.git または pyproject.toml）を搭載。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が可能。
      - 複雑な .env パースを実装（export 形式、クォート内バックスラッシュエスケープ、行内コメントの扱いなど）。
      - 環境変数必須チェック関数 `_require` と Settings クラスを提供（各種パス・フラグ・閾値・着目設定をプロパティで取得）。
      - PAPER_FILL_MODE の検証、環境（KABUSYS_ENV）/ログレベル検証、paper_sqlite_path 等のサポート。
  - 設定ユーティリティ CLI
    - src/kabusys/config_setup.py
      - .env を対話式に作成・更新するウィザードを提供。既存 .env 読み込み、シークレットマスク表示、保存確認を実装。
    - src/kabusys/validate_config.py
      - .env と config/*.yaml の基本的な整合性検証ツールを提供。--strict オプションで警告を FAIL 扱いにできる。
      - PyYAML 未導入時のフォールバック（YAML 検証をスキップ）や DB パスの親ディレクトリ存在チェック、ライブ環境向け追加警告を実装。
  - ロギング / プロセス制御ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定。LOG_DIR 作成失敗時はファイル出力をスキップしてコンソールへフォールバック。
      - ログレベルとログディレクトリの解決順を実装。
    - src/kabusys/utils/process_priority.py
      - Windows と POSIX の差を吸収したプロセス優先度設定（psutil 利用）。set_cpu_affinity による CPU ピニング機能も提供。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（スコア降順）、等重配分、スコア加重配分（スコア合計 0 の場合は警告と等重フォールバック）を実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限 apply_sector_cap（売却予定銘柄を除外してセクターエクスポージャーを計算）とレジーム乗数 calc_regime_multiplier を実装。
      - 未知セクターは "unknown" 扱いで上限適用除外。未知レジームは 1.0 でフォールバック（警告付き）。
    - src/kabusys/portfolio/position_sizing.py
      - ポジションサイズ計算（allocation_method: "risk_based" / "equal" / "score"）を実装。単元株（lot_size）で丸め、max_position_pct や max_utilization による上限、aggregate cap（利用可能現金超過時のスケールダウン）を実装。コストバッファ（手数料・スリッページ想定）も考慮。
  - 解析・レポートツール
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード用 SQLite DB を読み取り、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などの指標を算出する CLI。閾値に基づく PASS/FAIL 判定を実装。
  - 研究用モジュール（部分実装）
    - src/kabusys/research/factor_research.py
      - DuckDB を用いたファクター計算基盤（モメンタム、MA200、ATR、出来高等）を実装する設計。関数 calc_momentum 等の定義開始。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし（初回リリース）

### Removed
- なし（初回リリース）

### Security
- なし（初回リリース）

### Notes / Known issues / TODO
- apply_sector_cap 内で price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の TODO が残っており、将来的に代替価格（前日終値や取得原価）を利用する検討が必要。
- position_sizing では将来的に銘柄別単元（lot_size）を stocks マスタから取得する拡張を想定する TODO が記載されている。
- research/factor_research.py はファイル末尾で未完（calc_momentum の実装最終部分が切れている）となっているため、ファクター計算の完全実装は今後の作業。
- .env パーサは比較的堅牢だが、極端な複雑ケース（ネストした引用や特殊なエスケープ）については追加のテストが望ましい。

---

README やドキュメント（PortfolioConstruction.md や StrategyModel.md 等）を参照して、運用手順（.env の作成 -> python -m kabusys.validate_config -> 実行スクリプト起動）を推奨します。