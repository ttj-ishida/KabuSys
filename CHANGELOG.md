Keep a Changelog に準拠した CHANGELOG.md（日本語）
※この変更履歴は、提示されたコードベースの内容から推測して作成しています。

All notable changes to this project will be documented in this file.
The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-20
初回リリース。以下の主要コンポーネントと機能を追加。

### Added
- 全体
  - パッケージ初期版を追加。バージョンは kabusys.__version__ = "0.1.0"。
  - Python パッケージ構成（src/kabusys）および複数のサブモジュールを導入。

- 設定管理
  - Settings クラス（src/kabusys/config.py）を導入し、環境変数から設定値を取得する統一インタフェースを提供。
  - 自動 .env ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。読み込み順: OS 環境 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルパーサを実装:
    - export KEY=val 形式に対応
    - シングル／ダブルクォートのエスケープ処理、インラインコメントの扱いなどを考慮
    - override / protected オプションで既存 OS 環境変数を保護
  - 設定項目には J-Quants / kabu API / LINE / DB / 監視閾値 などを網羅。PAPER_FILL_MODE の有効値制約（instant/partial/never/reject）を実装。

- 起動・運用用スクリプト
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を追加:
    - KABUSYS_ENV による paper_trading (専用 SQLite DB) と live の切り替え対応
    - BrokerClientFactory によるブローカークライアントの生成（paper_trading では MockBrokerClient を使用する設計）
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立て・起動ロジック
    - 停止フラグ（data/stop_requested.flag）検出時の安全停止、PID ファイル管理
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を追加:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き（デフォルト 60 秒）
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する方針
    - SystemMonitor の単発チェックをループで実行。停止フラグ検出、例外捕捉、リソースクローズ処理を実装

- 監査・ユーティリティ
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加:
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在/パースチェック
    - --strict オプションで警告を失敗扱いにできる
  - 環境設定ウィザード（src/kabusys/config_setup.py）を追加:
    - 対話式に .env を生成・更新するウィザード。秘密項目はマスク表示、選択肢／デフォルト対応。生成テンプレートは .env に書き込む
  - ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加:
    - stdout への StreamHandler と 日次ローテーション（TimedRotatingFileHandler）を組み合わせてルートロガーを統一設定
    - ログディレクトリ作成失敗時はファイルロギングをスキップし stdout のみで継続。バックアップ保持 30 日。
    - LOG_LEVEL / LOG_DIR の解決順を明示
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加:
    - Windows / POSIX の差分を吸収して優先度を設定（high/normal/low）
    - CPU affinity 固定機能（set_cpu_affinity）を提供
    - psutil の権限不足など失敗時は警告出力してスキップ

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: BUY シグナルのスコア降順選抜（タイブレーク: signal_rank）
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア正規化配分（全スコア 0 の場合は等配分へフォールバック・警告）
  - risk_adjustment（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値を超えるセクターの新規候補を除外）
      - unknown セクターは制限対象外
      - sell_codes（当日売却予定）をエクスポージャー計算から除外
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームは 1.0 でフォールバック）
  - position_sizing（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes:
      - allocation_method: "risk_based" / "equal" / "score" をサポート
      - lot_size（単元株）で丸め、max_position_pct / max_utilization / cost_buffer を考慮した上で aggregate cap によるスケーリング実装
      - スケールダウン時の端数配分アルゴリズム（fractional remainder に基づく再配分）を実装
      - 価格欠損時のスキップやログ出力、0 価格保護など

- リサーチ / ファクター計算
  - factor_research（src/kabusys/research/factor_research.py）を追加:
    - ドキュメントと定数群（モメンタム、MA200、ATR、出来高等）を実装
    - calc_momentum 関数の準備（prices_daily テーブルを用いる設計）。（ファイル末尾は実装途中の状態で存在）

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）を追加:
    - PAPER_TRADING_SQLITE_PATH / --db オプションで DB を指定してレポート生成
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ、リスク却下数
    - Pass/Fail 基準の閾値を定義（稼働率 >= 99%、fill >= 90%、send >= 95%、P95 <= 200 ms）
    - 各クエリはテーブル欠如時に例外を扱いデフォルト値で継続
    - CLI で期間フィルタ (--from / --to) を指定可能

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- .env を絶対に Git 管理下に置かない旨を config_setup のヘッダに明記

### Notes / Behavioural details / 注意点
- run_monitoring は「監視用 DB に常に本番 sqlite_path を使う」方針（settings.env に依存せず）。運用者は意図的な動作であることを留意すること。
- run_execution は paper_trading 環境時に data/paper_trading.db を使うよう設計され、本番 DB と完全分離することを想定。
- process_priority / cpu affinity の設定は権限やプラットフォームに依存するため、失敗時は警告出力して処理を継続する実装。
- .env パーサは柔軟に設計されているが、特殊なケース（複雑な multiline や非標準形式）では想定外の動作となる可能性あり。
- factor_research モジュールの実装は途中の箇所があり、完全なファクター計算は今後追加予定。

--------------------------------------------------------------------
過去のリリース履歴（もしあればここに追記してください）。