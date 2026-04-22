CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

[Unreleased]
------------

- （現時点のコードベースは初回リリース相当のため未リリースの差分はありません）

[0.1.0] - 2026-04-22
-------------------

Added
- 実行スクリプトを追加
  - run_execution.py
    - ExecutionEngine の起動スクリプトを提供。プロセス優先度を "high" に設定して起動する。
    - KABUSYS_ENV が paper_trading の場合は paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用し本番 DB と分離。MockBrokerClient を利用する想定（BrokerClientFactory 経由）。
    - init_monitoring_db により監視テーブルの存在を保証。
    - Engine を別スレッドで実行し、プロジェクトルートの data/stop_requested.flag により安全に停止できる。実行時に実行 PID を data/execution.pid に保存する仕組みを想定。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを提供。デフォルトのポーリング間隔は 60 秒。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（不正値は警告を出してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する設計（monitoring 用 DB 初期化を実行）。
    - stop フラグでループを終了し、例外発生時はログ出力して次ポーリングに備える。

- 設定・環境変数管理
  - config.py
    - プロジェクトルート（.git または pyproject.toml）を基準に .env を自動読み込み（.env, .env.local の優先順）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサを実装:
      - export KEY=val 形式に対応
      - シングル/ダブルクォートの値内でのバックスラッシュエスケープ処理を考慮
      - クォートなし値のインラインコメント判定は直前が空白/タブのときのみコメントとみなすなど堅牢化
    - Settings クラスを提供（各種環境変数の取得・バリデーションメソッドを備える）
      - J-Quants / kabu API / LINE / DB パス / 監視しきい値 / ログ設定等のプロパティを提供
      - KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の妥当性チェックを実装
    - settings = Settings() のシングルトンを公開

  - config_setup.py
    - 対話式ウィザードで .env の作成・更新を支援する CLI を追加
    - 各項目の説明、デフォルト、選択肢、シークレット表示（マスク）に対応し、最終確認後に .env を書き出す
    - .env の既存値読み込み・上書きルールをサポート

  - validate_config.py
    - 起動前に .env および config/*.yaml の設定を検証する CLI を追加
    - 必須環境変数の未設定チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証を行う
    - --strict オプションで警告も FAIL 扱いにできる
    - live 環境時の追加ガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の危険性）を実装

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保存）を設定するユーティリティを追加
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続
    - ログレベル・ログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）を提供
  - utils/process_priority.py
    - psutil を用いて Windows / POSIX（Linux/Mac/FreeBSD）間の差分を吸収するプロセス優先度設定を実装
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ

- ポートフォリオ構成 / リスク調整 / 口数決定（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選択
    - calc_equal_weights: 等金額配分（1/N）
    - calc_score_weights: スコア比率で正規化。全スコアが 0 の場合は等配分にフォールバックして WARNING を出力
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外（"unknown" セクターは除外対象にしない）
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（"bull"=1.0, "neutral"=0.7, "bear"=0.3）、未知レジームは 1.0 にフォールバックして WARNING
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に応じた発注株数算出を実装
      - risk_based: 許容リスク率・損切り率に基づくロット算出
      - equal/score: 重み・max_utilization 等に基づく算出
      - 単元株（lot_size）で丸め、1 銘柄上限および全体の aggregate cap（available_cash）超過時のスケーリング、cost_buffer を考慮した保守的推定、端数配分の再割当てロジックを実装
      - 価格欠損時のスキップやログ出力に対応

- リサーチ（ファクター算出）スケルトン
  - research/factor_research.py
    - モメンタム等ファクター計算用の定数・関数群を追加（DuckDB 接続を想定した設計）
    - calc_momentum の実装開始（prices_daily を参照して 1M/3M/6M リターンや MA200 乖離率を計算する方針）。（ファイル末尾で実装途中に見切れている箇所あり）

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite を集計して検証レポート（稼働率、注文成功率、送信率、レイテンシ指標（P95）など）を生成する CLI を追加
    - デフォルトしきい値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を持ち、Pass/Fail 判定を出力
    - 日付フィルタ、DB パスの CLI オプションをサポート
    - P95（95パーセンタイル）の算出ロジックを実装

- パッケージ情報
  - __init__.py にて __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated
- 該当なし

Removed
- 該当なし

Security
- 該当なし

Notes
- calc_momentum（factor_research.py） は実装が途中の箇所が見られます。今後のリリースでファクター計算ロジックの完成を予定しています。
- run_monitoring/run_execution はローカルファイル（data ディレクトリ内）の存在・パーミッション等に依存するため、運用時は .env の設定・ディレクトリ作成を事前に行ってください（config_setup と validate_config を推奨）。
- ログディレクトリ作成やプロセス優先度設定は権限が不足していると失敗することがあります。いずれも失敗した場合は警告ログを出し、処理は継続されます。