# Keep a Changelog — CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。

注: 以下は提供されたコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴ではなく、コードに現れている機能・振る舞い・設計意図に基づく要約です。

## [Unreleased]

- ドキュメントやユーティリティ、テストに関する追加予定のメモ（該当箇所の TODO による）。
  - position_sizing の価格フォールバックや個別 lot_size 対応など将来対応予定の改善箇所あり。

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システムのコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理・検証ツール、および Paper Trading 向けの検証レポートを含む。

### Added

- パッケージ全体
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine の起動用スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する挙動を実装。
    - 実行中は停止フラグ (data/stop_requested.flag) を監視し、検出時に安全停止する機能を追加。
    - プロセス優先度を起動時に "high" に設定（set_process_priority を呼び出し）。
    - PID ファイル出力をサポート（data/execution.pid を想定）。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番の sqlite_path を使用する仕様（コード上で明示）。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - プロセス優先度を "high" に設定。

- 設定管理・検証
  - config.py
    - .env の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env の行パーサを実装（export プレフィックス、クォート文字、インラインコメントの取り扱いをサポート）。
    - Settings クラスを提供し、環境変数への安全なアクセス（必須変数チェック、デフォルト値、型変換、列挙チェック）を実現。
    - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等）や監視閾値 (CPU/MEM/DISK) を扱うプロパティを追加。

  - config_setup.py
    - インタラクティブな .env 作成・更新ウィザードを追加。
    - 既存 .env 読み込み・マスク表示・デフォルト値提示・保存確認を実装。
    - .env のテンプレート書き出しロジックを提供。

  - validate_config.py
    - 起動前に .env および config/*.yaml の不備を検出する CLI を追加。
    - 必須/任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、YAML のパース検証（PyYAML がない場合は警告）を実装。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーの一元設定ユーティリティを追加。
    - コンソール出力は stdout、ファイル出力は日次ローテーション (TimedRotatingFileHandler) でログディレクトリに保存（デフォルト logs/、30日保持）。
    - ログレベル解決順やログディレクトリ作成失敗時のフォールバックを明示。

  - utils/process_priority.py
    - プラットフォーム横断でプロセス優先度設定（Windows の priority class / POSIX の nice）を実装。
    - CPU affinity を指定する set_cpu_affinity も提供。
    - psutil のアクセス制限や未対応プラットフォームは警告を出してスキップする安全策を実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルから候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を追加。
    - スコア合計が 0 の場合は等金額配分にフォールバックして警告。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（売却予定銘柄の除外や "unknown" セクター取り扱いを考慮）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームはフォールバックして警告）。

  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate 上限・利用可能現金に対するスケーリング、cost_buffer（手数料/スリッページ見積り）を考慮。
    - 価格欠損時のスキップやログ出力を実施。
    - スケールダウン時の端数配分（fractional remainder）を考慮して再配分するアルゴリズムを実装。

  - portfolio/__init__.py
    - 上記関数群をパッケージ API としてエクスポート。

- リサーチ（ファクター計算）骨格
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity 等の計算方針および calc_momentum の冒頭実装（関数定義、定数、設計方針）を追加。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計し、PASS/FAIL 判定（しきい値はソース内定義）を行う。
    - 日付フィルタ（--from/--to）および DB パス指定（--db / 環境変数）をサポート。
    - DB が存在しない・テーブルがない場合に安全に N/A を出力する耐障害性を備える。

### Changed

- なし（初回リリースのため変更履歴は未過去分のみ）。ただしモジュール内に将来改善予定の TODO コメントあり。

### Fixed

- なし（初回リリース）。ただし以下の堅牢性対策が組み込まれている:
  - .env パーサが export やクォート・コメント処理を適切に扱うよう実装。
  - ログディレクトリ作成失敗や psutil の権限エラーをハンドリングしてフォールバックする設計。
  - Monitoring / Execution の停止フラグ検知で安全に停止する処理を導入。

### Security

- 機密情報の取り扱いに関する配慮:
  - config_setup と .env の出力において .env を決してコミットしない旨をコメントで明示。
  - ウィザードでシークレット項目はマスク表示。
  - ただし、実運用時は .env の管理・アクセス制御が必要。

### Notes / Known limitations

- position_sizing の価格フォールバック（価格が 0 の場合の代替取得）や銘柄別 lot_size サポートは TODO として残されている。
- research/factor_research モジュールは設計方針と一部関数の骨格を含むが、完全実装（全ファクターの計算ロジックなど）は未完。
- YAML 検証は PyYAML の有無に依存し、インストールされていない環境ではスキップして警告を出す。
- process_priority はプラットフォーム依存の制約により、権限不足や未対応 OS の場合はスキップされる可能性がある。

---

これらの記載はコードから読み取れる挙動・意図を基にした推測的な CHANGELOG です。実際のリリースノートとして使う場合は、各機能ごとに対応するコミットやユニットテスト、ドキュメントを参照して内容を確定してください。