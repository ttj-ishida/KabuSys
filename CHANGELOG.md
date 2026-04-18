# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システム KabuSys の基礎機能を実装しました。

### Added
- コア設定・環境変数管理
  - Settings クラスを実装し、環境変数（.env / .env.local / OS 環境変数）からアプリ設定を取得する機能を提供。
  - 自動 .env ロード機能（プロジェクトルートの検出:.git または pyproject.toml）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
  - .env のパース機能を強化（export プレフィックス対応、クォート文字列のエスケープ、行内コメント扱いなど）。
  - 設定値の検証ロジック（ログレベル・KABUSYS_ENV 等の妥当性チェック）を実装。

- 起動・運用用スクリプト / CLI
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine の起動・停止ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）検知により安全に停止。
    - PID ファイル管理（data/execution.pid）対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔の上書きが可能（デフォルト 60 秒）。
    - 監視用 DB（監視テーブル）は環境にかかわらず本番 sqlite_path を参照する実装。
    - 停止フラグ検知でループを終了。
  - validate_config.py: 設定検証 CLI を追加。
    - .env の必須項目チェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML があれば内容検査）。
    - --strict オプションで警告も失敗扱いにできる。
  - config_setup.py: 対話式の .env 作成 / 更新ウィザードを追加。
    - 標準項目群（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス, LOG_LEVEL, Kill Switch 関連など）を対話的に生成。
    - 既存 .env の読み込みと既存値の再利用に対応。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供（スコア合計が 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率に基づく候補除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を実装。未知レジームはフォールバックで 1.0。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数決定。
    - 単元（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金を超えた場合のスケールダウン）や cost_buffer を考慮した安全なスケーリングを実装。

- ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、保存日数 30）を設定する共通ユーティリティを追加。
    - LOG_LEVEL / LOG_DIR / app_name による設定、既存ハンドラのクリア処理を実装。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみで継続。
  - utils/process_priority.py:
    - プロセス優先度（high/normal/low）の設定ユーティリティを追加。Windows/Linux(macOS/FreeBSD) の差分吸収（psutil 利用）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供（権限不足や未対応環境では警告を出してスキップ）。
  - utils.__init__（パッケージ化）。

- モニタリング / DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を利用して監視テーブルの冪等な初期化を行う（run_execution / run_monitoring から呼び出し）。

- 分析・検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から期間指定で検証レポートを生成する CLI を追加。
    - システム稼働率、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシなどを集計し PASS/FAIL 判定を行う（閾値はソース内定義）。
    - SQL クエリの失敗（テーブル未存在等）を適切に扱うフェイルセーフ処理を備える。

- research/factor_research.py（ファクター計算の基礎）
  - DuckDB を用いたモメンタム等ファクター計算基盤を追加（関数雛形と定数を実装、prices_daily/raw_financials を参照する設計）。

- パッケージ情報
  - パッケージの __version__ を "0.1.0" に設定。

### Changed
- ロギング挙動
  - StreamHandler は stdout に出力するようにして、cron 等で stdout/stderr を一本化してリダイレクトしやすくした。
  - 既存ハンドラをクリアしてから再設定することで二重ログ出力を防止。

- .env 読み込み順序と保護
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は既存 OS 環境変数を上書きするが保護セットにより OS 側のキーは上書きされない）。
  - .env の読み込み失敗時は警告を発行して継続する（テストでの柔軟性向上）。

### Fixed
- 環境変数パースの堅牢化
  - _parse_env_line にて export プレフィックスやクォート内のエスケープ、行内コメントの扱いを正しく処理するように実装。これにより複雑な .env 値やコメント混在時の誤読を防止。

- 実行時の安全性強化
  - run_execution / run_monitoring で停止フラグ（data/stop_requested.flag）を監視し、安全に停止するロジックを追加。
  - DB 接続後の finally ブロックで確実に接続を閉じるように修正。

### Security
- .env に関する注意喚起を config_setup のヘッダに明記（.env を Git に絶対にコミットしないこと）。
- 環境変数必須項目の未設定時に検出して起動前にエラーを出す validate_config を用意し、本番デプロイ前の設定漏れを減らす。

### Documentation
- 各モジュールに docstring と使用例、設計意図・注意点を明記（PortfolioConstruction.md / StrategyModel.md などドキュメント参照に基づいた実装方針を注記）。

### Removed
- なし

---

注: 上記は現行コードベースの実装内容から推測して作成した CHANGELOG です。機能の詳細・実際のマイナーバージョン管理方針に応じて適宜編集してください。