# Changelog

すべての重要な変更点をこのファイルに記録します。  
この変更履歴は "Keep a Changelog" の形式に準拠しています。  

なお、以下の記載はコードベースの内容から推測してまとめたものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]
- 今後のリリース向けの注記・TODO（コード内の TODO コメント参照）
  - position_sizing: 銘柄ごとの単元サイズ（lot_size）を銘柄マスタから取得する拡張の実装予定
  - risk_adjustment: 価格が欠損した場合のフォールバック（前日終値／取得原価等）を改善予定
  - research/factor_research: ファクター計算モジュールの未完了箇所（ファイル末尾で途切れ）を完了予定

---

## [0.1.0] - 2026-04-24

### Added
- 基本アプリケーション情報
  - パッケージ初期バージョンを `__version__ = "0.1.0"` として定義。

- 実行スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）による停止制御をサポート。
    - スレッドで ExecutionEngine を起動し、停止フラグ検知時に安全にエンジンを停止。

  - run_monitoring.py: SystemMonitor ポーリングループ起動用スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する（設計上の注意点）。
    - 停止フラグ（data/stop_requested.flag）の検知でループを終了。
    - 例外発生時もログ出力して次回ポーリングへ復帰。

- 設定・環境管理
  - config.py: 環境変数・設定取得用 Settings クラスを実装。
    - .env / .env.local の自動ロード機能（プロジェクトルートが検出できる場合）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env 解析は export プレフィックス・クォート・バックスラッシュエスケープ・インラインコメント等に対応する堅牢な実装。
    - Paper Trading 向け設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）や監視・閾値設定（CPU/MEM/DISK 閾値）をプロパティで提供。
    - env 値の検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE のバリデーション）。

  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - 必須項目・選択肢・シークレット入力に対応し、.env を生成/更新する CLI。
    - 出力テンプレートには注意書き（.env をリポジトリにコミットしない等）を含む。

  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在とパース（PyYAML が利用可能な場合）などをチェック。
    - `--strict` オプションで警告も失敗扱いにできる。
    - live 環境向けの追加ガード（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険設定など）を警告。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - stdout 用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の環境変数で挙動を制御。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX(Linux/Mac/FreeBSD) の差分を吸収して優先度設定（high/normal/low）を実行。
    - CPU affinity の設定関数も提供。権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定・重み計算関数を追加。
    - select_candidates: スコア降順で上位 N を選択（タイブレークルール含む）。
    - calc_equal_weights, calc_score_weights: 等分配・スコア加重（スコア合計が 0 の場合は等分配へフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数を追加。
    - apply_sector_cap: 既存保有のセクター曝露に基づき新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py: 発注株数計算ロジックを追加。
    - 複数の allocation_method をサポート（"risk_based", "equal", "score"）。
    - risk_based: 損切り幅・risk_pct に基づくポジションサイズ決定。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）に応じたスケールダウンと端数処理（lot 単位での再配分）を実装。
    - cost_buffer により手数料・スリッページを保守的に見積もる機能を提供。
    - price 欠除時や price <= 0 の場合はスキップする安全ロジックを実装。
    - TODO コメントで将来的な拡張点を明示（銘柄別 lot_map 等）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - PAPER_TRADING_SQLITE_PATH（または --db）で DB を指定して期間フィルタ（--from / --to）を適用可能。
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等の集計を行い、PASS/FAIL 判定を出力。デフォルトの閾値をコード内で定義（稼働率 99%、fill rate 90% 等）。
    - P95 はカスタム実装で計算（空データは N/A 表示）。

- 研究用ファクター計算
  - research/factor_research.py: ファクター計算モジュールを追加（モメンタム・ボラティリティ等の計算方針を実装開始）。
    - DuckDB 接続を受け prices_daily / raw_financials を利用して計算する設計。
    - 一部（ファイル末尾）は未完/断片的（実装継続予定）。

### Changed
- N/A（初回リリースのため既存からの変更なし）

### Fixed
- N/A（初回リリースのため既存からの修正なし）

### Security
- 環境変数の取り扱いに注意する旨の注意書き:
  - config_setup にて .env ファイルは Git にコミットしないよう強調。
  - Settings._require にて未設定の必須環境変数が無い場合は明示的に例外を投げることで起動前に検出。

### Notes / 注意事項
- Monitoring の挙動に関する重要な設計上の注意:
  - run_monitoring は「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」と明示しているため、意図しないデータの上書きに注意が必要です。
- 権限関連:
  - process_priority.set_process_priority は権限不足で設定できない場合に警告を出して安全にスキップします（root/管理者権限を要求する場合あり）。
- ログ出力:
  - ログディレクトリが作成できない場合はファイル出力を行わず stdout のみで動作します。cron 等で起動する環境では LOG_DIR の設定を確認してください。
- validate_config:
  - PyYAML が未インストールの場合、config/*.yaml の内容チェックはスキップされます（警告出力）。
- テスト・開発向けフラグ:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env 読み込みを無効化可能（テスト時に便利）。

---

今後のリリースでは、research モジュールの完了、ポートフォリオ構築の拡張（銘柄別 lot サイズや価格フォールバック）、監視・実行エンジン周りの堅牢化（フェイルオーバーや詳細メトリクス）などが想定されます。