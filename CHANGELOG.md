# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお、このリポジトリの初回リリース相当の状態をコードから推測してまとめています。

## [Unreleased]


## [0.1.0] - 2026-04-17
初回リリース相当。以下の主要機能とユーティリティを追加。

### Added
- アプリケーション設定管理（.env 自動読み込み・パース）
  - .env/.env.local をプロジェクトルートから自動読込（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 複雑な .env 行のパースをサポート（export プレフィックス、クォート／エスケープ、インラインコメントの扱い）
  - Settings クラスで各種設定値をプロパティとして提供（J-Quants / kabu API / DB パス / モニタ閾値 等） (src/kabusys/config.py)

- 環境設定ウィザード CLI（.env の対話式作成・更新）
  - 必須/任意の項目を対話形式で入力し .env を生成（デフォルト値・マスク表示対応）
  - .env 書き込みテンプレートを提供 (src/kabusys/config_setup.py)

- 設定検証 CLI
  - 必須環境変数やパスの存在チェック、config/*.yaml の存在とパース検証（PyYAML がない場合は警告）を実行
  - --strict モードで警告を失敗として扱うオプションを提供 (src/kabusys/validate_config.py)

- 実行系・監視系起動スクリプト
  - 実行エンジン起動スクリプト: ExecutionEngine をスレッドで実行し、stop フラグ検知で安全に停止（paper_trading 環境では paper DB を使用） (src/kabusys/run_execution.py)
  - 監視ループ起動スクリプト: SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能。監視は環境に関わらず本番 sqlite_path を使用 (src/kabusys/run_monitoring.py)

- Paper Trading 検証レポート生成ツール
  - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、レイテンシ等）を集計してレポート出力
  - P95 の計算、期間フィルタ、閾値による PASS/FAIL 判定を実装（閾値はソース内で定義） (src/kabusys/tools/paper_verification_report.py)

- ポートフォリオ構築モジュール（純粋関数群）
  - 候補選定 / 等配分・スコア加重配分 (select_candidates, calc_equal_weights, calc_score_weights) (src/kabusys/portfolio/portfolio_builder.py)
  - セクター上限適用（既存保有を考慮）とレジーム乗数（bull/neutral/bear） (src/kabusys/portfolio/risk_adjustment.py)
  - 株数計算（risk_based / equal / score）・単元株丸め・aggregate cap と cost_buffer を考慮したスケーリングロジック (src/kabusys/portfolio/position_sizing.py)
  - 上記をまとめて外部から利用できるパッケージエクスポートを提供 (src/kabusys/portfolio/__init__.py)

- リサーチ（ファクター）モジュール（DuckDB ベース）
  - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（ATR 等）、流動性指標等を DuckDB の prices_daily テーブルから計算する設計（関数化） (src/kabusys/research/factor_research.py)
  - 大規模データを想定したウィンドウ計算やデータ不足時の None 帰却などを考慮

- プロセス制御ユーティリティ
  - プラットフォーム差分（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）を設定する関数を追加
  - CPU affinity を最初の N コアに固定するユーティリティを提供
  - psutil による設定失敗は警告でスキップ (src/kabusys/utils/process_priority.py)

- 基本メタ情報
  - パッケージバージョンを定義 (src/kabusys/__init__.py: __version__ = "0.1.0")

### Changed
- （初回公開のため該当なし）

### Fixed
- （初回公開のため該当なし）

### Notes / Implementation details
- run_execution は paper_trading 環境の際に paper_sqlite_path を使用して本番 DB と分離することでテスト/検証を容易にしている。（設定: Settings.is_paper）
- run_monitoring は監視データ保存に production sqlite_path を使用する設計のため、モニタは常に本番 DB を参照する仕様になっている。
- .env の自動読み込みはプロジェクトルート検出（.git または pyproject.toml）に基づいており、配布後の実行環境でも CWD に依存せずに動作することを意図している。
- Paper Trading レポートの閾値・判定基準はソース内定数で定義されている（稼働率 99% など）。必要に応じて閾値は調整可能。

### Security
- .env は絶対に Git にコミットしないようにウィザードで注意書きを出力する。

---

参考:
- 主要ファイル一覧（実装参照）
  - src/kabusys/config.py
  - src/kabusys/config_setup.py
  - src/kabusys/validate_config.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/run_execution.py
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/portfolio/*
  - src/kabusys/research/factor_research.py
  - src/kabusys/utils/process_priority.py

（この CHANGELOG はソースから推測して作成しています。実際のリリースノート作成時は差分やコミットログを元に調整してください。）