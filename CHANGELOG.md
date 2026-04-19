# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。  

- リリース方針: 互換性のある API を壊す変更は Breaking Changes として明記します。
- 日付形式: YYYY-MM-DD

## [Unreleased]

- ドキュメントやユーティリティの改善予定（現状なし）。

## [0.1.0] - 2026-04-19

初回公開リリース。以下の主要機能・改善点・既知の制限を含みます。

### 追加 (Added)

- 起動スクリプト / 実行系
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。  
    - スレッドで engine.run_session を実行し、data/execution.pid に PID 管理。  
    - 停止フラグ (data/stop_requested.flag) を検知して安全に停止。  
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite (data/paper_trading.db) を使用し、MockBrokerClient を利用する設計（BrokerClientFactory による生成）。
    - RiskManager のデフォルト RiskConfig を定義し、初期ポートフォリオ値を broker.get_available_cash() から取得して初期化。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を設定（デフォルト 60 秒、無効値は警告を出してデフォルトにフォールバック）。  
    - 監視は環境にかかわらず本番用 sqlite_path を使用（監視データは本番 DB を参照する方針）。  
    - 停止フラグ検出と例外安全なループ（check_once() 内例外はログに残して継続）。  

- 設定関連
  - config.py: 環境変数・設定管理モジュールを追加。  
    - .env 自動ロード機能（プロジェクトルートの判定: .git または pyproject.toml を探す）。  
    - .env/.env.local の優先順と OS 環境変数保護（override / protected の仕組み）。  
    - 多数のプロパティ（J-Quants、kabu API、DB パス、Paper Trading 周りの設定、しきい値、ログレベル、環境判定等）を提供。  
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の妥当性チェック、パスは Path 型で返却。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加。  
    - 多数の設定項目をプロンプトで入力して .env を生成・保存。シークレット値はマスク表示。  

- 設定検証ツール
  - validate_config.py: 起動前チェック CLI を追加。  
    - 必須環境変数の未設定検出、KABUSYS_ENV の妥当性、ログレベル、DB パス（親ディレクトリの存在確認）、config/*.yaml の存在と（PyYAML があれば）パース検証、KABUSYS_ENV=live 時の追加ガードを実施。  
    - --strict オプションで警告を FAIL 扱いにする機能。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定を追加。  
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（デフォルト logs/<app>.log、30日保持）をルートロガーに設定。  
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続。ログレベル解決順（引数 > 環境変数 > デフォルト）。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows と POSIX(Linux/Mac/FreeBSD) の差を吸収して set_process_priority('high'|'normal'|'low') を提供。  
    - set_cpu_affinity(cpu_count) で最初の N コアにピン留めする機能を提供。  
    - psutil アクセス不可や未対応 OS の場合は警告を出してフォールバック。

- 取引ロジック（ポートフォリオ構築）
  - portfolio/portfolio_builder.py: シグナル選定と重み計算（等配分・スコア加重）を純粋関数として実装。  
    - select_candidates: スコア降順 + signal_rank によるタイブレーク。  
    - calc_equal_weights / calc_score_weights: スコア全0時は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限とレジーム乗数を実装。  
    - apply_sector_cap: 既存保有のセクター別エクスポージャにより新規候補を除外（unknown セクターは無視）。  
    - calc_regime_multiplier: 'bull'/'neutral'/'bear' に対する乗数（デフォルトフォールバックあり）。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（risk_based / equal / score）。  
    - ロット単位（lot_size）で丸め、1銘柄上限や aggregate cap のスケーリング、cost_buffer を考慮した保守的見積り、端数処理（fractional remainders による割当）を実装。

- 監査・検証ツール
  - tools/paper_verification_report.py: ペーパートレード検証用レポートジェネレータを追加。  
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を計算してレポート出力。  
    - 閾値（稼働率99%、注文成功率90%、送信率95%、P95レイテンシ200ms）に基づく PASS/FAIL 判定。  
    - コマンドライン引数で期間指定 (--from, --to) / DB パス指定 (--db) が可能。

- データ解析（研究用）
  - research/factor_research.py: ファクター計算の土台を追加（モメンタム・MA・ATR 等の定義と設計方針）。  
    - DuckDB 接続を受け取り prices_daily / raw_financials を用いてファクターを算出する方針（実装はモジュール内で進行中）。

- パッケージ初期化
  - __init__.py: バージョンを "0.1.0" に設定し、主要サブパッケージをエクスポート。

### 変更 (Changed)

- デフォルト設定 / 設計上の決定を明確化
  - 監視プロセスは KABUSYS_ENV に依存せず monitoring DB (sqlite_path) を本番ベースで利用する方針を明記。
  - .env 自動ロードはテストや特殊用途のため環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。

### 修正 (Fixed)

- 環境変数読み込みの堅牢化
  - .env のパースで export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなどを丁寧に実装し、一般的な .env フォーマットへの互換性を向上。

- ロギングハンドラ重複防止
  - setup_logging() は既存ハンドラを閉じて削除してから再設定するようにし、二重出力を防止。

### 既知の問題 / 制限 (Known issues / Limitations)

- research/factor_research.py は計算ロジックの一部（ファイル終端近傍）が未完（コードが途中で切れている模様）。実運用では追加実装が必要。
- apply_sector_cap: price_map に価格が欠損（0.0）な場合、エクスポージャが過少に見積られる可能性あり。コメントでフォールバック価格導入の TODO を記載。
- process_priority / set_cpu_affinity: psutil の権限不足や未対応 OS では機能がスキップされる。アクセス拒否時は警告ログのみ。
- run_monitoring の MONITOR_POLL_INTERVAL は負値や 0 の入力を受けない設計で、無効値はデフォルトにフォールバックする（time.sleep のエラー回避目的）。

---

貢献やバグ報告は issue を通じて受け付けてください。改修履歴は今後のリリースで逐次追加します。