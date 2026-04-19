# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: 以下の変更点は提示されたコードベースの内容から推測して作成しています。

## [Unreleased]

- ドキュメント・小さな改善やテスト用の変更をここに記載してください。

---

## [0.1.0] - 2026-04-19

初回リリース。シンプルな日本株自動売買システムのコアユーティリティ、実行/監視ランナー、設定管理、ポートフォリオ構築、検証ツールを実装しました。

### Added

- 基本パッケージ
  - パッケージ初期化とバージョン管理（kabusys.__version__ = "0.1.0"）。

- 実行用ランナー
  - src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db デフォルト）を使用して本番 DB と分離。
    - ブローカーは BrokerClientFactory で作成（実運用／モック選択を透過的に切り替え）。
    - エンジンはデーモンスレッドで実行され、プロセス内の停止フラグ（data/stop_requested.flag）検知で安全に停止。
    - 実行時にプロセス優先度を "high" に設定する処理を呼び出す。

- 監視用ランナー
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視テーブルを記録する設計。
    - 停止フラグを検知するとループを終了し、DB 接続をクローズして終了。

- 設定管理
  - src/kabusys/config.py
    - .env の自動ロード機構を実装（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
    - .env 読み込みの詳細なパース実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い等対応）。
    - 環境変数必須チェック用ヘルパー _require と Settings クラスを提供。多数のプロパティ（J-Quants, kabu API, DB パス, PID/kill flag パス, モニタ閾値, 環境種別判定等）を用意。
    - PAPER_FILL_MODE のバリデーション（"instant" / "partial" / "never" / "reject" のみ許可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト向け）。

- 設定ウィザード & 検証 CLI
  - src/kabusys/config_setup.py
    - 対話式で .env を初期作成・更新するウィザード。
    - シークレット項目を隠して表示し、.env を安全に書き出す（Git にコミットしない旨の注意文を出力）。
  - src/kabusys/validate_config.py
    - 起動前に .env および config/*.yaml の簡易チェックを行う CLI。
    - 必須環境変数の有無、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、PyYAML があれば YAML ファイルのパース検証を実行。
    - --strict オプションで警告を FAIL として扱うことが可能。

- ポートフォリオ構築ライブラリ（純関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定(select_candidates) と重み計算 (calc_equal_weights, calc_score_weights) を実装。スコアが全て 0 の場合は等金額配分にフォールバックし警告を出力。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を実装。既存保有・当日売却予定を考慮し、"unknown" セクターは上限適用対象外とする仕様。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull":1.0, "neutral":0.7, "bear":0.3、未知のレジームは 1.0 にフォールバックして警告）。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（allocation_method: "risk_based", "equal", "score"）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を使った保守的見積り、端数処理（残余キャッシュで lot_size 単位の追加配分）などを実装。

- ロギング & プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler を stdout に設定し、TimedRotatingFileHandler（デフォルト logs/<app_name>.log、日次ローテーション、30 日分保持）を追加するヘルパー。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続する耐障害性を実装。
    - ログレベルは引数 > 環境変数 > デフォルト の順に解決。
  - src/kabusys/utils/process_priority.py
    - psutil を使い Windows / POSIX 系でプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）と CPU affinity を設定するユーティリティ。対応外 OS やアクセス権限不足は警告を出してスキップ。

- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の SQLite（PAPER_TRADING_SQLITE_PATH 指定可）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ等）を集計してレポート出力する CLI。
    - デフォルトの合格基準（稼働率 >= 99%, 成功率 >= 90%, 送信率 >= 95%, P95 レイテンシ <= 200 ms）を実装し、PASS/FAIL 判定を出力。
    - 日付範囲フィルタ（--from / --to）をサポート。DB スキーマが存在しない場合もエラーを吐かずに N/A 等で扱う堅牢性を持たせている。

- 研究用ファクター計算（開発中）
  - src/kabusys/research/factor_research.py
    - DuckDB 接続を受け、momentum/value/volatility/liquidity 等のファクターを計算するための骨組みを追加。
    - 200 日移動平均や ATR, リターン計算等の定義とスキャンウィンドウの定数を定義。実装は続行中（注記あり）。

### Changed

- （初回リリースのため該当なし）将来的な仕様変更がある場合はここに追記してください。

### Fixed / Hardening

- .env パースロジックを堅牢化
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの扱いを実装し、現実の .env フォーマットの差異により強く耐えるようにしました。
  - 自動ロード時に OS 環境変数を保護する protected 機構を導入（.env.local の上書き等で OS 側の変数を壊さない）。

- ログ設定のフォールバック
  - ログディレクトリ作成やファイルハンドラ生成に失敗してもコンソール出力で継続するようにして、起動不能に陥らないようにしました。

- プロセス優先度 / CPU affinity の安全な適用
  - 未対応 OS や権限不足時に例外を投げず警告ログでスキップするようにし、安全に起動できるようにしました。

- DB 初期化の冪等性
  - run_execution / run_monitoring 起動時に monitoring 用テーブルの初期化関数 init_monitoring_db を呼び、テーブルが存在しない場合でも安全に作成されるようにしました。

### Security

- 機密情報の扱い
  - config_setup でシークレット項目は対話時に表示をマスクし、.env 生成時にも "絶対に Git にコミットしないこと" の注意文を出力しています。
  - 環境変数未設定時は Settings._require で ValueError を発生させるため、必須トークンが空のまま実行されることを未然に防止します。

---

開発中の事項・今後の予定（推測）
- research/factor_research.py の関数実装を完了し、DuckDB を用いたファクター計算パイプラインを整備する予定。
- Strategy / Execution のさらなるテストと例外ハンドリング強化（ネットワーク障害、DB ロックなどへの耐性強化）。
- 単体テスト・統合テストの整備、および CI 上での自動検証。
- ドキュメント（README、運用手順書、PortfolioConstruction.md 等）の充実。

※ 本 CHANGELOG はコード内容から推測して作成したものであり、実際のリリースノートとは異なる可能性があります。必要に応じて差し替え・補足してください。