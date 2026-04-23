# Changelog

すべての重要な変更は「Keep a Changelog」規約に従って記載しています。  
このファイルはリポジトリのコードから推測できる変更点・導入機能を元に作成しています。

※ バージョン番号は src/kabusys/__init__.py の __version__ に合わせています。

## [Unreleased]
- 小さな改善・調整（ログ出力のフォールバックや環境変数パースの堅牢化など）
  - ログディレクトリ作成に失敗した場合にファイルハンドラをスキップしてコンソール出力のみで継続するように改善。
  - .env 読み込みで OS 環境変数を保護する仕組み（protected set）を導入。
  - MONITOR_POLL_INTERVAL の不正値に対してデフォルトにフォールバックする安全対策を追加。
  - process priority / CPU affinity 設定で権限不足や未対応 OS の場合に警告を出してスキップするよう堅牢化。
  - monitoring の初期化処理を冪等化（init_monitoring_db を利用）して安全に起動できるように調整。

---

## [0.1.0] - 2026-04-23
初回公開リリース。

### 追加 (Added)
- 基本アプリケーション構成
  - パッケージエントリポイントとバージョン情報を追加（__version__ = "0.1.0"）。
- 設定・環境管理
  - Settings クラス（kabusys.config）を導入し、.env ファイルや環境変数から設定を取得する仕組みを提供。
  - 自動 .env 読み込み:
    - プロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロード。
    - OS 環境変数を保護する仕組みを実装。
  - .env パーサの実装:
    - export プレフィックス、クォート文字列、エスケープ、行末コメント等に対応。
  - 各種設定プロパティを提供（DB パス、PAPER_FILL_MODE、KABUSYS_ENV、ログレベル、閾値など）。
- 設定支援ツール
  - 対話式設定ウィザード（kabusys.config_setup）を追加して .env の作成・更新を支援。
  - 設定検証 CLI（kabusys.validate_config）を追加:
    - 必須環境変数チェック、KABUSYS_ENV 検証、DB パスや config/*.yaml の存在・パースチェック、
      本番環境向けのガードチェック（LINE トークンや Kill Switch 設定）などを実施。
    - --strict オプションで警告を失敗扱いにできる。
- 実行・監視プロセス起動スクリプト
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）を追加:
    - KABUSYS_ENV=paper_trading 時は専用の Paper Trading DB を使用し、本番 DB と分離（PAPER_TRADING_SQLITE_PATH）。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）検知で安全に停止する仕組みを実装。
    - PID ファイルの取り扱い (data/execution.pid)。
  - SystemMonitor 起動スクリプト（kabusys.run_monitoring）を追加:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に production 用の sqlite_path を参照して監視データを記録。
    - 停止フラグ検知でループを終了。
- データベース・分析
  - DuckDB と SQLite を併用する設計を導入（設定からパスを取得して接続）。
  - init_monitoring_db を用いて監視用テーブルの初期化を保証。
- ロギング
  - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）を追加:
    - stdout（StreamHandler）と日次ローテーションのファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - ログレベルとログディレクトリの解決順を明示（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力を無効化して stdout のみで動作。
- プロセス制御
  - process_priority ユーティリティ（kabusys.utils.process_priority）を追加:
    - Windows / POSIX（Linux/macOS/FreeBSD）で優先度（high/normal/low）を設定。
    - CPU affinity を指定する set_cpu_affinity を提供。
    - 権限不足や未対応プラットフォームでのフォールバック実装。
- ポートフォリオ構築（pure functions）
  - 選定・重み付け（kabusys.portfolio.portfolio_builder）
    - select_candidates（スコア降順選択）、等金額およびスコア加重の重み計算を実装。
  - リスク調整（kabusys.portfolio.risk_adjustment）
    - セクター集中制限 apply_sector_cap、マーケットレジームに基づく乗数 calc_regime_multiplier を実装。
  - ポジションサイズ算出（kabusys.portfolio.position_sizing）
    - risk_based / equal / score の配分方式に対応した calc_position_sizes を実装。
    - lot_size 単位での丸め、aggregate cap によるスケーリング、コストバッファ考慮などを実装。
- 研究用ファクター計算
  - research/factor_research にモメンタム等ファクター計算の骨格を追加（DuckDB 接続を受ける設計）。
- ペーパートレード検証ツール
  - tools/paper_verification_report を追加:
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ等を集計してレポート出力。
    - P95 計算、閾値判定（稼働率 99% 等）に基づく PASS/FAIL 判定を実装。
    - --from/--to/--db オプションを提供。
- そのほか
  - Execution 側の RiskManager にデフォルト設定値を導入（max_position_pct, max_utilization, rate_limit_per_sec 等）。
  - Engine/Monitor の起動時にプロセス優先度を high に設定する呼び出しを追加。

### 変更 (Changed)
- 設定読み込みの優先順を明確化（OS 環境変数 > .env.local > .env）。
- ロガー設定の既存ハンドラのクリーンアップ（重複設定の防止）。

### 修正 (Fixed)
- .env パーサ: クォート内でのバックスラッシュエスケープや行末コメントの扱いを改善。
- MONITOR_POLL_INTERVAL の不正値による例外を回避し、デフォルト値へフォールバックするように修正。

### セキュリティ (Security)
- .env ファイルは絶対に Git にコミットしないようにウィザードの注意書きを追加。

---

もし CHANGELOG に追記・修正したい項目（リリース日、既存の変更の分類変更、追加で記載してほしい変更点など）があれば教えてください。コードの更なる検査に基づいて内容を更新できます。