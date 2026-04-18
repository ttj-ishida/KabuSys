Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

書式:
- セクションはリリースごとに分け、主要な変更カテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）を使用します。
- 日付はリリース日を表します。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーション初期実装を追加。
  - パッケージ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 実行スクリプト:
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV が paper_trading の場合は専用の paper_trading DB を使用（data/paper_trading.db デフォルト）して本番 DB と完全分離。
      - ブローカークライアント用の Factory を導入（BrokerClientFactory）。
      - ExecutionEngine の立ち上げ/停止、PID ファイル管理、停止フラグ検出ロジックを実装。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視 DB は環境にかかわらず本番 sqlite_path を使用して接続。
  - 設定管理:
    - config.py: 環境変数 / .env ロードのユーティリティを実装。
      - プロジェクトルート検出（.git または pyproject.toml ベース）により .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
      - 複雑な .env 行パース（export 形式、クォート／エスケープ、インラインコメント等）に対応。
      - Settings クラスを提供し、各種設定値（DB パス、API トークン、監視しきい値、環境判定等）をプロパティ経由で取得。
  - 設定支援・検証 CLI:
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新するツールを追加（必須/任意項目、シークレットマスキング、保存確認など）。
    - validate_config.py: .env および config/*.yaml の検証ツールを追加。--strict オプションで警告を失敗扱いにできる。
  - ポートフォリオ構築（純関数群）:
    - portfolio/portfolio_builder.py:
      - select_candidates: BUY シグナルのスコア降順選択。
      - calc_equal_weights, calc_score_weights: 等配分・スコア割合配分（スコア全0 の場合は等配分にフォールバック）。
    - portfolio/risk_adjustment.py:
      - apply_sector_cap: セクター集中上限チェック（売却予定銘柄の除外、"unknown" セクターはスキップ）。
      - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバック）。
    - portfolio/position_sizing.py:
      - calc_position_sizes: 重み・候補情報から単元株丸めやリスクベース配分、aggregate cap（利用可能現金に応じたスケーリング）を行う。コストバッファや lot_size に対応。
  - ユーティリティ:
    - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加（console stdout + 日次ローテーションファイルハンドラ、LOG_LEVEL/LOG_DIR の解決ロジック、既存ハンドラのクリア等）。
    - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度（nice / Windows 優先度）と CPU affinity 設定を追加。アクセス権限不可の場合は安全にフォールバックして警告を出力。
  - モニタリング DB 初期化:
    - monitoring/monitoring_db モジュール（参照される形で init_monitoring_db を呼び出し、監視用テーブルが存在することを保証）。
  - ペーパートレード検証ツール:
    - tools/paper_verification_report.py:
      - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を解析して、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を算出、PASS/FAIL 判定を行う。
      - デフォルトの閾値を定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。
      - 日付フィルタ（--from/--to）、DB パス指定（--db / 環境変数）に対応。
  - リサーチ（ファクター計算）下地:
    - research/factor_research.py: モメンタム、ボラティリティ、流動性、バリュー等のファクター計算モジュールの設計と一部実装（DuckDB 接続を受け SQL と Python 組合せで計算）。（実装は継続中／部分的）
  - パッケージ構成:
    - __all__ に主要サブパッケージを設定（data, strategy, execution, monitoring）。

Changed
- 初期リリースのため過去変更はありません。

Fixed
- 初期リリースのため過去修正はありません。

Known issues / Notes
- research/factor_research.py は途中で切れている（ファクター計算の一部実装が継続中）。完全実装は今後のリリース予定。
- position_sizing.calc_position_sizes 内で価格欠損時のフォールバック（前日終値や取得原価等）は未実装（TODO コメントあり）。価格欠損があるとエクスポージャーが過小評価される可能性がある。
- process_priority / set_cpu_affinity は OS 権限やプラットフォームに依存するため、権限不足や未サポート環境では警告を出して何もしない挙動となる。
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされる（CI / 配布パッケージ環境を想定）。
- logging_setup: ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみになる。
- monitoring 実行時は監視 DB に接続して init_monitoring_db を呼び出すため、監視テーブルが存在しない場合でも安全に初期化される（冪等性あり）。
- Paper Trading と本番 DB は明示的に分離（paper_trading 用 sqlite パスを用意）。ペーパートレード用の動作検証により本番データを汚染しない設計。

開発メモ / 今後の改善候補
- factor_research の完全実装（すべてのファクター、Zスコア正規化の統合）。
- 銘柄ごとの lot_size を stocks マスタに保持し、position_sizing を拡張する。
- price フォールバックロジック追加（欠損時の前日終値等）。
- モニタリング／エンジン起動の systemd / docker 用設定例の追加。
- 単体テスト・CI の充実（特に数値アルゴリズム部分の回帰テスト）。

References
- 実行例:
  - 監視ループ: python -m kabusys.run_monitoring
  - エンジン起動: python -m kabusys.run_execution
  - .env ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

---
（注）上記変更履歴は提供されたコードから推測して作成しています。実際のコミット履歴や差分に基づく正確な履歴が必要な場合は Git ログ等を提供してください。