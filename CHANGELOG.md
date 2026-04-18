# Changelog

すべての変更は Keep a Changelog の方針に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買フレームワーク「KabuSys」の基礎機能を実装しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として追加。

- 起動スクリプト / 実行系
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine の起動スクリプトを実装。起動時にプロセス優先度を設定し、DB 接続、ブローカークライアント生成、コンポーネント組み立て、エンジンの別スレッド実行と停止フラグ監視を行う。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用して本番 DB と分離。
    - PID ファイル管理（data/execution.pid）と停止フラグ（data/stop_requested.flag）対応。
    - RiskManager のデフォルト設定値（max_position_pct, max_utilization, rate_limit_per_sec 等）を定義。

  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor ポーリングループ起動スクリプトを実装。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視データを記録。
    - 停止フラグ検知でループ終了、例外はロギングして継続。

- 設定管理
  - Settings クラス (src/kabusys/config.py)
    - .env 自動読み込み機構（プロジェクトルート検出: .git / pyproject.toml 基準）。
    - .env/.env.local の読み込み順序と OS 環境変数保護機能。
    - 各種設定プロパティを提供（J-Quants/Kabu API、DB パス、paper trading 設定、監視しきい値、PID/kill フラグパス、環境判定ユーティリティ等）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。

  - .env ウィザード (src/kabusys/config_setup.py)
    - 対話式で .env を初期作成・更新する CLI を実装。秘匿値のマスク表示、選択肢・デフォルト対応、ファイル書き込みをサポート。

  - 設定検証ツール (src/kabusys/validate_config.py)
    - 起動前に必須環境変数、KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在/パース等をチェックする CLI を実装。
    - `--strict` オプションで警告を FAIL 扱いに変更可能。
    - PyYAML が未インストールの場合は YAML 検証をスキップして警告。

- ロギング / プロセス管理ユーティリティ
  - ログ設定ユーティリティ (src/kabusys/utils/logging_setup.py)
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保管）を設定する共通関数を実装。
    - LOG_LEVEL / LOG_DIR の解決順、ハンドラの重複防止、ディレクトリ作成失敗時のフォールバックをサポート。

  - プロセス優先度・CPU affinity (src/kabusys/utils/process_priority.py)
    - Windows/Linux/macOS の差分を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを実装。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装（利用不可時は警告を出してスキップ）。

- ポートフォリオ構築モジュール (src/kabusys/portfolio/)
  - portfolio_builder.py
    - 銘柄候補選定 select_candidates（スコア降順、signal_rank によるタイブレーク）。
    - 重み計算 calc_equal_weights（等金額）、calc_score_weights（スコア加重、全スコア 0 の場合は等金額にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap：セクター集中を検出して新規候補を除外するロジック（sell_codes の除外対応、"unknown" セクターは除外しない挙動）。
    - calc_regime_multiplier：市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。
  - position_sizing.py
    - calc_position_sizes：allocation_method（risk_based / equal / score）に応じて発注株数を計算。単元株（lot_size）丸め、per-position 上限、aggregate cap でスケーリング、cost_buffer を考慮した保守的見積りを実装。
    - リスクベースの計算や、利用可能現金に応じたスケールダウンロジック、残差分配アルゴリズムを実装。

- リサーチ / ファクター計算（初期実装）
  - research/factor_research.py（ファクター計算の設計・一部実装）
    - Momentum, Value, Volatility, Liquidity ファクターの設計に基づく計算ロジックを開始。DuckDB を利用して prices_daily / raw_financials を参照する方針を提示。

- Paper Trading 向けツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成ツールを実装。各種閾値（稼働率、注文成功率、送信率、P95 レイテンシ）を定義し、trade_logs/system_status/risk_logs から指標を抽出してレポートを出力。
    - DB パスはコマンドライン --db / 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- 監視データベース初期化ヘルパー使用
  - 複数起動スクリプトで monitoring_db 初期化関数 init_monitoring_db を呼び出し、監視テーブルの存在を保証（冪等）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env 読み込み周りの堅牢化
  - export プレフィクス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行内コメント処理、既存 OS 環境変数の保護（protected set）を実装して .env 読み込みの堅牢性を向上。

### 既知の問題 / 制限事項 (Known issues / Notes)
- research/factor_research.py は途中（ファイルが途中で終わっている箇所があり、未完の実装が含まれます）。ファクター計算は今後の実装・テストが必要です。
- portfolio.risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）だとエクスポージャーが過少見積もられる可能性がある旨の注記（将来的に前日終値等のフォールバックを検討）。
- position_sizing:
  - 単元株数 lot_size は現状グローバル固定（100）を想定。将来的に銘柄別単元を stocks マスタで管理する拡張を検討中（TODO コメントあり）。
- プロセス優先度 / CPU affinity の設定は権限不足や未対応プラットフォームではスキップされ、その旨をログに出力する実装です。
- run_monitoring は監視のため常に本番 sqlite_path を使う設計です。環境により別挙動が必要な場合は設定を調整してください。
- テストコード・CI 設定は含まれていません（別途追加推奨）。

### ドキュメント（注記）
- ファイル内に多くの docstring / コメント / 使用例が含まれており、各機能の利用方法や設計意図が記載されています。まずは README / ドキュメントを整備のうえ、外部公開・運用前に設定検証（python -m kabusys.validate_config）を推奨します。

---

注: 今後のリリースでは以下を予定しています（非包括的）:
- factor_research の完成・テスト
- 単体テストと CI の導入
- 銘柄別 lot_size のサポート、価格フォールバック処理の追加
- ブローカークライアント周りのモック/抽象化強化（テスト容易性向上）