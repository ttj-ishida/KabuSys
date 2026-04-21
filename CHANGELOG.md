# Changelog

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-04-21
初回リリース（コードベースから推測した機能をまとめています）。

### Added
- 全体
  - パッケージの初期バージョンを追加（__version__ = 0.1.0）。
  - DuckDB/SQLite を用いたデータ保存・分析のためのパス設定を導入（Settings.duckdb_path / Settings.sqlite_path）。
  - 環境変数読み込みの自動化（プロジェクトルートの .env / .env.local の読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化に対応。
  - .env の堅牢なパーサを実装（クォート、export プレフィックス、インラインコメントの取り扱いなどに対応）。
  - Settings クラスを追加し、各種環境設定値（API トークン、DB パス、監視閾値、実行環境フラグ等）をプロパティで取得可能に。
  - 環境設定ウィザード CLI を追加（kabusys.config_setup）。対話形式で .env を作成/更新し、シークレット項目はマスクして扱う。
  - 起動前検証 CLI を追加（kabusys.validate_config）。必須環境変数、ログレベル、DB パス、config/*.yaml の存在と YAML のパース（PyYAML が存在する場合）等をチェック。`--strict` で警告をエラー扱いにできる。
- 実行 / 監視（ランスクリプト）
  - 実取引用エンジン起動スクリプトを追加（kabusys.run_execution）。  
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用専用 SQLite を使用し、MockBrokerClient を想定した分離が可能。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による停止制御、PID ファイル出力に対応。
    - RiskManager、OrderManager、Reconciler 等コンポーネントの組み立てロジックを実装。
  - 監視ループ起動スクリプトを追加（kabusys.run_monitoring）。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告。
    - 監視は本番 sqlite_path を使用する設計メモ（環境に依存せず本番 DB を参照する旨の注記あり）。
    - stop flag の検知で安全にループを終了。
- ロギング / プロセス管理ユーティリティ
  - 統一ロギング設定ユーティリティを追加（kabusys.utils.logging_setup）。  
    - stdout への StreamHandler（cron/Task Scheduler との相性のため stderr ではなく stdout を使用）と、日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。デフォルトログディレクトリは logs/、30 日分保持。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。Windows/Linux/macOS 等の差分を吸収し、優先度（high/normal/low）や CPU コアピン止めを設定可能。権限不足等は警告でスキップ。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定・重み計算モジュールを追加（kabusys.portfolio.portfolio_builder）。  
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。全スコア 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数を追加（kabusys.portfolio.risk_adjustment）。  
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補から除外（unknown セクターは除外しない）。  
    - calc_regime_multiplier: market regime に対して資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3、未知値は 1.0 にフォールバック）。
  - ポジションサイズ計算を追加（kabusys.portfolio.position_sizing）。  
    - risk_based / equal / score の各 allocation method をサポート。  
    - 単元（lot_size）丸め、1 銘柄上限、総投下上限（aggregate cap）、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング、端数の再配分アルゴリズムを実装。
- 研究・ツール
  - DuckDB を用いるファクター研究モジュールを追加（kabusys.research.factor_research）。モメンタム・ボラティリティ・バリュー等の計算を想定（prices_daily / raw_financials テーブル参照）。（注: ファイル末尾に未完の実装断片あり）
  - Paper Trading 検証レポート生成ツールを追加（kabusys.tools.paper_verification_report）。  
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）などを計算し、PASS/FAIL 判定を行う CLI。閾値は定義済み（例: 稼働率 >= 99% 等）。
    - PAPER_TRADING_SQLITE_PATH 環境変数 / --db オプションで DB を指定可能。

### Changed
- なし（初回リリースのため既存変更は無しと推測）。

### Fixed
- なし（初回リリースのため既存不具合修正は無しと推測）。

### Security
- 機密情報（J-Quants トークン、kabu API パスワード、LINE トークン）は .env に保存する設計。config_setup による .env 自動生成は .env を絶対に Git にコミットしない旨の注意を出力。

### Notes / Known issues (推測)
- factor_research.py において calc_momentum 関数の実装が途中で終わっている断片（ファイル末尾の切れ）が見られるため、当該モジュールは一部未完成または追加実装が必要。
- run_monitoring のコメントにある通り、監視処理が本番 sqlite_path を参照するため、意図しない DB を参照しないよう環境設定に注意が必要。
- process_priority / cpu_affinity の設定は権限やプラットフォーム実装に依存するため、実行環境に応じた挙動の確認が必要。

---

今後のリリースでは、未完成の研究モジュールの実装完了、ユニットテスト追加、CI/デプロイ手順の整備、さらに細かな動作確認に基づくバグ修正・改善を行うことが想定されます。必要であれば、この CHANGELOG をベースにさらに細かく分割して Unreleased セクションや日付を更新します。