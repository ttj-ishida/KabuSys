# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  

注: このリリースは、提供されたコードベースから推測して作成した CHANGELOG です。実際のコミット履歴や差分と完全に一致しない場合があります。

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 初期リリース。以下の主要機能／モジュールを追加。
- 環境設定・読み込み
  - .env / .env.local の自動読み込み機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - 複雑な .env パース対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの解釈）。参照: src/kabusys/config.py
  - Settings クラスにより環境変数をラップして提供（各種パス、API トークン、Paper Trading 設定、閾値 等）。参照: src/kabusys/config.py
- 対話式設定ウィザード
  - .env の初期作成／更新を支援する CLI を追加（項目定義・マスク表示・保存機能）。参照: src/kabusys/config_setup.py
- 設定検証 CLI
  - .env および config/*.yaml の存在／基本整合性を検証するスクリプトを追加。--strict オプションで警告を FAIL 扱いにできる。参照: src/kabusys/validate_config.py
- ログ設定ユーティリティ
  - 統一的なログ初期化関数を追加。stdout ストリームハンドラと日次ローテーションするログファイルハンドラ（TimedRotatingFileHandler）を設定。ログレベル・ログディレクトリ解決の優先順位を実装。参照: src/kabusys/utils/logging_setup.py
- プロセス優先度／CPU affinity 操作
  - Windows/Linux/macOS を吸収するプロセス優先度設定ユーティリティを追加（"high"/"normal"/"low"）。CPU affinity 設定もサポート。参照: src/kabusys/utils/process_priority.py
- 実行および監視プロセス起動スクリプト
  - ExecutionEngine 起動スクリプトを追加。paper_trading 環境では MockBrokerClient を利用して専用 SQLite（デフォルト: data/paper_trading.db）を使用する分離設計。参照: src/kabusys/run_execution.py
  - SystemMonitor 起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する旨を明示。参照: src/kabusys/run_monitoring.py
  - いずれも起動時にプロセス優先度を "high" に設定する呼び出しを行う。
  - 停止制御用の stop_requested.flag / pid ファイルパスの取り扱いを実装。
- Execution コンポーネントの組み立て
  - BrokerClientFactory / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager などの依存関係を組み合わせてセッション実行する起動フローを実装。参照: src/kabusys/run_execution.py（注: 実際の各コンポーネント実装はファイルに依存）。
- Portfolio 構築ライブラリ
  - 銘柄選定・重み算出: select_candidates, calc_equal_weights, calc_score_weights を実装。スコア全体が 0 の場合は等分配にフォールバックして警告を出す。参照: src/kabusys/portfolio/portfolio_builder.py
  - リスク調整: セクター集中度制限 apply_sector_cap（売却予定銘柄の除外や unknown セクター扱い）、レジームに応じた資金乗数 calc_regime_multiplier（bull/neutral/bear）を実装。参照: src/kabusys/portfolio/risk_adjustment.py
  - 購入株数決定: calc_position_sizes を実装。risk_based / equal / score の配分方式をサポートし、単元株（lot_size）丸め、最大ポジション上限、利用可能現金に応じたスケーリング、cost_buffer を用いた保守的見積り、端数配分ロジック等を実装。参照: src/kabusys/portfolio/position_sizing.py
- Paper Trading 検証レポート
  - ペーパートレード用 SQLite（data/paper_trading.db 等）を走査して稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定を行うレポートツールを追加。閾値と表示フォーマットを定義。参照: src/kabusys/tools/paper_verification_report.py
- 研究用ファクター計算（研究モジュール）
  - DuckDB を使ったファクター計算基盤を追加。モメンタム等の計算関数（calc_momentum）を用意（prices_daily / raw_financials 想定）。参照: src/kabusys/research/factor_research.py（設計方針と初期実装を含む）

### 変更 (Changed)
- パッケージ初期化
  - パッケージのバージョンを 0.1.0 に設定。参照: src/kabusys/__init__.py

### 修正 (Fixed)
- .env 読み込み失敗時に警告を出す際、stacklevel を指定して warnings.warn を行うよう改善（ユーザーへの原因特定を容易にする）。参照: src/kabusys/config.py

### ドキュメント (Documentation)
- 各モジュールに詳細なドキュメンテーション文字列を追加（動作、引数、戻り値、備考、設計指針等）。例: portfolio モジュール、logging_setup、process_priority、factor_research、run_* スクリプト 等。

### 既知の制約 / 注意点
- run_monitoring はコメントにある通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する設計のため、監視データは環境分離されない点に注意してください。
- calc_position_sizes 等は価格データが欠損（price <= 0）な場合は該当銘柄をスキップする実装。将来的にフォールバック価格導入の余地あり（TODO コメントあり）。
- factor_research の実装は設計の段階からの実装を含むが、まだ完全実装されていない可能性があります（コードは先頭で一部マークされています）。

---

今後のリリースでは、各コンポーネント（ExecutionEngine、BrokerClient、リスク管理、モニタリング実装、本番向けの運用テストなど）の詳細な変更・改善を個別にリリースノートとして残していく予定です。