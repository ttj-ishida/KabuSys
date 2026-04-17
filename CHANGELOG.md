CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣習に従って記載しています（意図的な推測を含みます）。  
各項目はコードベースから推測してまとめたもので、実際のコミット履歴ではありません。

フォーマット
-----------
- 影響範囲として該当するモジュール / ファイル名を併記しています。
- 日付はこのスナップショットの現在日（2026-04-17）を使用しています。

## [Unreleased]

### Added
- run_monitoring 起動スクリプトを追加/整備
  - src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループを起動する CLI スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止はプロジェクトルート/data/stop_requested.flag によるフラグ検出で行う。
  - 起動時にプロセス優先度を "high" に設定する処理を組み込み（utils/process_priority.set_process_priority を使用）。

- 実行エンジン起動スクリプト（ExecutionEngine）を追加/整備
  - src/kabusys/run_execution.py
  - ExecutionEngine を別スレッドで実行し、停止フラグ検出で安全に停止する仕組みを提供。
  - KABUSYS_ENV=paper_trading の場合は専用の paper_trading SQLite DB を使用し、本番 DB と分離して動作する（PAPER_TRADING_SQLITE_PATH により上書き可能）。
  - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine に注入する。

- 環境設定管理とウィザード
  - src/kabusys/config.py
    - .env 自動ロード機能（プロジェクトルート検出：.git または pyproject.toml を基準）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パース処理は export 句・クォート・エスケープ・インラインコメントの取り扱いに対応。
    - Settings クラスで各種環境変数の getter を提供（バリデーション付き: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - src/kabusys/config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援。生成される .env のテンプレートを整備。
    - 機密値は表示をマスクして確認。

- 設定検証 CLI
  - src/kabusys/validate_config.py
    - 必須環境変数やパス、config/*.yaml の存在・パースチェックを行う CLI。--strict オプションで警告も失敗にできる。
    - PyYAML が未インストールでも graceful に警告し検証をスキップする。

- ポートフォリオ構築ロジック（純粋関数群）
  - src/kabusys/portfolio/
    - portfolio_builder: 銘柄選定（select_candidates）と重み計算（等金額 / スコア加重）。
    - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）。
    - position_sizing: risk_based / equal / score の各配分方式に基づく株数計算（単元株丸め、aggregate cap によるスケーリング、cost_buffer による保守的見積り等）。
  - 各関数は副作用がなくメモリ内計算のみ（テスト容易性を考慮）。

- 研究用ファクター計算
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility 等のファクター計算を DuckDB 経由で実装（prices_daily, raw_financials を想定）。
    - 200日移動平均、1/3/6ヶ月リターン、ATR、出来高系指標などを算出。データ不足時は None を返す設計。

- ユーティリティ: プロセス優先度 / CPU affinity
  - src/kabusys/utils/process_priority.py
    - psutil を用いたクロスプラットフォーム向けのプロセス優先度設定（Windows の優先度クラスと POSIX の nice 値を吸収）。
    - CPU affinity 設定関数も用意（権限不足や未対応 OS では警告を出してスキップ）。

- ペーパートレード検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレードの検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL を判定。
    - デフォルト DB は data/paper_trading.db。--from/--to/--db オプション対応。

### Changed
- 環境変数の取り扱いと検証を強化
  - Settings と validate_config による入力バリデーションを充実させ、誤った値は明示的に例外や警告で通知するようにした（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。

- DB 関連の初期化を冪等化
  - init_monitoring_db を run_execution/run_monitoring 起動時に呼ぶことで監視テーブルが存在することを保証。monitoring 用テーブルの事前準備を明示化。

### Fixed
- .env パーサーの堅牢性向上
  - export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを改善し、誤読や意図しないトリミングを軽減。

### Known issues / TODO（コード内コメントより）
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、エクスポージャーが過小評価される可能性があるため、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO が残る。
  - lot_size を銘柄毎に可変にする拡張は未実装（現状は全銘柄共通の lot_size を想定）。
- monitor は「環境にかかわらず本番 sqlite_path を使用する」旨の挙動があるため、運用時に意図しない DB を操作しないよう注意が必要（意図的な設計であれば問題なし）。

## [0.1.0] - 2026-04-17

初回リリース（推定） — 基本機能の実装を含むリリース。

### Added
- 基本パッケージ情報
  - src/kabusys/__init__.py にバージョン __version__ = "0.1.0" を設定。

- CLI / 起動スクリプト
  - run_execution: 実運用 / ペーパートレードを分離して ExecutionEngine を起動するエントリポイントを提供。
  - run_monitoring: システム監視ポーリングループの起動スクリプトを提供。
  - config_setup: .env を対話式に作成・更新するウィザード。
  - validate_config: 起動前に環境・設定ファイルを検証する CLI。
  - tools/paper_verification_report: ペーパートレードの検証レポート生成ツール。

- コアライブラリ
  - 環境設定管理（src/kabusys/config.py）：.env 自動ロード、Settings クラス、各種環境変数のバリデーションを実装。
  - ポートフォリオ構築ライブラリ（src/kabusys/portfolio/）: 候補選定、重み付け、リスク調整、ポジションサイジングの純粋関数を実装。
  - 研究用ファクター計算（src/kabusys/research/factor_research.py）: Momentum / Volatility 等のファクター計算を DuckDB 経由で実装。
  - ユーティリティ（src/kabusys/utils/process_priority.py）: プロセス優先度 / CPU affinity 設定ユーティリティ。

### Changed
- DB 分離設計
  - ペーパートレード時に紙の取引ログは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）に保存し、本番 monitoring.db と分離する実装を導入。

### Security
- .env ファイルは絶対に Git にコミットしない旨の注意を config_setup に明記。

---

注意事項
--------
- 本 CHANGELOG は与えられたコードスナップショットの内容から推測して作成しています。実際のコミット・変更履歴とは差異がある可能性があります。  
- 実際のリリースノートにする場合はコミットログや PR の説明、リリース担当者の確認を踏まえて調整してください。