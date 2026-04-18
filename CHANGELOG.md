# CHANGELOG

すべての変更は Keep a Changelog 形式に従って記載しています。  
リリース履歴は安定したバージョンのみを記載しています（作業中の変更は Unreleased にまとめてください）。

## [Unreleased]
- ドキュメント／コード追加中のモジュール（例: research.calc_momentum の未完部分）が存在します。今後のリリースで完成させます。

## [0.1.0] - 2026-04-18
初回リリース。本バージョンでは自動売買システムの基盤機能、運用・検証ツール、設定管理ユーティリティを実装しています。

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御: プロジェクト配下 data/stop_requested.flag を検知して優雅に終了。
    - 監視では KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する設計。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB（data/paper_trading.db）を使用し、MockBrokerClient による完全分離ペーパートレードをサポート。
    - 停止制御: data/stop_requested.flag、execution.pid を扱う。バックグラウンドスレッドで engine を実行し、停止フラグを検知して停止を要求。
- 設定管理
  - config.py
    - .env の自動読み込み機構を実装（プロジェクトルートの検出: .git または pyproject.toml）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
    - .env の各種値のパーサーを実装（export プレフィックス、引用符、インラインコメント対応）。
    - Settings クラスを実装し、アプリケーションで利用する各種設定値（DB パス、API トークン、しきい値、環境種別等）をプロパティとして提供。
- 設定/検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を初期作成・更新する機能を追加。
    - 入力補助、既存値の表示、シークレット値のマスク表示、保存確認機能を実装。
  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の値検証、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパース検証を実行。
    - --strict オプションで警告も失敗扱いにできる。
- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに対して StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定する統一的なログセットアップ関数を追加。
    - LOG_LEVEL / LOG_DIR の解決ルール、ログディレクトリ自動作成、失敗時のフォールバック（コンソールのみ）を実装。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを追加。
    - Windows（HIGH_PRIORITY_CLASS 等）・POSIX（nice 値）双方に対応。CPU affinity 設定関数も実装。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 銘柄候補抽出（select_candidates）、等配分（calc_equal_weights）、スコア加重（calc_score_weights）を純粋関数で実装。
    - スコアが全て 0 の場合は等配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクター別時価を計算し、上限超過セクターの候補を除外する。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear 対応、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - position sizing（calc_position_sizes）を実装。以下をサポート:
      - allocation_method: "risk_based"（リスクベース） / "equal" / "score"
      - lot_size 単位で丸め、単銘柄上限・ aggregate cap（available_cash）でスケールダウン
      - cost_buffer を含めた保守的な約定コスト見積り
      - マージンが不足する場合のスケールと残余配分ロジック
- 検証・レポートツール
  - tools/paper_verification_report.py
    - ペーパートレード DB から各種検証指標（稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95））を集計してレポート出力する CLI を追加。
    - 閾値に基づく PASS/FAIL 判定を実装（稼働率、成功率、送信率、P95 レイテンシなど）。
    - 日付フィルタ（--from / --to）や DB パス指定（--db / 環境変数）に対応。
- DuckDB / SQLite 統合
  - 起動スクリプトやツールは DuckDB 接続と SQLite 接続を併用する設計を採用（分析用に DuckDB、監視/注文履歴に SQLite）。
  - 監視 DB 用の init_monitoring_db 呼び出しにより監視テーブルの存在を保証（冪等）。
- パッケージ情報
  - __init__.py によるバージョン定義: __version__ = "0.1.0"

### 変更 (Changed)
- ログ出力ポリシー
  - StreamHandler を stdout に向けることで、cron やタスクスケジューラ実行時のログ取り扱いを容易にした。
- 環境読み込みポリシー
  - .env の読み込み順序や保護（OS 環境変数の保護）ルールを明確化し、安全に既存環境を保持する仕様にした。

### 修正 (Fixed)
- 環境変数解析の堅牢化
  - .env パーサーで export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントルール（クォートなしの場合の '#' 解釈）に対応し、よくある .env フォーマット差異に耐性を持たせた。

### 注意事項 / 既知の制約 (Known issues / Notes)
- research/factor_research.py の一部（calc_momentum の実装途中）が存在します。今後のリリースで完成予定です。
- 一部機能は外部モジュール（psutil、duckdb、PyYAML 等）に依存します。環境により機能制限や警告が出ます（validate_config は PyYAML 未インストール時に YAML 検証をスキップします）。
- run_monitoring は監視 DB として常に sqlite_path（本番DB）を参照する設計です。運用時は環境変数の設定に注意してください。

### 破壊的変更 (Breaking Changes)
- 初回リリースのため該当無し。

---

将来のリリースでは以下を予定しています:
- research モジュールの完成（ファクター計算全実装）
- テストカバレッジ拡充・CI 統合
- broker や engine のモック／スタブを用いた統合テスト用ユーティリティ
- エラーハンドリング・再試行／サーキットブレーカー機構の強化

以上。