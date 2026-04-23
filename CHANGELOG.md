# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルは、リポジトリ内のソースコードから推測可能な機能追加・挙動・安全策をまとめたものです。

## [0.1.0] - 2026-04-23

### Added
- 初回リリース — KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 起動スクリプト
  - run_execution: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV が `paper_trading` の場合は専用の Paper DB（既定: data/paper_trading.db）を使用して本番 DB と分離する。
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプト。環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関係なく本番用 sqlite_path を使用する設計。
- 設定管理
  - `kabusys.config.Settings` クラス: 環境変数からアプリ設定を提供（KABUSYS_ENV、DB パス、API トークン、モニタ閾値など）。`settings` のグローバルインスタンスを公開。
  - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を起点）を探索し、`.env` と `.env.local` を優先度に応じて読み込む（OS 環境変数は上書きされない）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env パーサー: クォート、エスケープ、コメント処理、`export KEY=val` 形式などに対応。
  - `config_setup` CLI: 対話式ウィザードで `.env` を新規作成・更新。シークレット項目はマスク表示。
  - `validate_config` CLI: 起動前チェックを行うツール。必須環境変数、KABUSYS_ENV の妥当性、ログレベル、DB パスや config/*.yaml の存在や YAML パース（PyYAML がある場合）を確認。`--strict` で警告も失敗扱いにできる。
- ロギング・運用ユーティリティ
  - `utils.logging_setup.setup_logging`: 共通ログ設定。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler、30 日分保持）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - ログレベル解決は引数 > 環境変数 > デフォルト("INFO") の優先順。
  - `utils.process_priority`:
    - プラットフォーム差分を吸収してプロセス優先度（high/normal/low）を設定。
    - CPU affinity を最初 N コアに固定する補助関数を提供。
    - Windows/Linux/macOS 等に対応し、権限不足や未対応環境では警告を出して安全にフォールバック。
- ポートフォリオ構築ロジック（純粋関数群）
  - `portfolio.portfolio_builder`:
    - select_candidates: BUY シグナルのスコアで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等配分にフォールバック）。
  - `portfolio.risk_adjustment`:
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値を超えるセクターの新規候補除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告と 1.0 フォールバック）。
  - `portfolio.position_sizing`:
    - calc_position_sizes: risk_based / equal / score の配分方式をサポート。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）でのスケールダウン、cost_buffer（手数料/スリッページ想定）を考慮した再配分ロジックを実装。
- Research（部分実装を含む）
  - `research.factor_research`: DuckDB 接続を用いた各種ファクター（モメンタム、移動平均乖離、ATR 等）計算モジュールの骨格を追加（DuckDB の prices_daily / raw_financials を参照する設計）。
- ツール
  - `tools.paper_verification_report`: Paper Trading 用 SQLite（既定: data/paper_trading.db）から稼働率、注文成功率・送信率、リスク却下数、レイテンシ（avg/max/P95）を集計してレポート出力。基準値を定義し PASS/FAIL 判定を行う。
- モニタリング DB 初期化
  - `monitoring.monitoring_db.init_monitoring_db` 呼び出しにより、実行時に監視用テーブルが存在することを保証（冪等な初期化）。

### Changed
- 起動時のプロセス優先度設定を起動直後（最初に）実行するように統一。これにより起動プロセスの優先度が早期に適用される。
- run_monitoring のポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能。値が不正（0 以下や非数）の場合は警告を出してデフォルト（60 秒）にフォールバックする安全策を追加。
- run_execution は paper_trading モードで専用の Paper DB を使用することで本番 DB と完全分離する挙動を明確化。

### Fixed
- .env パーサーの強化：
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理や、インラインコメントの正しい無視を実装。export 形式にも対応。
  - 無効行や空行、コメント行を適切にスキップするよう修正。
- logging_setup:
  - 既に設定済みのハンドラを再設定時に flush/close してから削除するようにし、二重ハンドラ登録を防止。
  - ログ出力を stdout に統一（cron 等からのリダイレクト対策）。
- process_priority:
  - 未対応 OS や権限不足時に例外で停止しないようにキャッチして警告でフォールバックする安全化。
- portfolio.position_sizing:
  - aggregate cap 超過時のスケーリング処理を追加し、lot_size 単位で端数処理・残余配分を行う実装で現金制約下の配分ずれを低減。

### Security
- シークレット項目（J-Quants トークン、kabu API パスワード、LINE トークン等）は config_setup の表示でマスクされ、.env ファイルの生成手順でユーザに明示的に入力を促すようにした。

### Notes / Operational details
- 停止フラグファイル（data/stop_requested.flag など）や PID ファイル（data/execution.pid 等）を用いた運用制御が組み込まれており、外部からの安全停止が可能。
- validate_config の `--strict` を使えば警告もエラー扱いにでき、本番環境移行前のチェックを厳格化できる。
- 一部モジュール（ブローカークライアント、ExecutionEngine、OrderManager、RiskManager、Reconciler、SystemMonitor、monitoring_db の内部実装等）は本リリースで参照・利用されており、実行時に適切な実装が必要。

---

今後の改善候補（推測）
- portfolio の銘柄別 lot_size 対応（マスタ参照による拡張）
- position_sizing の価格欠損時のフォールバック（前日終値など）
- research.factor_research の完全実装と単体テスト、DuckDB 最適化
- モニタリング・アラート（LINE 連携）の追加強化

---
（注）この CHANGELOG は、提供されたソースコードの内容に基づいて推測して作成しています。実際のコミット履歴やリリースポリシーに合わせて適宜編集してください。