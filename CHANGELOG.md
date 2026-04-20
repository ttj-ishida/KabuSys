# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。  
このファイルには、コードベース（バージョン 0.1.0）の主要な機能追加・改善点・修正を推定に基づきまとめています。

※ 日付はコードの最終更新日（推定）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 初期リリース: KabuSys パッケージ（日本株自動売買システム）の公開。
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - 設定に応じて paper_trading モードでは MockBrokerClient を使用し、ペーパートレード用の専用 SQLite DB（デフォルト: data/paper_trading.db）に記録する仕組みを提供。
    - 停止フラグ（data/stop_requested.flag）および PID ファイルの管理を実装。停止フラグ検知時に安全にエンジンを停止するループを備える。
    - プロセス優先度を起動直後に High に設定する処理を組み込み。
  - run_monitoring.py
    - SystemMonitor のポーリングループを実行するエントリポイント。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はログを出してデフォルトにフォールバック。
    - 停止フラグによるグレースフルシャットダウンと KeyboardInterrupt のハンドリング。
    - Monitoring は実行環境に関わらず本番の sqlite_path を用いる（監視データ一元化）。
- 設定管理
  - config.py
    - Settings クラスを提供し、環境変数から設定を取得する抽象化を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を検索）に基づく .env / .env.local の自動読み込み機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env ファイルの robust なパーサー実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメントの扱いなど）。
    - 各種設定プロパティ（DB パス、PID/kill flag パス、paper_trading 関連、監視閾値、環境種別判定など）を提供。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）や KABUSYS_ENV の有効値検査を実装。
- 設定ユーティリティ / CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。秘密値は入力時にマスク表示。
    - 既存の .env 読み込みと Enter による既存値再利用、保存前の確認画面を提供。
    - .env 書き込みテンプレートに注意文（Git にコミットしないこと）を含める。
  - validate_config.py
    - 起動前チェック用 CLI。必須環境変数や DB パス、config/*.yaml の存在・パースチェック（PyYAML 未導入時は警告）を行う。
    - --strict オプションで警告を FAIL として扱うモードを提供。
- ロギングとプロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一されたロギング初期化関数 setup_logging を提供。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保存）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の環境変数または引数による解決。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログにフォールバック。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。Windows と POSIX 系で差分を吸収し、安全にフォールバック。
    - psutil を用い、権限不足時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルをスコア降順で選択する機能。
    - calc_equal_weights / calc_score_weights: 重み計算。スコア合計がゼロのとき等金額配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑制するための候補フィルタリング（既存保有のセクター別エクスポージャー計算）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じて投下倍率を返す。
  - portfolio/position_sizing.py
    - calc_position_sizes: 重み・候補・ポートフォリオ価値・現金等から発注株数を決定（risk_based, equal, score の各方式をサポート）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate 上限（available_cash）に応じたスケーリング、cost_buffer による保守的見積り、残余を用いた追加配分のロジックを実装。
- 分析・ツール
  - tools/paper_verification_report.py
    - ペーパートレード用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等の指標を算出し PASS/FAIL 判定を行う。
    - P95 計算、期間フィルタ、DB パスのオプション指定をサポート。
  - research/factor_research.py（ファクター計算モジュールの初期実装）
    - Momentum 等のファクター計算（モメンタム、MA200 乖離等）を実装する設計に着手（DuckDB を用いた prices_daily 参照を想定）。※ ファイルは一部で切れており実装継続が必要。

### 変更 (Changed)
- 初期公開のための機能群を整理・モジュール化。全体設計として以下を採用:
  - DuckDB（分析用）と SQLite（監視／発注ログ用）を併用するアーキテクチャ。
  - 環境変数 / .env による構成管理、自動読み込み（.env, .env.local）を標準化。
  - 全起動スクリプトで共通の logging_setup を呼び出してログを統一管理。

### 修正 (Fixed)
- .env パーサーを強化し、クォート内のエスケープやインラインコメントの誤解析を防止することで設定読み込みの堅牢性を向上。
- MONITOR_POLL_INTERVAL の検証を追加し、0 以下や非整数入力が time.sleep に渡されるのを防止（不正値時はデフォルトにフォールバックし警告ログを出力）。
- ロギング初期化時に既存ハンドラを適切に flush/close してから再設定するようにし、二重出力を回避。
- init_monitoring_db の呼び出しを冪等化（監視テーブルが存在することを保証）して、起動時のエラーを低減。

### セキュリティ (Security)
- .env 書き込みテンプレートに「.env を Git にコミットしないこと」を明記。config_setup にて秘密値は入力時にマスク表示。
- 環境変数未設定時は明示的に ValueError を投げる保護（必須トークン・パスワードなど）。

### 廃止・削除 (Deprecated / Removed)
- なし（初期リリース）。

---

開発や運用中に検出された不具合や機能追加は、次のリリースで Unreleased セクションに追記してください。