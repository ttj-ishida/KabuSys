# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルは、リポジトリ内のコードから推測できる機能追加・変更点・既知の注意点をまとめたものです。

注: 日付はコード解析時点（2026-04-19）を使用しています。実際のリリース日やバージョン管理履歴に合わせて調整してください。

## [Unreleased]

- ドキュメント／リファクタ用途の軽微な注記や TODO コメントが含まれています（将来の拡張点の明記）。
- 一部モジュール（例: research.factor_research）は実装途中の状態のコード片が含まれます。完全実装・追加テストは今後の作業対象です。

## [0.1.0] - 2026-04-19

### Added
- 初期リリース。日本株自動売買システム「KabuSys」の基礎機能を実装。
  - パッケージメタ情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - 設定管理
    - src/kabusys/config.py
      - .env ファイルの自動読み込み（.env, .env.local）を実装。OS 環境変数の保護機能や自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。
      - 柔軟な .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱い等に対応）。
      - Settings クラスを実装し、J-Quants / kabu API / DB パス / monitoring 閾値 / 環境フラグ等のプロパティを提供。環境値検証（有効な KABUSYS_ENV, LOG_LEVEL 等）を内包。
  - 環境設定ユーティリティ
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env を生成・更新する CLI を提供。既存 .env 読み取り・シークレットマスク表示・保存確認を実装。
  - 設定検証ツール
    - src/kabusys/validate_config.py
      - .env および config/*.yaml の基本チェックを行う CLI を提供。必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベル、DB パス（親ディレクトリ存在チェック）、YAML パースチェック（PyYAML 利用可否に対応）、本番向けガードチェックを実装。
      - --strict オプションで警告を失敗（exit(1)）扱いにできる。
  - 起動スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動するエントリスクリプトを提供。プロセス優先度を高く設定し、SQLite/ DuckDB コネクションを確立。paper_trading 環境では専用 SQLite(DB: data/paper_trading.db)を使用して本番 DB と分離する挙動を採用。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のスレッド実行と停止フラグ（data/stop_requested.flag）監視を実装。
      - PID ファイル管理（data/execution.pid）・停止フラグ検出による安全停止処理を実装。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - Monitoring は環境にかかわらず production の sqlite_path を使用する設計（意図的分離）。
      - stop フラグ検出による安全終了、例外時のロギングとループ継続を実装。
  - 監視 DB 初期化
    - src/kabusys/monitoring/monitoring_db.py（参照のみだが init_monitoring_db が起動スクリプトから呼ばれることを想定）。
  - ロギング／プロセスユーティリティ
    - src/kabusys/utils/logging_setup.py
      - 共通ロギング設定ユーティリティを実装。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
      - ログレベル・ログディレクトリの解決順を明示。
    - src/kabusys/utils/process_priority.py
      - psutil を利用してクロスプラットフォームのプロセス優先度設定（high/normal/low）を実装。Windows と POSIX（Linux/Mac/FreeBSD）での差分を吸収。CPU affinity 設定ユーティリティも提供。
      - 権限不足や未対応 OS では警告を出して流す安全設計。
  - ポートフォリオ構築（純関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（スコア降順・signal_rank によるタイブレーク）、等金額配分、スコア加重配分（スコア全0 の場合に等金額へフォールバック）を実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限を適用する apply_sector_cap を実装（既存保有のセクターエクスポージャー算出、ブロック対象セクターの除外）。unknown セクターは上限適用外とする仕様。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear に対応、未知レジームは 1.0 にフォールバック）。
      - セクター露呈算出で価格欠損時の注意点（TODO コメント）を残す。
    - src/kabusys/portfolio/position_sizing.py
      - allocation_method（risk_based / equal / score）に基づく発注株数計算を実装。リスクベース計算、上限（1 銘柄上限・aggregate cap）および単元株丸め（lot_size、デフォルト 100）を考慮。コストバッファ（手数料・スリッページ見積り）とスケーリングによる調整を実装。
      - aggregate スケールダウン時の端数処理（lot 単位での再配分）を実装。
      - 将来的な拡張ポイント（銘柄毎の lot_size を持たせる等）を TODO として記載。
    - src/kabusys/portfolio/__init__.py にエクスポートをまとめる。
  - Paper Trading 向け検証ツール
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95））を集計し、PASS/FAIL 判定を行うレポート生成 CLI を実装。
      - P95 計算、日付フィルタ（ISO8601 形式を内部で構築）、各種閾値（稼働率 99%, 成功率 90%, 送信率 95%, P95 200ms）を定義。
      - DB スキーマが欠けている場合の sqlite3.OperationalError を受けてフォールバック出力する耐障害性を実装。
  - 研究モジュール（着手）
    - src/kabusys/research/factor_research.py
      - DuckDB を使ったファクター計算基盤（Momentum, Value, Volatility, Liquidity 等）の方針と一部定数を実装。calc_momentum 等の関数シグネチャや動作説明を含むが、ファイル末尾が途中で終わっているため実装継続が必要。
  - ユーティリティ
    - src/kabusys/utils/__init__.py, src/kabusys/tools/__init__.py を配置してパッケージ化。
  - その他
    - 起動プロセスにおける stop/kill フラグ（data/stop_requested.flag、data/kill.flag 等）と PID ファイルの取り扱い方針をコード全体で統一。

### Changed
- （初回リリースのため該当なし。今後のバージョンで追加予定。）

### Fixed
- .env のパースやログディレクトリ作成失敗時のフォールバック、psutil による権限エラーなど、実行時にクラッシュしないよう堅牢性を向上する例外処理と警告出力を多く追加。

### Security
- .env を生成する config_setup のヘッダに「.env は絶対に Git にコミットしないこと」を明記。

### Known issues / Notes
- research.factor_research.py はファイル末尾が途中で切れており、calc_momentum の実装が未完です。研究モジュールは追加実装・テストが必要です。
- apply_sector_cap のエクスポージャ計算では price_map に価格が欠損（0.0）だと過小評価される旨の TODO を残しています。価格フォールバックの導入を検討してください。
- monitoring は意図的に「環境に依らず production sqlite_path を使用」する設計になっています。必要に応じて挙動変更（環境ごとの DB 分離）を検討してください。
- process_priority や CPU affinity の設定は権限に依存するため、一般ユーザ実行では設定がスキップされる可能性があります（警告ログで通知）。
- position_sizing の将来的拡張点（銘柄ごとの lot_size）は TODO として記載。

---

上記はコードベースの内容から推測して作成した変更履歴です。実際のコミット履歴やリリースノートに合わせて項目・日付・バージョンを調整してください。必要であれば、各ファイルごとにさらに詳細な変更点（関数単位の説明や既知のバグの再現手順）を追記できます。どの程度の粒度で記載するか指示をいただければ、それに応じて追記します。