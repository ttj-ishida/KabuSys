CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
セマンティック バージョニングを採用しています。

Unreleased
----------

- 今後の改善候補（ドキュメント、テスト、性能改善、factor_research の実装拡張 など）。

[0.1.0] - 2026-04-19
--------------------

Added
- 基本アプリケーション骨格を追加（初期リリース）。
  - 実行スクリプト:
    - run_execution.py: ExecutionEngine を起動するエントリポイントを実装。KABUSYS_ENV=paper_trading 時に専用の Paper Trading DB を利用するよう分離。停止フラグ検出、PID ファイル管理、デーモンスレッドでのエンジン実行をサポート。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出で安全に停止。
  - 設定管理:
    - config.py: .env の自動ロード（.env < .env.local の優先度）と Settings クラスによる環境変数ラッパーを実装。必須値チェック、KABUSYS_ENV/LOG_LEVEL の検証、Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH など）を含む。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI を実装。機密値はマスク表示し、例外時は中断して変更を保存しない。
    - validate_config.py: .env と config/*.yaml の起動前検証 CLI を実装。--strict モードで警告を FAIL 扱いにできる。
  - ロギング / プロセス管理ユーティリティ:
    - utils/logging_setup.py: stdout StreamHandler と 日次ローテーションの TimedRotatingFileHandler を組み合わせた統一ロギング設定を実装。ログディレクトリ自動作成、LOG_LEVEL / LOG_DIR の解決ロジックを提供。
    - utils/process_priority.py: Windows/Linux（および一部 POSIX）を抽象化したプロセス優先度設定と CPU affinity 設定を実装。アクセス権限等で失敗しても安全にスキップする。
  - ポートフォリオ構築（純粋関数群）:
    - portfolio/portfolio_builder.py: 候補選定（スコア順）、等金額配分、スコア加重配分を実装。スコア全てが 0 の場合は等配分にフォールバック。
    - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジームはフォールバックで警告。
    - portfolio/position_sizing.py: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算を実装。単元株（lot_size）丸め、per-stock 上限、aggregate cap（available_cash に基づくスケーリング）、手数料スライド用 cost_buffer を考慮。
  - ツール:
    - tools/paper_verification_report.py: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計して検証レポートを出力する CLI を実装。閾値（稼働率 99%、注文成功率 90% 等）に基づく PASS/FAIL 判定を出力する。
  - 監視 DB 初期化:
    - monitoring.monitoring_db との連携により、起動時に監視テーブルの初期化（冪等）を行う処理を走らせる（monitoring と execution の両方で利用）。

Changed
- なし（初回リリース）。

Fixed
- .env 読み込み・パースの堅牢化:
  - export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱いなどをサポートするパーサを実装。空行・コメント行のスキップを実装。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。プロジェクトルート検出は .git / pyproject.toml を基準に行い、見つからない場合は自動ロードをスキップ。
- 安全性向上:
  - Execution と Monitoring の起動スクリプトで停止フラグ（data/stop_requested.flag）と Kill Switch 関連の取り扱いを実装し、誤発注等のリスクを低減。
  - run_execution では KABUSYS_ENV=paper_trading の場合に本番 DB と完全分離された paper_trading.db を使用するように実装。

Security
- config_setup の対話 UI で機密情報（J-Quants トークン、KABU API パスワード）をマスクして表示。
- .env ファイルに関する注意文言を出力（.env を Git にコミットしないよう明示）。

Documentation
- 各スクリプトと関数にドキュメンテーション文字列（docstring）を付与。使用例や引数、戻り値、既定値、挙動（フォールバックやエラー時の処理）が明記されている。

Notes / Implementation Details
- デフォルト動作・環境変数:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）。デフォルト 60。0 以下や不正な値はログ警告のうえデフォルトにフォールバック。
  - PAPER_FILL_MODE: paper_trading 用の擬似約定モード（"instant" | "partial" | "never" | "reject"）。不正値は ValueError。
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト data/paper_trading.db）。
  - DUCKDB_PATH / SQLITE_PATH のデフォルトは data/kabusys.duckdb / data/monitoring.db。
  - KILL_FLAG_CLEAR_ON_START: 起動時に Kill Flag を自動クリアするか（デフォルト 0）。本番での自動クリアは警告。
- ロギング:
  - stdout に StreamHandler、ファイルに TimedRotatingFileHandler（daily、30 日保持）を追加。ログディレクトリの作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - StreamHandler は stdout を用いる（cron/Task Scheduler のリダイレクトに配慮）。
- プロセス優先度:
  - set_process_priority("high") を起動直後に呼び出し、必要に応じて優先度設定を行う（権限不足等で失敗しても継続）。
- position_sizing の挙動:
  - risk_based: portfolio_value, risk_pct, stop_loss_pct を用いたリスクベース算出。単元株丸め、per-stock および aggregate の上限を適用。
  - equal/score: ウェイトに基づく配分。利用可能現金を超える場合はスケールダウンし、端数は lot_size 単位で再配分するロジックを持つ。

Known limitations / TODO
- research.factor_research.py はモメンタム等ファクター計算の骨格を含むが（duckdb を用いる設計）、一部実装が未完（ファイル最終で途中）であり、完全実装と単体テストが必要。
- position_sizing の price 欠損（0.0）の場合にエクスポージャーが過少見積もられる可能性がある旨の注記。将来的には前日終値や取得原価をフォールバックする拡張を検討。
- 銘柄ごとの lot_size を将来サポートするための拡張設計（stocks マスタの導入など）を検討中。
- config/*.yaml の存在チェック・パースは PyYAML が未インストールの場合はスキップされる（validate_config で注意喚起）。

Breaking Changes
- なし（初回公開）。

Authors
- KabuSys 開発チーム（コードベースから推測して記載）。

----- 

注: 本 CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実リリースではコミット履歴・実際の変更差分に基づいて正確に更新してください。