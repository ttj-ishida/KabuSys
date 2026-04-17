# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog 標準に準拠しています。セマンティック バージョニング (SemVer) を採用します。

## [0.1.0] - 初回リリース
最初の公開リリースです（コードベースから推測した主要機能・変更点を列挙しています）。

### 追加 (Added)
- 実行スクリプト
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading 用 DB（デフォルト: data/paper_trading.db）に記録することで本番 DB と完全に分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止制御: data/stop_requested.flag を監視して安全に停止。PID ファイルの管理（data/execution.pid）。
    - スレッドで engine.run_session を起動し、停止要求を検知したら engine.stop() を呼び出して終了を待機。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用する（monitoring 用初期化を実行）。
    - 起動時にプロセス優先度を "high" に設定。停止フラグ検知でループを終了。

- 設定管理
  - config.py: 環境変数 / .env ロードと Settings クラスを導入。
    - プロジェクトルート検出 (.git または pyproject.toml) を元に .env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパース機構を実装（export プレフィックス、クォート文字列、バックスラッシュエスケープ、行内コメント処理に対応）。
    - Settings クラスで各種設定をプロパティとして提供（DB パス, PAPER_FILL_MODE, paper_sqlite_path, PID/KILL flag パス, リソース閾値、環境判定メソッド等）。
    - env 値の基本的な妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。

- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - J-Quants / kabuAPI / DB パス / LINE 設定などの簡易設定フロー。シークレットは表示をマスクして入力。
    - .env の安全な書き出しテンプレートを提供（Git にコミットしないよう注意喚起）。
  - validate_config.py: 起動前の設定検証 CLI を追加。
    - 必須環境変数の確認、KABUSYS_ENV の妥当性、LOG_LEVEL、DB パスの親ディレクトリ確認、config/*.yaml の存在チェックと（PyYAML があれば）パース検証。
    - --strict オプションで警告を FAIL 扱いにできる。

- モニタリング / DB
  - init_monitoring_db 呼び出し箇所を run_* スクリプトに追加（監視用テーブルが存在することを保証する冪等初期化）。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順で上位 N 件取得（同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。スコア合計が 0 の場合は等金額にフォールバックして警告を出力。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有比率が閾値を超えるセクターの新規候補を除外）。"unknown" セクターは制限対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 発注株数決定ロジック（risk_based / equal / score の割当方式をサポート）。
    - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer による保守的見積り、残余キャッシュを考慮した再配分ロジックを実装。

- 研究用ファクター計算
  - research/factor_research.py:
    - DuckDB を用いたファクター計算モジュールを追加。
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR20）、流動性（20 日平均売買代金、出来高比）等を計算する関数を提供。
    - 入出力は DuckDB 接続と日付、戻り値は (date, code) をキーとする辞書リスト。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシなどを計算。
    - デフォルト DB: data/paper_trading.db。また --db/環境変数で指定可能。
    - 基準値（稼働率 99%、fill 90%、send 95%、P95 latency 200ms）に基づく PASS/FAIL 判定を実装。

- ユーティリティ
  - utils/process_priority.py:
    - クロスプラットフォーム（Windows / POSIX）対応のプロセス優先度設定ユーティリティを追加。
    - set_process_priority(level) で high/normal/low を設定。psutil の利用、権限不足や未サポート環境では警告を出してスキップ。
    - set_cpu_affinity(cpu_count) により最初の N コアにプロセスを固定する機能を提供（未指定時は全コア使用、無効時はスキップ）。
  - その他ユーティリティ初期ファイル追加。

- パッケージ初期化
  - __init__.py: パッケージ名・バージョンを定義（__version__ = "0.1.0"）。主要サブパッケージを __all__ に列挙。

### 変更 (Changed)
- なし（初回リリース想定）。

### 修正 (Fixed)
- なし（初回リリース想定）。

### セキュリティ (Security)
- なし（コードベースから確認できる顕著なセキュリティ修正はなし）。

---

注記・実装上の注意点（コードの挙動から推測）
- .env の自動ロードはプロジェクトルートを基準に行われるため、CWD に依存しない挙動を期待できる。ただしプロジェクトルートが検出できない場合はロードがスキップされる。
- .env のロードでは OS 環境変数が優先され、.env.local は .env を上書きする挙動（protected 機構により既存 OS 環境は上書きされない）。
- run_monitoring は MONITOR_POLL_INTERVAL に不正な値（0 以下や非整数）が渡された場合に警告を出してデフォルト 60 秒にフォールバックする。
- position_sizing のスケーリングや rounding ロジックは lot_size 単位での配慮、cost_buffer を使った保守的なコスト見積りを行う。price 欠損時はログ出力してスキップする実装があるため、呼び出し側は price_map/open_prices の完全性に留意すること。
- apply_sector_cap は "unknown" セクターを制限対象外としている（データ不足で意図せずブロックされないよう配慮）。
- validate_config は PyYAML が未導入でも動作するが、YAML 内容検証はスキップされるため、CI 等では PyYAML の導入を推奨。

もし特定の項目（例: 各モジュールの詳細な変更履歴や将来のリリースノート形式）が必要であれば、コード差分・コミットログに基づいてリリース単位でのより細かな CHANGELOG を作成できます。