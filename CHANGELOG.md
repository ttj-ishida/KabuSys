# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています（日本語記載）。

注: 実装内容から推測して作成しています。実際の変更履歴やコミットメッセージと差異がある場合があります。

## [Unreleased]

- 今後の改善案・未実装メモを追加予定（例: 銘柄ごとの lot_size マスタ対応、価格フォールバック戦略など）。

## [0.1.0] - 2026-04-20

### Added / 追加
- プロジェクト初期実装を追加。
  - パッケージ情報:
    - src/kabusys/__init__.py にバージョン情報を追加（__version__ = "0.1.0"）。
  - 環境設定・管理:
    - src/kabusys/config.py
      - .env 自動読み込み（.env, .env.local）。プロジェクトルート探索ロジック（.git または pyproject.toml 基準）。
      - 高度な .env パーサ（export 形式・クォート／エスケープ・インラインコメント処理対応）。
      - 必須環境変数取得ヘルパー（_require）と Settings クラス（環境判定、パス設定、Paper Trading 向け設定等）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - 設定ウィザード CLI:
    - src/kabusys/config_setup.py
      - .env の対話式作成・更新ウィザード。既存値の読み込み、シークレットマスク表示、.env 書き出し機能。
  - 設定検証 CLI:
    - src/kabusys/validate_config.py
      - 環境変数や config/*.yaml の存在・基本妥当性チェック。
      - --strict モード（警告を FAIL 扱い）。
      - PyYAML 未インストール時は YAML 検証をスキップして警告出力。
  - 起動スクリプト:
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は専用 paper DB を使用して本番 DB と分離。
      - BrokerClientFactory 経由でブローカークライアント生成。Engine のスレッド起動、data/stop_requested.flag による停止制御、execution.pid 管理。
    - src/kabusys/run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）。
      - 監視は環境に関わらず本番 sqlite_path を使用する設計（監視 DB の一貫性確保）。
      - stop フラグ検知、例外時のログ出力と次ポーリング継続、KeyboardInterrupt ハンドリング、DB 接続の確実なクローズ。
  - ロギング・プロセス制御ユーティリティ:
    - src/kabusys/utils/logging_setup.py
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
      - ログレベル・ログディレクトリの解決ルール（引数 > 環境変数 > デフォルト）。
    - src/kabusys/utils/process_priority.py
      - Windows / POSIX の差分を吸収したプロセス優先度設定（high/normal/low）。
      - CPU affinity 設定ヘルパー（最初の N コアに固定）。
      - 権限不足や未対応 OS 時は警告を出し安全にスキップ。
  - ポートフォリオ構築関連（純粋関数群 — メモリ内処理）:
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分（全スコア0のフォールバックあり）。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）：既存保有比率を計算して新規候補を除外、"unknown" セクターは上限適用除外。
      - レジーム乗数（calc_regime_multiplier）：bull/neutral/bear に応じた投下資金乗数（デフォルトフォールバックと警告）。
    - src/kabusys/portfolio/position_sizing.py
      - position sizing 実装（risk_based / equal / score）。単元株（lot_size）で丸め、1 銘柄上限・aggregate cap（可用現金超過時のスケーリング）を実装。
      - cost_buffer による手数料・スリッページ見積り、残余キャッシュを用いた端数配分ロジック。
    - src/kabusys/portfolio/__init__.py に各関数をエクスポート。
  - リサーチ・ファクター計算基盤（部分実装）:
    - src/kabusys/research/factor_research.py
      - Momentum / Value / Volatility / Liquidity に関する計算方針と定数を定義。DuckDB 接続を受け prices_daily / raw_financials を参照する設計（関数の一部は未完／途中）。
  - ツール:
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレーディング検証レポート生成スクリプト。稼働率・注文成功率・送信率・レイテンシ（avg/max/P95）を集計して PASS/FAIL 判定を出力。
      - デフォルト DB パス: data/paper_trading.db。--from/--to/--db オプション対応。
  - 監視 DB 初期化ユーティリティ（参照はあるが実装ファイルは別モジュールに存在する想定）:
    - run_* スクリプトが init_monitoring_db を呼び出して監視テーブルの存在を保証。

### Changed / 変更
- （初期リリースのため大きな互換性破壊はなし）コード設計上の決定やデフォルト値を明示。
  - MONITOR_POLL_INTERVAL の取り扱い: 1 未満の値や不正値はデフォルト（60 秒）へフォールバックして警告を出力。
  - ログ出力は stdout を標準出力に使用（cron 等でのリダイレクトを想定）。
  - .env の読み込み優先度: OS 環境 > .env.local > .env（OS 環境は保護され上書きされない）。

### Fixed / 修正
- 複数の堅牢性向上:
  - run_monitoring / run_execution: 例外発生時でも DB 接続を finally で確実に閉じるように設計。
  - logging_setup: ログディレクトリ作成失敗時のフォールバック処理を実装（FileHandler 作成失敗時の警告）。
  - process_priority: 未対応 OS や権限不足時に例外で停止しないよう例外ハンドリングを追加。

### Known issues / 既知の課題（TODO）
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価等のフォールバック価格を使用する検討が必要。
- position_sizing:
  - 銘柄ごとの単元株（lot_size）をマスタ化する拡張が未実装（現在は全銘柄共通の lot_size を想定）。
- research/factor_research.py:
  - ファイル末尾で未完の関数実装がある（途中で切れている）。完全なファクター計算ロジックの実装が必要。
- テスト・ドキュメント:
  - 一部のモジュールでユニットテストや詳細ドキュメント（PortfolioConstruction.md 等への参照はあるが外部ファイル管理）が必要。

### Security / セキュリティ
- 環境変数管理:
  - .env は絶対に Git にコミットしない旨を config_setup で注意喚起。
  - シークレット値はウィザードでマスク表示。

----

配布・運用メモ:
- 本リリースは基本設計・骨格の整備を目的とした初期版です。運用に際しては .env の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）と KABUSYS_ENV の設定を検証してください（python -m kabusys.validate_config を推奨）。
- Paper Trading 実行時は本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH / KABUSYS_ENV=paper_trading を確認）。