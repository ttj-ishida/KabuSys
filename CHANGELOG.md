# Changelog

すべての注目に値する変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマットの解釈:
- Added: 新機能の追加
- Changed: 既存機能の変更（挙動改善・仕様明確化など）
- Fixed: バグ修正や回避策
- Deprecated / Removed / Security: 今回該当なし

---

## [Unreleased]
- （現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-22

Added
- 基本アプリケーションの初期リリース。
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動エントリポイントを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite (デフォルト: data/paper_trading.db) を使用する仕組みを導入し、本番 DB と分離。  
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド起動と stop flag による安全停止を実装。
  - run_monitoring.py: SystemMonitor ポーリングループの起動エントリポイントを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視用 DB は KABUSYS_ENV に依存せず本番 sqlite_path を使用する設計。
- 設定関連
  - config.py: 環境変数/.env の読み込み・アクセスラッパーを実装。  
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env 自動読み込みをサポート。  
    - .env の行パースは export プレフィックス、クォート、エスケープ、行内コメント等に対応。  
    - Settings クラスでアプリ設定プロパティを提供（DB パス、各種閾値、環境判定、paper mode 等）。入力検証（列挙値検査や数値変換）を実装。
  - config_setup.py: 対話式の .env 作成/更新ウィザードを追加（secret マスク表示、既存値継承、保存テンプレート生成）。  
  - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パス親ディレクトリ確認、config/*.yaml の存在・パース検証、live 環境向けのガード）。--strict オプションで警告も失敗扱いにできる。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選別（select_candidates）と配分重み計算（等金額 calc_equal_weights、スコア比率 calc_score_weights）を実装。  
    - calc_score_weights は全スコアが 0 の場合に等分配へフォールバックして警告を出力。
  - portfolio/risk_adjustment.py: セクター集中上限適用（apply_sector_cap）と市場レジームに基づく乗数算出（calc_regime_multiplier）を実装。  
    - apply_sector_cap は売却予定銘柄をエクスポージャー計算から除外し、"unknown" セクターは上限適用対象外とする動作。  
    - calc_regime_multiplier は既定で bull/neutral/bear をハンドリングし、未知レジームは 1.0 へフォールバックして警告を出力。
  - portfolio/position_sizing.py: 発注株数算出ロジック（risk_based / equal / score の各方式）、単元株丸め、1銘柄上限・合計投下上限の調整、cost_buffer を加えた保守的見積もり、スケーリングと残差処理（lot 単位での再配分）を実装。
  - portfolio/__init__.py で上記関数をエクスポート。
- ユーティリティ
  - utils/logging_setup.py: 一貫したログ設定ユーティリティを追加。  
    - stdout 出力の StreamHandler（stdout を使用）と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、デフォルトで 30 日保持）をルートロガーに設定。  
    - 既存ハンドラのクリアで重複登録を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみへフォールバック。
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows と POSIX (Linux/Mac/FreeBSD) に対応。アクセス権限や未対応 OS では警告を出して安全にスキップ。
- tools
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。  
    - システム稼働率、注文成功率（fill/send）、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定する。  
    - 各閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）を定義。
- research
  - research/factor_research.py: ファクター計算モジュールの骨格（モメンタム/Value/Volatility/Liquidity 計算戦略）を追加。DuckDB 接続を受け prices_daily / raw_financials を参照する設計。モメンタム計算関数 calc_momentum の導入（未完の箇所あり、実装の続きが想定される）。

Changed
- ログ出力の扱いを統一: StreamHandler は stdout、ファイルハンドラは日次ローテーション、既存ハンドラの除去で複数起動時の重複を回避。
- .env 自動ロードの挙動:
  - OS 環境変数を保護して .env/.env.local を読み込む順序を定義。KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化可能。
- Execution / Monitoring の DB 接続ハンドリングを明確化:
  - monitoring は常に（環境にかかわらず）本番 sqlite を使用する仕様に明記。
  - execution は paper_trading 時に paper 専用 sqlite を使用して本番 DB と分離。

Fixed
- MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルト値へフォールバックする処理を追加（負または非整数入力に対処し time.sleep の例外を防止）。
- .env パースの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、行内コメントの取り扱い、無効行安全スキップを実装。
- process_priority / set_cpu_affinity 関数でアクセス権限不足や未サポート機能の例外をキャッチしてログ警告に置き換える安全化を実施。
- paper_verification_report の集計でテーブル欠如や OperationalError をキャッチして N/A/0 を返すように堅牢化。

Notes / Implementation details
- Stop/kill フラグ: run_execution/run_monitoring はプロジェクト内 data/stop_requested.flag を監視して安全停止する仕組みを採用（PID ファイルや kill flag との連携想定）。
- Execution の RiskManager デフォルト設定は実行時の broker.get_available_cash() に依存して initial_portfolio_value を初期化するように設定。
- position_sizing は現状単元株数 lot_size をグローバル固定（デフォルト 100）で処理。将来的には銘柄別単元対応を想定した拡張コメントあり。
- research/factor_research の実装は続きが必要（ファイル末尾が途中で切れている）。DuckDB ベースでのオンチェーン計算設計が行われている。

---

作成者: コードベースから推測して自動生成  
注: 上記はソースコードの内容から推測した変更履歴です。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、実リポジトリのコミットメッセージを基に詳細を補完してください。