# Changelog

すべての重要な変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

全般的な注意:
- このリリースはリポジトリの現状コードベースから推測して作成した変更履歴です。
- 実際のコミット履歴に応じて調整してください。

## [Unreleased]

（現在該当なし）

## [0.1.0] - 2026-04-18

初回リリース — KabuSys のコア機能群を実装・追加しました。主な追加点は以下のとおりです。

### Added
- 基本パッケージ情報
  - パッケージ識別子と初期バージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 環境設定と読み込み
  - .env 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。OS 環境変数を保護して .env/.env.local を読み込む仕組みを提供（src/kabusys/config.py）。
  - .env ファイルの柔軟なパース実装（export プレフィックス、クォート文字列、エスケープ、インラインコメント処理等）を追加。
  - Settings クラスで主要な設定項目をプロパティ形式で提供（J-Quants / kabuAPI / DB パス / PID / kill flag / 監視閾値 / env/log level 等）。
  - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）と paper_trading 用 SQLite パスの分離機能を追加。

- 設定関連 CLI
  - 対話式設定ウィザードを追加（python -m kabusys.config_setup）。.env の初期作成・更新を支援するインタラクティブ UI を提供。
  - 設定検証 CLI を追加（python -m kabusys.validate_config）。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パースチェック、本番環境向けの追加ガード等を検証。--strict オプションで警告を失敗扱いにできる。

- ロギングおよび運用ユーティリティ
  - 統一的なログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール出力は stdout に出力（StreamHandler）。
    - 日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を提供。ログディレクトリ作成失敗時はファイル出力を安全にスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順序を実装。
  - プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac 等）を吸収する実装。優先度設定（high/normal/low）、CPU affinity 固定機能を提供。権限不足等では安全にフォールバックし警告を出力。

- 実行・監視起動スクリプト
  - Execution エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - 起動時にプロセス優先度を high に設定。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と分離（MockBrokerClient の利用を選択する設計を示唆）。
    - BrokerClientFactory を経由してブローカークライアントを作成。
    - OrderRepository, OrderManager, RiskManager（デフォルトパラメータを含む構成）、Reconciler を組み立て ExecutionEngine を起動。ExecutionEngine は別スレッドで run_session を実行し、data/stop_requested.flag による停止を監視。
    - 起動前に監視テーブルを冪等に初期化（init_monitoring_db）。
  - Monitoring 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告でデフォルトにフォールバック。
    - Monitoring は環境に関係なく本番 sqlite_path を使用して監視データにアクセスする設計。
    - SystemMonitor を使った一回実行チェック（check_once）とループ処理、停止フラグ検出、例外ハンドリングを実装。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・タイブレークを実装し上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア正規化配分。スコア合計が 0 の場合は等金額にフォールバック。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター露出を計算し、1 セクター上限を超えている場合は当日の新規候補から除外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数を返却。未知のレジームは警告を出して 1.0 でフォールバック。
  - ポジションサイズ算出（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数算出（risk_based / equal / score）。
    - risk_based: 損切り率・リスク率に基づく株数計算、単元（lot_size）丸め。
    - equal/score: 重みに基づく割当て、1 銘柄上限・aggregate cap（available_cash 超過時のスケーリング）を実装。
    - コストバッファ（cost_buffer）を考慮した保守的見積り、端数処理（lot 単位）と残余キャッシュでの再配分ロジックを実装。

- Paper Trading 検証ツール
  - paper_verification_report スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）を読み、システム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - 基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を行う。
    - コマンドライン引数で期間指定（--from / --to）や DB パス指定（--db）に対応。

- データ研究（骨組み）
  - factor_research の骨組みを追加（src/kabusys/research/factor_research.py）。モメンタム等のファクター設計（計算範囲や要件）を文書化し、DuckDB 経由での計算を想定した設計を開始。

### Changed
- 初期設計として各コンポーネントの責務を明確化
  - DB 関連: DuckDB は分析用、SQLite は監視／注文履歴用として明確に分離。
  - Paper trading と Live の DB/ブローカー分離設計を明示（paper_sqlite_path, BrokerFactory 経由の切替）。
  - ログ出力は stdout を基準とし、ファイル出力はオプションかつ安全フォールバックする方向に統一。

### Fixed
- （このバージョンにおける明示的なバグ修正は無し。初期実装のため主に機能追加と既知の注意点の注記を含む）

### Known issues / Notes
- factor_research モジュールは計算関数の実装が途中（ファイル末尾が切れている）であり、追加実装が必要。
- apply_sector_cap の価格欠損（price が 0.0）の場合にエクスポージャーが過少評価される可能性がある旨の TODO コメントあり。将来的にフォールバック価格を導入することを想定。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に警告を出して安全にスキップするようにしているが、運用環境での挙動確認を推奨。
- 設定自動読み込み機能はプロジェクトルート検出に .git または pyproject.toml を使用するため、配布後や特殊なレイアウトでは自動読み込みがスキップされる場合がある。

---

今後の予定（推奨）
- factor_research の完全実装とテスト追加
- ExecutionEngine / SystemMonitor の統合試験（paper_trading / live）と運用ドキュメント整備
- 単体テスト・CI の導入（特に position_sizing・risk_adjustment のロジック）
- config/*.yaml のスキーマ検証と自動生成スクリプトの整備

<!--
参考: Keep a Changelog (https://keepachangelog.com/en/1.0.0/)
-->