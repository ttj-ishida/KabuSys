# Changelog

すべての notable な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。  
配布バージョンは semantic versioning を想定しています。

全体の注意:
- 日付はリポジトリのスナップショットから推測して付与しています。
- 下記はコードの内容から推測して作成した変更履歴です（実際のコミット履歴ではありません）。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-19
初回公開（ベース実装）。

### Added
- 基本アーキテクチャ
  - KabuSys のパッケージ初期実装を追加（src/kabusys/__init__.py, __version__ = 0.1.0）。
  - 実行・監視・設定・分析・ポートフォリオ関連の主要モジュールを実装。

- 実行エンジン起動スクリプト
  - run_execution.py:
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite(DB) を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立ててエンジンをデーモンスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル管理をサポート。
    - プロセス優先度を起動時に "high" に設定。

- 監視プロセス起動スクリプト
  - run_monitoring.py:
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB（SQLite）は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ検知（data/stop_requested.flag）で安全にループを終了。

- 設定管理
  - config.py:
    - .env 自動ロード機構を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - .env の読み込みは OS 環境変数を保護（上書き防止）するオプションを実装。
    - .env パースで export prefix、クォート文字列、エスケープ、インラインコメントをサポート。
    - Settings クラスで主要な設定値 (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等) をプロパティとして提供。
    - 環境 (KABUSYS_ENV) の妥当性チェックや paper_trading / live フラグ用ヘルパーを追加。

- 設定ユーティリティ CLI
  - config_setup.py:
    - 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 項目定義（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LINE_* 等）と保存処理を提供。
    - 既存 .env の読み込みと既存値の再利用、シークレットマスク表示をサポート。

  - validate_config.py:
    - .env および config/*.yaml の事前検証ツールを追加。
    - 必須環境変数の未設定検出、プレースホルダ値検出、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスや config YAML の存在チェックを実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ロギング / プロセス設定ユーティリティ
  - utils/logging_setup.py:
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）をルートロガーに設定する共通セットアップを追加。
    - ログレベル・ログディレクトリ解決の優先順を実装。ディレクトリ作成失敗時はファイル出力を省略してコンソールのみで継続。
  - utils/process_priority.py:
    - Windows / POSIX を透過するプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity 設定ヘルパーを追加（first N cores に固定）。
    - アクセス権限や未サポート OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）と配分重みの計算（等分配 calc_equal_weights、スコア加重 calc_score_weights）を実装。
    - スコア全0時に等分配へフォールバックする警告を追加。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 apply_sector_cap を実装（売却予定銘柄を除外して既存エクスポージャーを計算）。
    - 市場レジームに基づく投資乗数 calc_regime_multiplier（bull/neutral/bear を考慮）を実装。
  - portfolio/position_sizing.py:
    - allocation_method（risk_based / equal / score）に応じた株数算出ロジックを実装。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer による保守的見積りを実装。
    - 価格欠損時のスキップやデバッグロギングを含む。

- Paper Trading 用検証ツール
  - tools/paper_verification_report.py:
    - ペーパートレード用の検証レポート生成スクリプトを追加。
    - 稼働率（uptime）、注文成功率（fill rate）、送信率、レイテンシ（avg/max/P95）等を算出して PASS/FAIL 判定（閾値はソース内定義）を出力。
    - 日付フィルタと DB パスのオプションをサポート。P95 計算や DB 存在チェックを実装。

- 研究向けファクター計算（基礎）
  - research/factor_research.py:
    - DuckDB 接続を受け取り prices_daily / raw_financials を基にモメンタム等のファクターを計算する設計枠を追加（モジュール開始、定数定義、calc_momentum の骨組みを用意）。  
    - （ファイル末尾はスニペットで中断しているが、設計方針と定数が実装されている）

- DB 初期化フック
  - monitoring/monitoring_db.init_monitoring_db を run 系スクリプトから呼び出して監視テーブルの冪等な初期化を行う（monitoring 用テーブルの保証）。

### Changed
- ロギング仕様
  - 標準出力は stderr ではなく stdout を用いるように変更（cron / Task Scheduler での出力統一を想定）。

### Fixed
- 環境変数パースの堅牢化
  - .env パースで export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理をサポートして不正な読み込みを低減。

- モニタリングポーリング間隔の妥当性チェック
  - MONITOR_POLL_INTERVAL が不正（非整数または <= 0）の場合にデフォルト（60 秒）へフォールバックし、ログで警告を出力するように修正。

### Security
- シークレット値は対話式ウィザードでマスク表示するなど取り扱いに配慮（.env をコミットしない旨の注意を .env へ明示）。

### Notes / Known issues / TODO
- research/factor_research.calc_momentum の実装は途中まで（スニペットが途中で中断）になっているため、完全実装が必要。
- portfolio.risk_adjustment.apply_sector_cap: price_map が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある（TODO コメントあり）。フォールバック価格の導入を検討。
- process_priority / cpu_affinity の呼び出しは権限に依存するため、環境によっては警告を出してスキップする仕様になっている。
- run_monitoring は監視 DB に常に本番 sqlite_path を使う設計のため、テスト環境での分離を意図する場合は別途検討が必要。
- Paper Trading の挙動は PAPER_FILL_MODE に依存。無効な値は ValueError を送出するため、設定時に注意が必要。

---

（必要があれば各変更項目をコミット ID や該当ファイルの行番号・関数名でより詳細に紐付けして追記できます。どの程度の粒度で記載するか指示してください。）