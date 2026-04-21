# CHANGELOG

すべての変更は Keep a Changelog の方針に従って記載しています。重要な変更のみを抜粋しており、コードベースの実装内容から推測してまとめています。

フォーマット:
- Unreleased: 今後の変更予定（現状は空）
- 各リリースは日付付きで記載

---

## [Unreleased]
- 今後の改善候補・未実装メモ（コード内の TODO 等）
  - 銘柄ごとの単元情報（lot_size）のマスタ化による position sizing の拡張
  - apply_sector_cap における価格欠損時のフォールバック（前日終値や取得原価の使用）
  - research/factor_research モジュールの実装継続（ファイル末尾が未完の箇所あり）
  - テストカバレッジとエンドツーエンド検証の追加

---

## [0.1.0] - 2026-04-21

Added
- パッケージ初期リリースを作成
  - バージョン: `kabusys.__version__ = "0.1.0"`
- 実行・運用用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加
    - KABUSYS_ENV により paper_trading モードでは MockBrokerClient（専用 SQLite）を使用して本番 DB と完全分離
    - 起動時にプロセス優先度を設定（high）
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理をサポート
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
    - monitoring は環境にかかわらず本番 sqlite_path を使用する挙動を採用
    - 停止フラグの検知、例外時のログ出力、リソースクローズを実装
- 環境設定・検証ツール
  - config_setup.py
    - .env の対話式ウィザードを実装（.env の初期作成・更新支援）
    - J-Quants / kabuステーション / DB パス / LINE など主要設定項目を扱う
    - 秘匿項目はマスク表示、既存 .env の読み込み・Enter で再利用対応
  - validate_config.py
    - 起動前の設定検証 CLI を追加
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在確認、config/*.yaml の存在と YAML パース検証（PyYAML がある場合）
    - --strict オプションで警告を FAIL 扱いに変更可能
- 環境変数 / 設定管理
  - config.py
    - プロジェクトルート自動検出（.git または pyproject.toml 基準）により .env 自動読み込みを実装（OS 環境変数優先、.env.local が .env を上書き）
    - export 形式やクォート値、インラインコメントの扱いに対応した .env パーサを実装
    - Settings クラスでアプリ設定をプロパティ化（J-Quants/Kabu/API/DB/監視閾値/システム設定など）
    - 環境値のバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等）
    - settings = Settings() のエクスポート
- ロギングおよびプロセス制御ユーティリティ
  - utils/logging_setup.py
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）をルートロガーに設定するユーティリティを実装
    - ログレベル・ログディレクトリ解決ロジック、既存ハンドラのクリーンアップを含む
  - utils/process_priority.py
    - Windows / POSIX を抽象化してプロセス優先度（high/normal/low）を設定するユーティリティを実装
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供
    - 実行権限不足や未対応 OS 時は安全にスキップしログ出力する設計
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を実装
    - スコア全ゼロ時は等配分にフォールバック（警告ログ）
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装
    - unknown セクターの扱い、レジームに応じた multiplier（bull/neutral/bear）を定義
    - 実装中の注意点（価格欠損時の扱い）をコメントで記載
  - portfolio/position_sizing.py
    - 各銘柄の発注株数を計算する主要アルゴリズムを実装（allocation_method: risk_based / equal / score）
    - 単元株丸め、1銘柄上限、aggregate cap (available_cash) のスケーリング、cost_buffer（手数料・スリッページ見積り）を考慮
    - スケールダウン時に残差を lot 単位で再配分するロジックを実装
- Paper Trading 検証・レポート
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数など）を集計しテキストレポートを出力するツールを追加
    - 合格基準（稼働率、成功率、送信率、P95）を定義し PASS/FAIL 判定を行う
    - 日付フィルタ、CLI オプション（--from/--to/--db）を提供
- research/factor_research.py（ファクター計算の骨格）
  - DuckDB 接続を受け取り prices_daily/raw_financials を用いる方針を実装
  - Momentum/Value/Volatility/Liquidity に関する設計と一部定数・calc_momentum の骨格を追加
  - （注）ファイル末尾で未完の箇所あり（実装継続予定）

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Security
- なし（初回リリースのため）

Notes / 実装上の注意
- .env 自動ロードはプロジェクトルートが特定できる場合のみ実行され、OS 環境変数を保護する設計（.env の上書きに対して保護リストを用いる）
- run_monitoring/run_execution は停止フラグ（data/stop_requested.flag）により安全に停止できる（外部運用での Kill Switch を想定）
- paper_trading 用 DB は本番 DB とは分離して扱う（PAPER_TRADING_SQLITE_PATH / Settings.is_paper）
- 一部ロジックに TODO コメントあり（将来的な改善点を明示）
- research/factor_research は完全実装に向けて継続中（現在は一部関数が途中）

---

今後の予定（コードからの推定）
- research/factor_research の完全実装（Momentum 等の計算処理・正規化ユーティリティ結合）
- 銘柄毎の lot_size 管理・マスタ導入による position sizing の精緻化
- CI/CD やユニットテストの追加、エンドツーエンド検証の整備
- 運用監視・アラート（LINE）の設定強化と本番用ガードの追加

--- 

（本 CHANGELOG はソースコードの内容から推測して作成しています。実際のリリースノートとして利用する際は、変更者による確認・追記を推奨します。）