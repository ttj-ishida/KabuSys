CHANGELOG
=========

すべての変更は "Keep a Changelog" の書式に準拠して記載しています。  
日付はこのリポジトリのコードから推測して作成しています。

[Unreleased]: https://example.com/compare/v0.1.0...HEAD

[0.1.0] - 2026-04-20
-------------------

Added
- 初期リリースとして以下の主要機能を追加。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。  
      - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用する設計をサポート。  
      - ブローカークライアント生成は BrokerClientFactory 経由。OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動する。
      - 停止フラグ（data/stop_requested.flag）や実行 PID ファイルの扱い（data/execution.pid）に対応。スレッドでエンジンを起動し、フラグ監視で安全に停止可能。
    - run_monitoring.py: システム監視ポーリングループ起動スクリプトを追加。  
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。  
      - Monitoring は環境に関係なく本番用 sqlite_path を使用する設計。
  - 設定 / 環境管理
    - config.py: Settings クラスを追加。環境変数や .env の自動読み込み（.env / .env.local）に対応。  
      - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。  
      - 各種設定プロパティ（DB パス、PID ファイル、閾値、KABUSYS_ENV 判定、PAPER_FILL_MODE 等）を提供。値検証（許容値チェック）を実装。
    - config_setup.py: 対話式 .env 作成ウィザードを追加。  
      - シークレットのマスク表示、選択肢サポート、既存値の読み込み・再利用、.env の書き込みロジックを実装。
    - validate_config.py: 起動前の設定検証 CLI を追加。  
      - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ検査、config/*.yaml の存在・パース検証（PyYAML 未インストール時は警告）および本番環境向けガードを実装。`--strict` で警告を失敗扱いにするオプションあり。
  - ロギング / プロセス制御ユーティリティ
    - utils/logging_setup.py: 共通ログ設定ユーティリティを追加。  
      - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせたルートロガー設定。LOG_DIR / LOG_LEVEL による設定、ファイル作成失敗時のフォールバックがある。
    - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。  
      - Windows と POSIX (Linux, macOS, FreeBSD) を吸収する実装。`set_process_priority("high"|"normal"|"low")` と `set_cpu_affinity(n)` を提供。アクセス権限不足時は警告でスキップ。
  - ポートフォリオ構築ライブラリ（純関数群）
    - portfolio/portfolio_builder.py: シグナル選定と重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装。score がすべて 0 の場合は等配分へフォールバック。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、レジーム未定義時のフォールバックを含む。
    - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）を実装。  
      - allocation_method（"risk_based" / "equal" / "score"）に対応。  
      - 単元株（lot_size）丸め、1銘柄上限、総投下上限（available_cash）によるスケーリング、コストバッファの考慮（スリッページ/手数料見積り）を実装。残余キャッシュでの端数配分ロジックあり。
  - リサーチ / ファクター計算（骨格）
    - research/factor_research.py: DuckDB 接続を受けてモメンタム等のファクターを計算するモジュールを追加（設計・定義、関数骨格）。prices_daily / raw_financials テーブルを想定した設計方針を記載。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
      - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し、閾値に基づく PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数と --db オプションをサポート。

Changed
- パッケージ初期構成としてモジュール分割を行い、__all__ / __version__ を設定（__version__ = "0.1.0"）。

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 実装上の重要点（ドキュメント的注意）
- .env ローダは OS 環境変数を上書きしない（デフォルト）。ただし .env.local は override=True で読み込まれ、既存の OS 環境を上書きしないよう保護される実装になっている。
- config.py の _require() は必須環境変数未設定時に ValueError を投げるため、呼び出し箇所で例外処理が必要。
- run_monitoring は監視 DB に settings.sqlite_path（本番用パス）を常に使用する点に注意（環境に依らず同一の監視 DB を参照）。
- process_priority / CPU アフィニティ設定は権限不足や未対応プラットフォームで安全にスキップされ、ログに警告を出す。
- paper_verification_report の集計はテーブル不在時に sqlite3.OperationalError を捕捉して Graceful に N/A を返す実装となっている。

今後の作業（提案）
- research/factor_research.py のファクター計算の完全実装（現在はモジュール設計・一部関数骨格が存在）。
- 各モジュールに対するユニットテスト追加（.env パーサ、position sizing のスケーリング等）。
- 実運用時の監視・アラート（LINE）統合の確認（validate_config の警告対応）。
- 銘柄ごとの lot_size を stocks マスタから取得するなどの拡張（position_sizing の TODO）。

---
この CHANGELOG はコードの内容から推測して作成しています。実リリースノート作成時は差分コミットやリリース日付、実際の変更差分をもとに調整してください。