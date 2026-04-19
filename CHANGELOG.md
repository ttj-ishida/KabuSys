# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このログは与えられたコードベースから推測して作成したものであり、実際のコミット履歴ではありません。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-19

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加点は以下の通りです。

### Added
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。プロセス優先度を設定し、BrokerClientFactory を使ってブローカークライアントを生成、ExecutionEngine をバックグラウンドスレッドで実行。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と完全分離。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）に対応。停止フラグ検知で安全にエンジンを停止。
    - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を追加し、初期ポートフォリオ値に基づく設定を行う。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化・記録。

- 設定管理
  - config.py
    - .env 自動ロード（プロジェクトルートの .env/.env.local、OS 環境変数を尊重）を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env のパース機能（export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント扱いなど）を実装。
    - Settings クラスを提供し、各種設定値（J-Quants、kabuAPI、DuckDB/SQLite パス、Paper Trading 用設定、監視閾値、環境判定等）をプロパティとして取得可能にした。
    - PAPER_FILL_MODE（instant/partial/never/reject）など Paper Trading 関連設定サポート。

  - config_setup.py
    - 対話式の .env 作成/更新ウィザードを実装。既存 .env の読み込み、シークレット値のマスク表示、選択肢サポート、.env のテンプレート書き出しを提供。

  - validate_config.py
    - 起動前に環境変数および config/*.yaml の存在・基本的整合性を検証する CLI を追加。--strict オプションで警告も失敗扱いにできる。
    - PyYAML の有無に応じた YAML パース検査、KABUSYS_ENV の live 時の追加ガード（LINE トークン未設定や Kill Switch 設定など）を実装。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。ログディレクトリ解決と作成失敗時のフォールバック（コンソールのみ）に対応。
  - utils/process_priority.py
    - Windows/Linux/Mac を跨いでプロセス優先度（high/normal/low）を設定する関数を提供（psutil ベース）。CPU affinity を設定する set_cpu_affinity も提供。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順・同点時タイブレーク）、等金額配分、スコア加重配分（全スコアが 0 の場合は等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py
    - セクター集中制限（既存保有を考慮して同一セクターの新規買い候補を除外する apply_sector_cap）を実装。unknown セクターは除外対象外として扱う。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull:1.0 / neutral:0.7 / bear:0.3、未知は 1.0 でフォールバックし警告）。
  - portfolio/position_sizing.py
    - allocation_method（risk_based / equal / score）に基づく株数決定アルゴリズムを実装。
    - 単元株（lot_size）で丸め、1 銘柄上限・集合上限（available_cash）を考慮したスケーリング処理、cost_buffer による保守的コスト見積り、スケールダウン時の端数配分ロジックを備える。

- 分析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite データから検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、API レイテンシ（平均/最大/P95）などを算出し、閾値（稼働率 99%、成功率 90% 等）で PASS/FAIL を判定。
    - 日付フィルタ (--from, --to)、DB パス指定 (--db)、P95 計算、各種安全な SQL ハンドリングを実装。

- リサーチ
  - research/factor_research.py（実装開始）
    - DuckDB の prices_daily/raw_financials を用いてモメンタム・Value・Volatility・Liquidity 等のファクター計算を行う設計を追加（モメンタム関連定数や関数 calc_momentum の骨組み実装を含む）。（一部実装が継続中 / ファイル末端が途中で切れているため WIP）

### Changed
- ログの標準出力先を stderr ではなく stdout に統一（cron 等でのリダイレクト処理を考慮）。
- .env 読み込みの優先順位を明確化：OS 環境 > .env.local > .env。既存 OS 環境は protected として上書きされない。

### Fixed
- .env パーサーの改善
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い（クォート無しで # の直前に空白がある場合のみコメント扱い）を実装して不正なパースを低減。
- 環境変数のバリデーション改善
  - MONITOR_POLL_INTERVAL の不正値（0以下や非整数）に対する警告とデフォルトフォールバックを run_monitoring に実装。
  - Settings クラスで、PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL など不正値時に明確な例外を投げるように改善。
- ログディレクトリ作成失敗時の堅牢化（ファイルハンドラ作成失敗を警告し、コンソールのみで継続）。

### Security
- .env の取り扱いに関する注意書きを config_setup の出力テンプレートに追加（.env を Git にコミットしない旨）。

### Documentation / UX
- CLI ヘルプ・usage テキストを各スクリプトに追加（config_setup, validate_config, paper_verification_report）。
- config_setup の対話ウィザードでシークレット項目をマスク表示。

### Known issues / WIP
- research/factor_research.py はモメンタム計算部分の実装が途中（ファイル末端が切れている）であり、完全実装は未完了。
- position_sizing の価格欠損時（price = 0.0）における挙動について TODO が残っている（フォールバック価格の導入検討）。
- 一部モジュール（SystemMonitor, ExecutionEngine, BrokerClientFactory 等）の内部実装は本リリース外の別モジュールに依存（本変更点ではインターフェース使用を前提に実装）。

---

この CHANGELOG はコードベースから推測して作成したものです。実際のリリースノートやコミット履歴が必要な場合は、バージョン管理の履歴（git log）に基づいて正確に作成してください。