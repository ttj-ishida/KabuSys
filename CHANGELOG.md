# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-23

### 追加 (Added)
- 基本アプリケーションパッケージを追加
  - パッケージ情報: kabusys (バージョン 0.1.0)
- 起動スクリプト / デーモン類
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ機構: プロジェクトの data/stop_requested.flag ファイルを監視して優雅に停止。
    - 監視は環境に関わらず本番用の sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（Paper Trading）を利用し、data/paper_trading.db を専用 DB として分離。
    - 停止フラグ（data/stop_requested.flag）検知による停止制御、エンジン PID ファイルの書き出し機能（data/execution.pid）。
    - マルチスレッドで ExecutionEngine を起動し、停止フラグ検知時に engine.stop() を呼ぶ仕組み。
- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env と .env.local の読み込み規則（OS 環境変数を保護しつつ .env.local は上書き可能）。
    - 複雑な .env パース実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント処理）。
    - Settings クラスを提供し、各種環境変数（J-Quants / kabu API / DB パス / 監視しきい値 / 実行環境等）をプロパティ経由で取得。
    - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH 等の Paper Trading 関連設定サポート。
- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードにより .env の初期作成 / 更新を支援。
    - デフォルト値、選択肢、シークレット入力対応、保存前の確認プロンプトを実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - --strict モードで警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出力。
    - 必須環境変数チェック、KABUSYS_ENV 値チェック、ログレベル・DB パスの検査、Live 環境向けガードを実装。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード DB を解析して稼働率、注文成功率、送信率、レイテンシ等を集計・判定するレポート生成スクリプトを追加。
    - コマンドライン引数 --from / --to / --db をサポート。
    - デフォルトの DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。
    - レポート内の判定基準（P95 レイテンシ、稼働率など）を定義（ソースに閾値を記載）。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア全てが 0 の場合は等配分へフォールバックし WARNING を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を実装（既存保有・売却予定銘柄を考慮）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear + フォールバック）。
  - portfolio/position_sizing.py
    - 株数算出ロジック (risk_based / equal / score) を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金超過時のスケーリング）を実装。
    - cost_buffer による手数料・スリッページ考慮、残差配分ロジック（fractional remainder に基づく追加配分）を実装。
- 研究・ファクター計算（下地）
  - research/factor_research.py（モメンタム計算の骨子を追加。関数 calc_momentum の実装開始）
    - DuckDB を前提としたファクター計算基盤（prices_daily / raw_financials 参照）を設計。
- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。
    - stdout への StreamHandler（stdout を使用）と、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30 日保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py
    - Windows / POSIX(Linux/macOS/FreeBSD) を吸収したプロセス優先度設定機能を追加（high/normal/low）。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。
    - 設定失敗時は警告を出してスキップする堅牢設計。

### 変更 (Changed)
- 起動時のプロセス優先度設定を統一
  - run_monitoring と run_execution ともに起動直後に set_process_priority("high") を呼び、優先度を上げるようにした。
- DB の扱いを環境により明確化
  - run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用し、本番 DB と完全分離。
  - run_monitoring は環境にかかわらず監視用 sqlite_path（本番設定）を使用するように明示。
- ロギングのデフォルト挙動
  - ログディレクトリ default を "logs" に統一し、アプリ名ごとに logs/<app_name>.log を出力。

### 修正 (Fixed)
- .env パースの強化
  - export プレフィックス、クォート/エスケープ、行内コメントなどのケースを正しく処理するよう改良。
- 設定検証の堅牢化
  - validate_config において YAML が読み込めない場合に適切にスキップして警告を出すようにした。
- ポジション決定ロジック
  - aggregate cap のスケーリングと残差処理で、lot_size 単位の丸めと追加配分を実装し、利用可能現金を超えないよう調整。

### 既知の制限・注意事項 (Known issues / Notes)
- research/factor_research.py の calc_momentum 実装が途中（ファイル末尾が切れている）。完全実装は今後のリリース予定。
- apply_sector_cap の注記: price が欠損（0.0）の場合にエクスポージャーが過少となる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨の TODO が残っている。
- process_priority の一部 API はプラットフォーム依存（Windows の定数等）。権限不足や未対応 OS の場合は警告を出してスキップする。
- logging_setup はログディレクトリ作成やファイルハンドラ作成に失敗した場合にファイル出力を無効化して stdout のみで継続する挙動となる。
- config.py の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。CI/テストで環境依存を避けるために利用できる。
- validate_config の警告は --strict オプションで失敗扱いにできる（CI に組み込み可能）。

### ドキュメント / 使用手順メモ
- 起動方法の例
  - 監視: python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔指定（秒）
  - 実行: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading にすると paper_trading DB を使用
- 設定管理
  - 初期 .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

### セキュリティ (Security)
- 現時点で特に公開済みのセキュリティフィックスはありません。機密情報（トークン・パスワード等）は .env を通して設定し、このファイルをリポジトリにコミットしないことを強く推奨します（config_setup のヘッダにも注意書きあり）。

---

今後の予定:
- factor_research の完全実装（モメンタム/Value/Volatility/Liquidity の算出）
- 戦略・実行エンジン (ExecutionEngine / BrokerClient 等) の統合テスト強化
- price フォールバックロジックや銘柄別 lot_size 対応等の改善

（以上）