Keep a Changelog 準拠の変更履歴を以下に作成しました。コードベースの内容から推測して記載しています。リポジトリの実際の履歴やコミットメッセージに基づくものではなく、ソースコードの実装内容を元に機能追加・変更点・既知の制限などをまとめています。

CHANGELOG.md
=============
すべての変更は https://keepachangelog.com/ja/ に準拠しています。

フォーマット:
- 変更はセマンティックバージョニングを前提にしています。
- 日付は本ファイル生成日（2026-04-18）を用いています（実際のリリース日が異なる場合は適宜置換してください）。

Unreleased
---------
- （なし）

[0.1.0] - 2026-04-18
--------------------
Added
- 実行用スクリプト群を追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite(DB) を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler の組み立てと ExecutionEngine の起動処理を実装。
    - ストップフラグ（data/stop_requested.flag）検出による安全停止処理を実装。
    - 実行用 PID ファイル管理（data/execution.pid への書き込み/参照を想定）。
    - プロセス優先度を High に設定する初期処理を追加（utils.process_priority）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用 sqlite_path を参照する仕様（環境に依存しない監視 DB 利用）。
    - 停止フラグ（data/stop_requested.flag）検出でループ終了。
    - 例外発生時のログ捕捉とループ継続処理を実装。

- 設定・環境周りのユーティリティを追加
  - config.py
    - .env ファイルの自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml に基づく）。
    - .env パーサーは export 形式、クォート有無、エスケープ、インラインコメント等に対応する堅牢な実装。
    - Settings クラスを導入し、各種環境変数（J-Quants, kabuAPI, DB パス, ペーパートレード設定, 監視閾値, ログレベル 等）をプロパティ経由で取得。
    - 環境変数の必須チェックで未設定時は ValueError を送出する _require 関数を提供。
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の検証を実装。

  - config_setup.py
    - 対話式ウィザードで .env を初期作成/更新する CLI。
    - 秘密情報のマスク表示、選択肢・デフォルト提示、既存 .env の取り込み機能を実装。
    - --env-file による保存先指定をサポート。

  - validate_config.py
    - 起動前検証 CLI。必須環境変数や設定ファイル（config/*.yaml）の存在・簡易パースをチェック。
    - --strict モードで警告を失敗扱いにするオプション。
    - 本番（KABUSYS_ENV=live）向けのガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の注意喚起）を実装。
    - PyYAML 未インストール時は YAML 内容検証をスキップして警告。

- ロギング・プロセス周りのユーティリティを追加
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション）を設定する共通セットアップ関数 setup_logging を提供。
    - LOG_LEVEL/LOG_DIR の解決順、既存ハンドラのクリーンアップ、ログディレクトリ作成失敗時のフォールバックを実装。
    - stdout を使用することでスケジューラ等からのログリダイレクトを想定。

  - utils/process_priority.py
    - psutil を利用して Windows/Linux/macOS 間の差分を吸収するプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告ログでスキップし安全に動作。

- ポートフォリオ構築モジュールを追加（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順かつタイブレークに signal_rank を利用して候補選定。
    - calc_equal_weights / calc_score_weights: 正規化とスコア全ゼロ時のフォールバック（等配分）を実装。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別の既存エクスポージャーを計算し、1セクター上限を超える場合は当該セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた乗数を返す。未知レジームは警告のうえ 1.0 でフォールバック。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に従い、単位株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash）に対するスケーリング、cost_buffer を用いた保守的見積りなどを実装。
    - スケールダウン時の端数配分アルゴリズムを実装（fractional remainder に基づく lot_size 単位の追加配分）。

- Paper Trading 用検証ツールを追加
  - tools/paper_verification_report.py
    - ペーパートレーディングの SQLite DB（デフォルト: data/paper_trading.db）からシステム安定性、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計してレポート出力。
    - CLI オプションで期間（--from, --to）および DB パス（--db）を指定可能。
    - 合格判定 (PASS/FAIL) のしきい値定義を実装（稼働率、成立率、送信率、P95 レイテンシ等）。

- 研究用モジュール（雛形）を追加
  - research/factor_research.py
    - モメンタム等のファクター計算の設計と一部実装（定数、関数の枠組み、calc_momentum の冒頭実装）を追加。
    - DuckDB を用いた prices_daily / raw_financials に基づく計算を想定。

- パッケージ初期設定
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （特記事項なし）

Notes / Known limitations / TODO
- research/factor_research.py は途中で切れている箇所があり、ファクター計算の完全実装が未完（calc_momentum の続きや他ファクターの実装が必要）。
- position_sizing.py のコメントにあるように銘柄ごとの単元株（lot_size）のマスタ対応は未実装（現在は全銘柄共通の lot_size を前提）。
- risk_adjustment.apply_sector_cap: price_map に価格が欠損（0.0）の場合にエクスポージャーを過小見積りする可能性がある旨の TODO がある（前日終値や取得原価などのフォールバックが将来的に必要）。
- run_monitoring は Monitoring 用 DB に常に本番 sqlite_path を使用する仕様（設計上の意図）。運用時は監視 DB の配置に注意。
- 一部外部依存（psutil, duckdb, PyYAML 等）が存在。実行環境にインストールされていない場合は該当機能が制限される（validate_config は PyYAML 未導入時に YAML 検証をスキップ）。

以上

必要であれば次を対応できます:
- 日付やバージョンを実際のリリース情報に合わせて更新
- 各ファイルごとの詳細な変更点（関数ごとの説明、既知のバグのチケット参照など）を追加
- 英語版 CHANGELOG の作成