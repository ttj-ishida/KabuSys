# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/) 準拠で記載しています。

なお、本CHANGELOGは提供されたコードベースの内容から実装意図を推測して作成しています。実際のコミット履歴やリリースノートではない点にご注意ください。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-04-23
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。以下は主要な追加点と設計上の要点です。

### 追加
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、専用の Paper Trading SQLite DB（デフォルト: data/paper_trading.db）を使用して本番 DB と完全に分離する。
    - 起動時にプロセス優先度を "high" に設定。
    - stop フラグ（data/stop_requested.flag）や実行用 PID ファイル（data/execution.pid）を扱う。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てと ExecutionEngine のスレッド実行ロジックを実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を定義。
  - run_monitoring.py
    - システム監視ループの起動スクリプト（SystemMonitor を利用）。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を変更可能（デフォルト: 60 秒）。
    - 監視は環境にかかわらず本番向け sqlite_path を使用する設計になっている（監視用 DB の初期化を実施）。
    - 起動時にプロセス優先度を "high" に設定。stop フラグで安全に終了。

- 設定管理 / CLI
  - config.py
    - 環境変数読み込みと Settings クラスを実装。
    - .env / .env.local の自動読み込み（プロジェクトルートの検出: .git または pyproject.toml）。
    - 複雑な .env パース対応（export プレフィックス、クォート内のエスケープ、インラインコメントの扱い等）。
    - 各種設定項目（J-Quants, kabuAPI, LINE, DuckDB/SQLite パス、Kill Switch 関連、監視閾値等）をプロパティとして提供。入力値検証（列挙値チェックなど）を実施。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成／更新する CLI を実装。
    - シークレット項目のマスク表示、選択肢、デフォルト値、保存確認、ファイル書き込みロジックを提供。
  - validate_config.py
    - 起動前に .env / config/*.yaml の状態を検証する CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイル存在と（PyYAML が利用可能な場合は）パース検証を実施。
    - --strict オプションで警告も失敗（exit 1）扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、デフォルト 30 日保存）を統一的に設定。
    - ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - psutil を用いてクロスプラットフォーム（Windows / POSIX）でプロセス優先度（high/normal/low）を設定するユーティリティ。
    - CPU affinity の設定関数 set_cpu_affinity を提供（権限やプラットフォームにより失敗する場合は警告を出してスキップ）。

- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順＋タイブレークとして signal_rank）、等金額配分、スコア加重配分を提供。
    - スコア合計が 0 の場合は等金額配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存保有を基にセクター上限を超える場合はそのセクターの新規候補を除外するロジック。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバック）。
    - 既知の注意点として、"unknown" セクターはセクター上限の適用対象外、価格欠損時の扱いに TODO を残す。
  - portfolio/position_sizing.py
    - allocation_method ("risk_based", "equal", "score") に応じた株数計算ロジック。
    - risk_based: 損失許容（risk_pct）、ストップロス割合、単元株（lot_size）を考慮。
    - equal/score: ウェイトに基づく配分、max_position_pct（1銘柄上限）、max_utilization（合計投下上限）を考慮。
    - aggregate cap 超過時はスケーリングし、lot_size 単位で再配分するアルゴリズムを実装（端数処理のための fractional 残差を使用）。
    - 手数料・スリッページ見積り用の cost_buffer が導入されている。
  - portfolio/__init__.py で主要関数をエクスポート。

- リサーチ / ファクター計算（基礎実装）
  - research/factor_research.py
    - モメンタム、ボラティリティ、流動性、バリュー系ファクターを計算するモジュールの骨格を実装（DuckDB 接続を受け SQL/Python で計算）。
    - 定数・窓サイズ（1M/3M/6M, MA200, ATR20 等）を定義。
    - calc_momentum の冒頭を含むが、ファイル末尾が途中で切れている（実装継続が必要）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）から検証レポートを生成する CLI。
    - システム稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を集計し PASS/FAIL 判定を行う。
    - デフォルト基準値（例: 稼働率 >= 99%、Fill >= 90%、P95 <= 200ms）を定義。
    - 日付フィルタ、DB パス指定オプションをサポート。

- パッケージ情報
  - __init__.py にてパッケージバージョンを "0.1.0" として設定。

### 変更
- 初回リリースのため既存コードのリファクタリングや API 仕様の変更履歴はありません。

### 修正
- 初回リリースのため修正履歴はありません。

### 削除
- 初回リリースのため削除履歴はありません。

### 既知の注意点 / TODO
- research/factor_research.py が途中で切れており、計算ロジックの続きが未実装。完全なファクター計算実装が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に 0.0 が含まれる場合、既存保有のエクスポージャーが過小見積もられる可能性があり、将来的に前日終値や取得原価などのフォールバック価格を導入することが検討されている（TODO コメントあり）。
- process_priority および set_cpu_affinity: 権限不足や未対応プラットフォームでは設定をスキップする設計になっているため、実行環境ごとの挙動に注意が必要。
- logging_setup: ログディレクトリ作成に失敗した場合はファイル出力が無効化される。ディスク権限等の設定を事前に確認することを推奨。
- validate_config: PyYAML 未インストール時は YAML の検証をスキップするが、その旨を警告する。運用環境では PyYAML をインストールしておくことが望ましい。
- run_monitoring は監視用 DB に常に本番 sqlite_path を用いる仕様になっているため、テスト実行時は設定に注意する必要あり。

---

今後のリリース案（例）
- 0.2.0: research モジュールの完成、ExecutionEngine の詳細実装とテスト、CI の追加
- 0.3.0: 銘柄別 lot_size 対応、価格フォールバックロジック、詳細な監視アラート（LINE 通知）実装

（このCHANGELOGはコードを解析して推測した内容に基づき作成しています。実際の変更履歴はリポジトリのコミットログをご参照ください。）