# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠し、セマンティックバージョニングを想定しています。

全般的な注記: 以下はコードベースの内容からの推測に基づく変更点の要約です。実際のコミット履歴が存在する場合はそれを優先してください。

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 初期リリースとして自動売買システム「KabuSys」の主要コンポーネントを実装。
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義。 (src/kabusys/__init__.py)
- 起動用スクリプトを提供。
  - SystemMonitor をポーリングする run_monitoring スクリプト（MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグファイルを監視）。(src/kabusys/run_monitoring.py)
  - ExecutionEngine を実行する run_execution スクリプト（KABUSYS_ENV=paper_trading のとき paper_trading 用 DB とモックブローカーを使用、停止フラグ・PID 管理）。(src/kabusys/run_execution.py)
- 環境設定・管理関連のツールを実装。
  - Settings クラスによる環境変数/設定の抽象化と検証（多くのプロパティ、PAPER_FILL_MODE の検証など）。(src/kabusys/config.py)
  - .env の対話的ウィザード `config_setup`（.env の生成・更新、シークレットのマスク表示）。(src/kabusys/config_setup.py)
  - 設定検証 CLI `validate_config`（必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、config/*.yaml の存在とパース検証、--strict オプション）。(src/kabusys/validate_config.py)
- 分析・検証ツールを追加。
  - ペーパートレーディング検証用レポート生成スクリプト `paper_verification_report`（稼働率、注文成功率、送信率、レイテンシ（P95）等の集計・閾値判定）。(src/kabusys/tools/paper_verification_report.py)
- ポートフォリオ構築ロジック（純粋関数群）を実装。
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。(src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）。(src/kabusys/portfolio/risk_adjustment.py)
  - 株数決定ロジック（calc_position_sizes）：risk_based / equal / score の各配分方式、単元株（lot_size）丸め、aggregate cap の縮小ロジック、cost_buffer による保守的見積り。(src/kabusys/portfolio/position_sizing.py)
- 共通ユーティリティを提供。
  - ロギング設定ユーティリティ `setup_logging`（stdout ストリームハンドラ + 日次ローテーションのファイルハンドラ、ログディレクトリ自動作成・フォールバック）。(src/kabusys/utils/logging_setup.py)
  - プロセス優先度／CPU affinity 設定ユーティリティ（Windows / POSIX の差分吸収、失敗時は警告でスキップ）。(src/kabusys/utils/process_priority.py)
- 研究用ファクター計算モジュール（骨格）を追加（momentum 等を想定、DuckDB 経由で prices_daily / raw_financials を参照）。(src/kabusys/research/factor_research.py)
- SQLite / DuckDB を用いた DB 初期化・接続処理（monitoring 用テーブルの初期化呼び出しポイントを整備）。(複数ファイル)

### 変更 (Changed)
- .env 自動ロードの挙動を整備。
  - プロジェクトルート判定ロジックを実装し（.git または pyproject.toml を探索）、CWD に依存せず .env/.env.local を読み込むようにした。OS 環境変数は保護され、.env.local は上書き可能。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。(src/kabusys/config.py)
- .env パーサーを強化。
  - export KEY=val 形式、シングル/ダブルクォート中のバックスラッシュエスケープ、コメント処理（クォート外での '#' 処理）などに対応。これにより .env の柔軟な記述をサポート。(src/kabusys/config.py)
- ロギング初期化の挙動を明確化。
  - 既存ハンドラのクローズ・削除を確実に行い二重設定を防止。ログファイル作成に失敗した場合はコンソール出力のみで継続するフォールバックを追加。(src/kabusys/utils/logging_setup.py)
- プロセス優先度設定のプラットフォーム互換性を向上。
  - Windows 用の HIGH/NORMAL/IDLE 定数のフォールバック、安全に access-denied を捕捉して警告を出す実装。(src/kabusys/utils/process_priority.py)
- ExecutionEngine 起動時の DB 分離を明確化。
  - paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離。monitoring テーブルは冪等に初期化される。（src/kabusys/run_execution.py, src/kabusys/run_monitoring.py, src/kabusys/config.py）

### 修正 (Fixed)
- ポーリング間隔の環境変数取り扱いで不正値を安全に処理。
  - MONITOR_POLL_INTERVAL が非整数・負値のときは警告を出してデフォルト（60秒）にフォールバック。(src/kabusys/run_monitoring.py)
- ExecutionEngine の起動・停止ロジックを安定化。
  - 停止フラグが既に立っている場合は起動を回避。起動中に停止フラグを検出したら Engine.stop() を呼んで安全に終了を試みる。スレッド結合処理にタイムアウトを設定。(src/kabusys/run_execution.py)
- Paper Trading レポート生成の堅牢性向上。
  - DB が存在しない場合の明確なエラーメッセージ、SQL 実行でテーブルが無い場合の例外保護（OperationalError をキャッチして N/A を扱う）。P95 計算の実装（空リスト時は None を返す）。(src/kabusys/tools/paper_verification_report.py)
- ポートフォリオ計算におけるゼロ・欠損データの安全処理。
  - 価格欠損・ゼロ価格を検出した場合にスキップしてログ出力。スコア合計が 0 の場合は等金額配分にフォールバック。(src/kabusys/portfolio/*)

### ドキュメント・補助 (Documentation)
- config_setup のウィザード・説明（各項目のデフォルト・説明文・シークレット扱い）を充実。書き出される .env テンプレートに注記（.env を絶対に Git にコミットしない旨）。(src/kabusys/config_setup.py)
- validate_config が生成するメッセージで INFO/WARNING/ERROR を出力し、--strict オプションで警告を失敗扱いにできるようにした。YAML パースチェックは PyYAML がインストールされていない場合はスキップして警告を出す。 (src/kabusys/validate_config.py)

### 既知の制約 / 注意点 (Known issues / Notes)
- research/factor_research.py はモメンタム等の計算ロジックの骨組みを含むが、ファイル末尾が途中で切れている（この changelog は存在するコードを基にした想定であり、未実装箇所がある可能性があります）。(src/kabusys/research/factor_research.py)
- position_sizing の単元株（lot_size）は現状グローバルに固定で 100 を想定している。将来的には銘柄別の lot_size をサポートする設計に拡張予定である旨の TODO コメントが残されている。(src/kabusys/portfolio/position_sizing.py)
- apply_sector_cap は "unknown" セクターを上限適用外にする仕様だが、price が欠損の場合に露出が過少見積りされる可能性がある点がコメントで指摘されている（将来的なフォールバック価格の導入を検討）。(src/kabusys/portfolio/risk_adjustment.py)

### セキュリティ (Security)
- .env ファイルはデフォルトで .git にコミットしないよう注意喚起を .env テンプレートに明記。シークレット入力時はマスク表示を行う。(src/kabusys/config_setup.py)

---

今後のリリース候補:
- factor_research の完全実装（DuckDB を用いた実データ処理、正規化ユーティリティとの連携）
- 単元株・手数料設定の銘柄別対応、ポートフォリオ最適化アルゴリズムの追加
- より詳細なテスト・CI、モニタリングの拡張（アラート送信の実装など）