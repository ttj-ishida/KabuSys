CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
（コードベースから推測して作成しています。実際のコミット履歴とは差異がある可能性があります。）

フォーマット:
- Unreleased: まだリリースされていない変更
- 各バージョン: 主要な追加・変更・修正を分類して記載

---------------------------------------------------------------------

## [Unreleased]

- なし

---------------------------------------------------------------------

## [0.1.0] - 2026-04-24

概要:
初期リリース。日本株自動売買フレームワークの基本コンポーネントを実装。
監視（monitoring）、実行エンジン（execution）、設定管理、ポートフォリオ構築、解析ツール等の主要機能を含む。

主要な追加
- 起動スクリプト
  - run_monitoring.py を追加
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告を出力。
    - 停止フラグファイル（data/stop_requested.flag）を監視して安全にループを終了。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する（監視データは本番 DB を参照）。
  - run_execution.py を追加
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離。
    - 停止フラグと execution.pid に対応し、別スレッドでエンジンを実行。停止フラグ検知でエンジンを停止し安全終了。

- 設定・環境管理
  - config.py を追加
    - .env 自動ロード（プロジェクトルート検出: .git または pyproject.toml を起点）。
    - .env 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等）。
    - Settings クラスを提供し、主要な設定（J-Quants / kabu / DB パス / paper_trading 用 DB / 監視閾値など）をプロパティ経由で安全に取得。
    - 環境変数値の検証（PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV の値検証、LOG_LEVEL の検証など）。
  - config_setup.py を追加
    - 対話式ウィザードで .env を初期作成・更新する CLI を提供。
    - シークレット値はマスク表示、既存 .env の読み込み・デフォルト値の利用に対応。
    - 出力される .env のテンプレートを定義（J-Quants、kabu、DB、LINE、ログ、Kill Switch 等）。
  - validate_config.py を追加
    - 起動前に .env と config/*.yaml の不足や設定ミスを検出する CLI。
    - 必須環境変数チェック、KABUSYS_ENV の警告（live の場合は注意喚起）、YAML ファイルの存在・パース検証（PyYAML が存在する場合）。
    - --strict オプションで警告をエラー扱いにできる。

- 監視・モニタリング
  - monitoring_db の初期化（init_monitoring_db）呼び出しを各起動スクリプトで実行し、監視テーブルの存在を保証（冪等）。
  - run_monitoring が sqlite3 と duckdb のコネクションを使用してループ実行。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py を追加
    - すべての起動スクリプトで共通利用できるログ設定ユーティリティ。
    - StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログレベル・ログディレクトリの解決順を明記（引数、環境変数、デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - stdout を使用することで外部ジョブスケジューラとのリダイレクト運用を容易に。
  - utils/process_priority.py を追加
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - psutil を使って nice / priority を設定。アクセス権限不足や未対応 OS では警告を出力してスキップ。
    - CPU affinity 設定関数 set_cpu_affinity も提供（指定が None の場合は何もしない）。

- ポートフォリオ構築（純粋関数）
  - portfolio パッケージを追加
    - portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順で上位 N 件抽出。
      - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分。
      - スコアが全て 0 の場合は等金額配分にフォールバック（警告）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限ロジック（既存保有を考慮して候補を除外）。
      - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear で 1.0/0.7/0.3、未知レジームはフォールバック 1.0）。
      - Unknown セクターはセクター上限チェックの対象外。
    - position_sizing.py
      - calc_position_sizes: allocation_method（risk_based, equal, score）に応じて銘柄ごとの発注株数を計算。
      - 単元株（lot_size）丸め、per-stock 上限（max_position_pct）、aggregate cap（available_cash）でのスケーリング、cost_buffer を用いた保守的見積りを実装。
      - スケーリング時の端数処理（lot 単位の残差を大きい順に追加配分）を実装。
      - 価格欠損時はスキップしてログ出力。

- リサーチ / ファクター計算
  - research/factor_research.py を追加（未完の一部を含むが主要設計を実装）
    - Momentum、Value、Volatility、Liquidity などの計算を行う方針を実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。
    - 指標計算用のパラメータ定数（期間等）を定義。

- ツール
  - tools/paper_verification_report.py を追加
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標を集計して検証レポートを出力。
    - 集計指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率、P95 レイテンシ、リスク却下数。
    - 閾値（デフォルト）を定義し PASS/FAIL を判定（稼働率>=99%、注文成功率>=90% 等）。
    - 日付フィルタ対応（--from / --to）、コマンドラインから DB パス指定可能。
    - レポートで欠損データは N/A 表示。

- パッケージメタ
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - パッケージの __all__ を定義（data, strategy, execution, monitoring）。

改善・注意点（実装上の考慮）
- .env パーサー
  - export プレフィックス、クォート内部のバックスラッシュエスケープ、インラインコメントの取り扱いをサポート。より堅牢な自動ロードを実現。
- 設定の安全性
  - Settings._require により必須環境変数が未設定の場合は ValueError を送出（起動前に明確に失敗）。
  - validate_config により起動前に設定ミスを検出しやすくした。
- ロギング
  - ログディレクトリ作成失敗やファイルハンドラ作成失敗時に落ちずにコンソールのみで継続するフェイルセーフを実装。
  - stdout を使うことで外部のログ収集・リダイレクトと相性が良い設計。
- プロセス優先度
  - 実行開始直後に高優先度を要求する設計（set_process_priority("high") を各起動スクリプトで呼び出す）。権限やプラットフォームにより設定に失敗した場合は警告でフォールバック。
- Paper Trading の分離
  - paper_trading モードは本番 DB と完全分離（専用 SQLite）することでテスト時の誤発注リスクを軽減。
- 監視 DB
  - 監視テーブルの初期化は起動時に必ず行う（冪等実装）。Monitoring は意図的に本番 sqlite_path を参照する仕様。

既知の制約・TODO（コード中注記に基づく）
- position_sizing.calc_position_sizes の price 欠損時の挙動は暫定（price が欠損するとエクスポージャーが過小見積りされる可能性あり）。将来的に前日終値や取得原価でのフォールバックを検討。
- research/factor_research.py はファイル末尾で未完（コメントで続きが示唆されている）。実装の続きが必要。
- 一部のモジュールは外部依存（psutil, duckdb, PyYAML 等）に依存しており、環境により機能制限や警告が発生する。

セキュリティ
- 機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は .env に保存する前提。config_setup で .env にシークレットを保存する旨を明記し、.env を Git にコミットしない旨の注意を出力。

---------------------------------------------------------------------

注:
- 本 CHANGELOG は提示されたソースコードから機能・意図を推測して作成しています。実際のコミット差分や履歴は別途 Git の履歴等を参照してください。