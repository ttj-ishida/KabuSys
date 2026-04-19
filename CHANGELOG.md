# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-19

初回リリース。KabuSys のコア CLI / ランタイム / ユーティリティ群を追加しました。

### Added
- 全体
  - パッケージ初期化（バージョン 0.1.0）。
  - 設定読み込み・管理モジュールを追加（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルート検出: .git / pyproject.toml）を実装。
    - .env のパース機能を強化（export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメントの扱いをサポート）。
    - 各種環境変数用のプロパティ（J-Quants、kabuAPI、DB パス、PID / Kill flag 等）。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
  - 設定ウィザード CLI（src/kabusys/config_setup.py）を追加。
    - 対話式に .env を作成・更新する機能。
    - デフォルト値・シークレット入力・選択肢対応。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスや config/*.yaml の存在チェック、
      live 環境向けの追加ガードなどを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
  - 実行系起動スクリプト
    - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
      - KABUSYS_ENV=paper_trading 時は paper_sqlite_path を使用して本番 DB と分離。
      - BrokerClientFactory を介したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て。
      - 停止フラグ (data/stop_requested.flag) と PID ファイル (data/execution.pid) の扱い。
      - プロセス優先度を起動時に high に設定。
    - SystemMonitor 起動スクリプト（src/kabusys/run_monitoring.py）を追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番 sqlite_path を使用する実装（監視 DB は本番パス固定の挙動）。
      - duckdb を監視処理と併用。
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加。
    - SQLite（PAPER_TRADING_SQLITE_PATH）から集計し、稼働率・注文成功率・送信率・レイテンシ（平均 / 最大 / P95）などを出力。
    - PASS/FAIL 判定基準（稼働率 99% 等）を実装。
    - 日付フィルタ (--from / --to) をサポート。
  - Portfolio 構築ライブラリ（src/kabusys/portfolio/*）を追加。
    - 候補選定: select_candidates（スコア降順、同点時は signal_rank でタイブレーク）。
    - ウェイト計算: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
    - リスク調整: apply_sector_cap（既存保有をセクターごとに集計し上限超過セクターの新規候補を除外、"unknown" セクターは適用除外）、calc_regime_multiplier（bull/neutral/bear の乗数、未知値は 1.0 でフォールバック）。
    - ポジションサイズ決定: calc_position_sizes
      - risk_based / equal / score の割当方式に対応。
      - 単元株（lot_size）で丸め、1 銘柄上限・集計上限（available_cash）でスケールダウン、スケールダウン後の端数は残差順に単元単位で再配分。
      - cost_buffer による手数料/スリッページ見積りを考慮。
  - Research ファクター計算（部分実装、src/kabusys/research/factor_research.py）
    - モメンタム / MA200 / ATR / 出来高等を計算する設計、DuckDB 経由で prices_daily / raw_financials を参照する想定。
  - ユーティリティ群
    - ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）
      - stdout ストリームハンドラ + 日次ローテーションファイルハンドラをルートロガーに設定。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
      - 既存ハンドラのフラッシュ/クローズ→クリアを行い二重設定を防止。
    - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
      - Windows / POSIX の差分を吸収して set_process_priority(level) を提供。
      - set_cpu_affinity(cpu_count) で先頭 N コアに固定する機能（存在しない場合は警告を出してスキップ）。

### Changed
- ログ周り
  - ログ設定はアプリ毎（app_name）にログファイルを分け、デフォルトで logs/<app_name>.log を使用。
  - ログレベル解決順を明確化（引数 > 環境変数 LOG_LEVEL > デフォルト INFO）。
- DB の扱い
  - 監視 (run_monitoring) は環境に関係なく Settings.sqlite_path（本番想定）を使用する設計を明示。
  - 実行エンジン (run_execution) は paper_trading 環境のとき専用の paper_sqlite_path を使用し本番 DB と完全に分離。
- .env 自動ロード
  - OS 環境変数が優先され、.env.local は .env を上書きする挙動（ただし既存の OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。

### Fixed / Robustness improvements
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープや引用符閉じの扱いを正しく解析。
  - クォートなし値のインラインコメント扱い（直前がスペース/タブのみコメントと認識）。
- ロギング初期化でのディレクトリ作成失敗に耐性を持たせ、ファイルハンドラ作成失敗時はコンソール出力のみで継続。
- process_priority / cpu_affinity の例外処理を強化し、権限不足や未サポートプラットフォームでも安全にスキップして警告ログを出すようにした。
- calc_score_weights: 全スコアがゼロのとき等配分へフォールバックして警告ログを出力。
- apply_sector_cap: セクター不明 ("unknown") の銘柄は強制除外対象とせず除外を適用しない仕様を明確化。
- calc_position_sizes: 単元丸め・aggregate cap スケーリング・端数配分ロジックの実装により、可用現金を超える配分時の安定性を向上。

### Documentation / CLI messages
- 各 CLI（config_setup / validate_config / paper_verification_report）の使い方・メッセージを充実化。
- config_setup の出力テンプレートは .env の作成/保存手順を明示（Git に .env をコミットしない注意書き等）。

### Known limitations / Notes
- research/factor_research.py は設計・一部実装を含むが、完全なクエリ実装やユニットテストが未完了の箇所がある（ファイル末尾で途中断）。
- calc_position_sizes 内の価格欠損時の挙動に対する TODO コメントあり（価格が 0 の場合のフォールバックに関する改善点）。
- run_monitoring は監視 DB として常に sqlite_path（本番想定）を使用するため、開発・検証時は注意が必要。

---

（以上）