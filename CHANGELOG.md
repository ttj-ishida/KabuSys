# Changelog

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

## [0.1.0] - 2026-04-17

### 追加 (Added)
- 基本パッケージ初期実装
  - パッケージバージョンを `__version__ = "0.1.0"` に設定（src/kabusys/__init__.py）。

- 環境設定・読み込み関連
  - .env 自動読み込み機能を実装（OS環境変数の保護、`.env` → `.env.local` の優先度）。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート（src/kabusys/config.py）。
  - .env パーサーを高精度に実装（export プレフィックス、シングル/ダブルクォートのエスケープ、行内コメントの扱いなど）。無効行をスキップする堅牢な実装（src/kabusys/config.py）。
  - Settings クラスを実装し、環境変数から各種設定を取得・検証（KABUSYS_ENV / LOG_LEVEL のバリデーション、PAPER_FILL_MODE の検証、DBパスなど）（src/kabusys/config.py）。
  - 対話式ウィザードで .env を生成・更新する CLI を実装（src/kabusys/config_setup.py）。
  - 設定検証 CLI を実装（必須環境変数、KABUSYS_ENV、ログレベル、DBパス、config/*.yaml の存在と YAML パースチェック、live 環境向けガードなど。--strict オプションあり）（src/kabusys/validate_config.py）。

- 実行 / 監視エントリポイント
  - ExecutionEngine 起動スクリプトを実装（プロセス優先度設定、paper_trading 環境での DB 分離、BrokerClientFactory によるブローカー生成、ExecutionEngine の起動と停止フラグ処理、PID ファイル利用）（src/kabusys/run_execution.py）。
    - ペーパートレード時は専用 SQLite（data/paper_trading.db をデフォルト）を使用し、本番 DB と分離する旨をドキュメント化。
    - スレッド駆動のセッション実行と停止フラグ検出ロジックを実装。
  - SystemMonitor ポーリングループ起動スクリプトを実装（MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き、停止フラグ、監視 DB 初期化）（src/kabusys/run_monitoring.py）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様をドキュメント化。

- 監視・検証ツール
  - Paper Trading 用の検証レポート生成ツールを追加（SQLite から集計し、稼働率、注文成功率、送信率、レイテンシ（P95 など）を出力。コマンドライン引数 --from/--to/--db 対応）（src/kabusys/tools/paper_verification_report.py）。
    - レポートの閾値（稼働率、成功率、送信率、P95 レイテンシ）を定義し、PASS/FAIL 判定を出力。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）を実装（src/kabusys/portfolio/portfolio_builder.py）。
    - スコア降順・同点時のタイブレークなど実装。スコアがすべて 0 の場合に等金額配分へフォールバック。
  - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - 既存保有を考慮したセクター別エクスポージャー算出と、上限超過セクターの新規候補除外ロジック。
    - レジームに応じた投下資金乗数（bull/neutral/bear）を提供。未知レジームはフォールバックで 1.0（ログ警告あり）。
  - 株数決定・リスク制限・単元丸め（calc_position_sizes）を実装（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - ロット（lot_size）単位切り捨て、最大ポジション比率や max_utilization、cost_buffer を考慮した aggregate cap スケーリング、スケールダウン後の端数処理（残差に基づく追加配分）を実装。

- リサーチ／ファクター計算
  - DuckDB を使ったファクター計算モジュールを実装（momentum / volatility 等、prices_daily や raw_financials テーブル参照。MA200、ATR、リターン等を計算）（src/kabusys/research/factor_research.py）。
    - 計算窓や不足データ時の None ハンドリング、P95 等の算出設計を反映。

- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを実装（Windows / POSIX の差分吸収、psutil 利用、set_process_priority / set_cpu_affinity）（src/kabusys/utils/process_priority.py）。
    - アクセス権限や未サポート OS の場合は警告を出してスキップする堅牢化。

- パッケージエクスポート整理
  - portfolio モジュールのトップレベルエクスポートを追加（select_candidates 等を __all__ に登録）（src/kabusys/portfolio/__init__.py）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 削除 (Removed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- （該当なし）

----

注:
- 各モジュールはドキュメンテーション文字列とログメッセージを充実させ、動作意図や安全上の注意（例: 本番 DB と paper_trading DB の分離、Kill/Stop フラグの扱い、.env ファイルは Git にコミットしない等）を明記しています。
- 実際の運用では .env/.env.local の管理、KABUSYS_ENV の設定、LINE 通知設定（本番時の監視）などを適切に行ってください。