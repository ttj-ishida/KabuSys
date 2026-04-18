# Changelog

すべての注目すべき変更履歴を Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠した形式で記載します。  
このファイルは、与えられたコードベースから推測して自動生成されています。実際のコミット履歴ではない点にご注意ください。

全般
- バージョン情報はパッケージルートの `src/kabusys/__init__.py` にて `0.1.0` が設定されています。

## [0.1.0] - 2026-04-18

Added
- 初期実装の主要コンポーネントを追加。
  - 実行系 / 監視系起動スクリプト
    - src/kabusys/run_execution.py: ExecutionEngine 起動スクリプトを追加。Paper Trading 時は専用の SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離する仕組みを実装。
    - src/kabusys/run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイル（data/stop_requested.flag）の検知で安全終了。
  - 設定・環境管理
    - src/kabusys/config.py: 環境変数ラッパー `Settings` を実装。.env 自動ロード機能（.env / .env.local）を追加し、`KABUSYS_DISABLE_AUTO_ENV_LOAD` による無効化をサポート。`.env` のパースはクォートや `export KEY=...` に対応。
    - src/kabusys/config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新）。シークレット項目は表示時にマスク。生成される .env は Git にコミットしない旨のヘッダー付与。
    - src/kabusys/validate_config.py: 起動前チェック用 CLI を追加。必須環境変数・KABUSYS_ENV 値・DB パス・config/*.yaml の存在・本番用ガードなどを検査。`--strict` により警告も失敗扱いにできる。
  - ロギング・プロセスユーティリティ
    - src/kabusys/utils/logging_setup.py: ルートロガー統一設定ユーティリティを追加。StreamHandler は stdout を使用、TimedRotatingFileHandler による日次ローテーション（30 日保持）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
    - src/kabusys/utils/process_priority.py: クロスプラットフォームでのプロセス優先度設定（`set_process_priority`）および CPU affinity 設定（`set_cpu_affinity`）を追加。Windows / POSIX に対応し、失敗時は警告を出してスキップ。
  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py:
      - select_candidates: BUY シグナルのスコア順ソートと上位 N 抽出。
      - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等金額へフォールバック）。
    - src/kabusys/portfolio/risk_adjustment.py:
      - apply_sector_cap: セクターごとの上限チェック（指定比率超過セクターに対して新規候補を除外）。"unknown" セクターは上限チェックの対象外。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear のマップ、未知レジームは警告のうえフォールバック）。
    - src/kabusys/portfolio/position_sizing.py:
      - calc_position_sizes: 複数の配分方式（risk_based / equal / score）をサポート。単元株（lot_size）での丸め処理、ポジション上限・agg cap（available_cash）に基づくスケーリング、cost_buffer（手数料/スリッページ想定）考慮、lot 単位での残余配分ロジックを実装。
    - src/kabusys/portfolio/__init__.py: 上記機能をパッケージとして公開。
  - リサーチ / ファクター計算（基礎実装）
    - src/kabusys/research/factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算モジュールを追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。（ファイル末尾は実装途中の断片あり）
  - ツール
    - src/kabusys/tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を出力。CLI オプション `--from` / `--to` / `--db` をサポート。

Changed
- ログ出力先とハンドラの仕様を統一
  - StreamHandler を stdout に固定（cron 等からのリダイレクトを想定）。ログファイルハンドラは日次ローテーションで保管、ディレクトリ作成失敗時は自動でファイル出力を無効化してコンソールのみで継続する動作に。
- .env 自動ロードの挙動
  - OS 環境変数を保護するため `.env` 読み込み時は既存 OS 環境変数を上書きしない（.env.local は override=True だが保護対象は上書きされない）。`KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
- 実行/監視プロセスの優先度
  - run_execution/run_monitoring の起動時に最初にプロセス優先度を "high" に設定する呼び出しを行うように変更（`set_process_priority("high")` を利用）。

Fixed / Behavior clarifications
- .env パーサの堅牢化
  - `export KEY=...` 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、クォートなしでのインラインコメント判定の改善などを実装。
- run_monitoring のポーリング間隔の検証
  - 環境変数 `MONITOR_POLL_INTERVAL` が不正（非数値や 0 以下）の場合は警告を出してデフォルト（60 秒）にフォールバックするように修正。0 以下を time.sleep に渡してしまう問題を回避。
- データベース接続とクリーンアップ
  - run_execution/run_monitoring は例外や割り込み時に SQLite / DuckDB 接続を確実にクローズするように実装。
- Execution 起動安全性
  - run_execution は停止フラグ（data/stop_requested.flag）が既に立っている場合は起動を中止。起動後に停止フラグを検知した場合は Engine.stop() を呼び安全終了する。

Security / Safety notes
- config_setup で生成される .env は機密情報（J-Quants トークン、Kabu API パスワード等）を含むため、コメントで Git コミット禁止を明示。
- validate_config の本番（KABUSYS_ENV=live）に関する追加ガード（LINE 通知未設定・KILL_FLAG_CLEAR_ON_START の危険性を警告）を実装。

Known limitations / TODOs
- research/factor_research.py は一部実装が途中（ファイル末尾が断片）で、完全なファクター計算ロジックは未完。
- position_sizing の price 欠損時の挙動（price が 0.0 の場合にエクスポージャー過小評価される点）について注記と TODO を残している（フォールバック価格の検討予定）。
- 単元株（lot_size）の将来的な銘柄別対応（stocks マスタへの拡張）がメモに残っている。
- 監視（monitoring）関連の DB スキーマ（init_monitoring_db）や SystemMonitor の内部実装は別モジュールに分離されているが、ここには含まれているファイルの参照のみ。

---

今後のリリースでは、research の完成、より詳細な E2E テスト、Telemetry/Alerting の強化、各種パラメータの設定可能化（YAML / コンフィグ反映）などを予定しています。必要であれば、この CHANGELOG を元にリリースノート（英語／より詳細な技術仕様）を作成します。