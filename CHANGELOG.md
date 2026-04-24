# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリースに相当する内容を、ソースコードから推測して記載しています。

全般的な注意
- 日付はリリース作成日: 2026-04-24
- バージョンはパッケージ定義（src/kabusys/__init__.py）に合わせて 0.1.0 としています。

## [0.1.0] - 2026-04-24

### Added
- 基本機能・エントリポイント
  - 実行用スクリプトを追加：
    - run_execution.py — ExecutionEngine の起動スクリプト。スレッドでエンジンを実行し、停止フラグ（data/stop_requested.flag）や PID ファイルを扱う。
    - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。監視は本番用 sqlite_path を使用する。
  - CLI ユーティリティを追加：
    - config_setup.py — 対話式ウィザードで .env を作成／更新するツール（各種設定項目の入力補助、シークレットマスク表示、保存確認）。
    - validate_config.py — 起動前の設定検証ツール。必須環境変数やパス、config/*.yaml の存在やパース（PyYAML があれば検証）をチェック。--strict モードをサポート。
    - tools/paper_verification_report.py — Paper Trading の検証レポート出力ツール。期間指定や DB パス指定が可能。稼働率、注文成功率、送信率、レイテンシ（P95 など）を計算し PASS/FAIL を判定する。
- 設定管理と自動ロード
  - config.py:
    - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）を実装し、.env/.env.local の自動読み込み（OS 環境変数を保護）を行う。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env の柔軟なパース実装（export プレフィックス対応、シングル/ダブルクォート・バックスラッシュエスケープ処理、行内コメント処理等）。
    - Settings クラスを提供し、環境変数への安全なアクセス（必須チェック、デフォルト値、値検証）を統一的に管理。
    - Paper Trading 用の分離された SQLite パス（PAPER_TRADING_SQLITE_PATH）や PAPER_FILL_MODE の検証を実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py:
    - ルートロガーに対する統一的なセットアップ関数を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。LOG_DIR / LOG_LEVEL の解決順を実装。
    - 既存ハンドラのクリア処理や、ログディレクトリ作成失敗時のフォールバック（コンソールのみ）を考慮。
  - utils/process_priority.py:
    - クロスプラットフォームなプロセス優先度設定（"high" / "normal" / "low"）を実装。Windows と POSIX（Linux/Mac/FreeBSD）への対応、失敗時は警告でフォールバック。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（アクセス権限等で失敗する場合は警告）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates、calc_equal_weights、calc_score_weights を実装。スコアが全て 0 の場合は等分配へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap：セクター集中上限の判定と候補除外ロジックを実装（"unknown" セクターは上限適用外）。
    - calc_regime_multiplier：レジーム（bull/neutral/bear）に応じた投下資金乗数を実装。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes：allocation_method（"risk_based"/"equal"/"score"）に基づく株数算出、単元株丸め（lot_size）、1銘柄上限・aggregate cap（利用可能現金に基づくスケーリング）、cost_buffer（手数料・スリッページ見積り）を考慮した配分ロジックを実装。
    - risk_based の場合は stop_loss_pct と risk_pct に基づくポジションサイズ算出を行う。
- リサーチ（ファクター計算）基盤
  - research/factor_research.py（現在のソースはモメンタム計算関数の実装を含む途中状態）：
    - DuckDB 接続を受けて prices_daily / raw_financials を参照し、Momentum / Value / Volatility / Liquidity といったファクター計算の方針を導入。
    - calc_momentum 関数（骨組み）を追加（詳細実装はファイル末尾で未完の可能性あり）。
- 監視データベース初期化ヘルパー
  - monitoring/monitoring_db.py（参照されている init_monitoring_db を起動スクリプトで利用）。監視テーブルを冪等に初期化する処理を使用。

### Changed
- 起動時のプロセス優先度設定を全スクリプトから行う設計に統一（run_execution と run_monitoring は起動直後に set_process_priority("high") を呼び出す）。
- ログ出力の標準化：
  - 全体で logging_setup.setup_logging を利用することで、ログフォーマット・出力先が統一された。
  - コンソール出力は stdout 指定（cron 等でのリダイレクト運用を考慮）。
- 実行環境の分離：
  - Execution（実運用）と Paper Trading（模擬発注）で DB を分離して運用する仕様に明確化（settings.is_paper による切替）。Paper Trading 時は専用の SQLite（data/paper_trading.db）がデフォルトで使用される。
- Configuration 自動読み込みの優先順位明示：
  - OS 環境変数 > .env.local > .env の順で設定が適用され、OS 側の変数は上書き保護される。

### Fixed
- 環境変数パースの改善により、.env 内のクォートやエスケープ、行内コメント、export プレフィックスなどのケースに正しく対応するよう修正（設定誤読の抑制）。
- run_monitoring と run_execution における DB 接続のクローズ処理を finally で保証し、例外発生時もリソースが解放されるようにした。
- monitor.check_once() 内での例外を監視ループ側で捕捉し、ポーリング継続を担保する（単一失敗でループ全体が停止しないように）。

### Notes / Behavioral details
- MONITOR_POLL_INTERVAL（run_monitoring）:
  - 環境変数でポーリング間隔を整数秒で上書き可能。1 未満や不正値はデフォルト 60 秒へフォールバックして警告を出力する。
- 停止制御:
  - data/stop_requested.flag（プロジェクトルート基準）を監視して停止処理を行う。実行中はこのフラグ検知で安全に終了する設計。
- ExecutionEngine 起動フロー:
  - BrokerClientFactory により設定（KABUSYS_ENV）に応じて本番または Mock ブローカーを選択。paper_trading 環境では MockBrokerClient を使い、発注データは専用 DB に分離される想定。
- Paper Verification Report:
  - デフォルト閾値: 稼働率 99%、注文成立率 90%、送信率 95%、P95 レイテンシ 200ms。
  - コマンドラインで期間(from/to) と DB パスを指定可能。DB が存在しない場合はエラーメッセージを出す。
- Settings / 環境変数の検証:
  - Settings クラスは必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を要求し、値の整合性チェック（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）を行う。
  - validate_config.py による事前検証で運用ミスを検出しやすくしている。

### Documentation
- ソース内に各機能の使い方・設計方針（docstring）が充実しており、CLI の使い方やパラメータ仕様が明記されている（config_setup、validate_config、paper_verification_report など）。

### Known limitations / TODO
- research/factor_research.calc_momentum はファイル終端で途中で切れている（実装未完の可能性あり）。ファクター計算の完全実装が必要。
- position_sizing の price 欠損（0.0）に関する注記あり（現在は過少見積りとなる可能性があるため、将来的にフォールバック価格を導入する予定）。
- ログディレクトリ作成やプロセス優先度設定は環境（権限）に依存するため、失敗時には警告を出しフォールバックする設計だが、運用上の注意が必要。

---

タグ:
- 初期リリース: 基本的な実行/監視フロー、設定管理、ポートフォリオ構築、ロギング・プロセス制御、Paper Trading 検証ツールを含むワンパッケージが揃っています。