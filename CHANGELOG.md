CHANGELOG.md

すべての注目すべき変更はこのファイルに記録します（Keep a Changelog 準拠）。
初期リリースでは、現行コードベースから推測される主要機能・改善点をまとめています。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更/改善
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当があれば記載

Unreleased
---------
（現在の開発中の変更はここに記載します）

0.1.0 - YYYY-MM-DD
------------------
初回公開リリース（コードベースから推測された主要機能、モジュール構成および動作仕様をまとめています）。

Added
- 全体
  - プロジェクトの初期バージョンを追加。パッケージ情報は kabusys.__version__ = "0.1.0"。
  - DuckDB と SQLite を併用するデータ処理基盤を採用（prices_daily / raw_financials 等を DuckDB で集計、監視データや実行ログは SQLite）。
- 実行・監視
  - run_execution.py: 実行エンジン起動スクリプトを追加。
    - ExecutionEngine の起動フローを実装（BrokerClient の生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て）。
    - Paper Trading モード（KABUSYS_ENV=paper_trading）では専用の SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と完全分離。
    - 起動時にプロセス優先度を "high" に設定する仕組みを導入。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔を MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する挙動を明記。
    - プロセス優先度設定（high）を実行開始時に行う。
- 設定読み込み（kabusys.config）
  - .env 自動ロード機能を実装（プロジェクトルート検出：.git または pyproject.toml を探索）。
  - .env/.env.local の読み込み順序を実装（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサを強化：export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い等に対応。
  - Settings クラスを提供し、環境変数の取得・検証をプロパティとして提供（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE のバリデーション等）。
- ユーティリティ
  - process_priority モジュールを追加。
    - set_process_priority(level) で Windows / POSIX を吸収したプロセス優先度設定を提供（"high" / "normal" / "low"）。
    - set_cpu_affinity(cpu_count) でプロセスを最初の N コアにピン留め可能（未指定時は変更しない）。
    - 権限不足や未対応環境では警告ログを出して安全にフォールバック。
- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder: シグナル選定（select_candidates）、等配分/スコア加重配分（calc_equal_weights / calc_score_weights）を実装。スコア全0時のフォールバックロジックを搭載。
  - risk_adjustment: セクター集中チェック（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。未知のレジームは警告を出してフォールバック。
  - position_sizing: 発注株数決定ロジックを実装（risk_based / equal / score の allocation_method 対応）。単元株丸め、per-position 上限、aggregate cap（利用可能現金を超える場合のスケーリング）および残差配分ロジックを実装。手数料/スリッページ見積り用 cost_buffer を考慮。
- 研究（kabusys.research）
  - factor_research: モメンタム、ボラティリティ、バリュー系ファクター計算を DuckDB 上の SQL で実装（calc_momentum, calc_volatility, calc_value）。長期 MA・ATR 等の窓計算、データ不足時の None 戻しに対応。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（spearman ランク相関）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージから zscore_normalize（kabusys.data.stats 経由）等を公開。
- AI / ニュース（kabusys.ai）
  - news_nlp モジュールを追加。
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（-1.0〜1.0）を評価して ai_scores に書き込むワークフローを実装。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）や、1銘柄あたりのトークン肥大化対策（記事数上限 / 文字数上限）を実装。
    - 最大 20 銘柄単位でのバッチ送信、429/ネットワーク/5xx に対する指数バックオフ retry、レスポンス構造のバリデーション、スコアの ±1.0 クリップ、部分失敗時の既存スコア保護（対象コードに絞った削除→挿入）など堅牢な設計。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から各種指標（稼働率、注文成功率、送信率、リスク却下数、平均/最大/P95 レイテンシ）を集計して標準出力にレポート出力。閾値（稼働率99%、Fill率90% 等）による PASS/FAIL 判定を実装。
  - P95 計算を自前実装（データ不足時の N/A ハンドリング）。
- データベース初期化
  - monitoring_db.init_monitoring_db を用いて監視テーブルの冪等な初期化処理を実行（run_execution/run_monitoring 起動時に保証）。

Changed
- 設定・環境周り
  - 環境変数の読み込み戦略を明確化（OS 環境を保護しつつ .env/.env.local を読み込む）。
  - Settings による厳密なバリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）を導入し、誤設定時に早期に検出。
- ログ出力
  - 起動スクリプトで logging.basicConfig(level=logging.INFO) を呼び出して基本ログレベルを設定（実稼働では設定の上書きを想定）。

Fixed
- env パーサの改善により、クォート内のバックスラッシュエスケープや export プレフィックス、インラインコメント解釈の不具合を回避。
- ポジティブでない MONITOR_POLL_INTERVAL 値に対して ValueError を避け、警告を出してデフォルトにフォールバックする安全策を追加。

Security
- OpenAI API 使用時に API キーが未設定の場合は ValueError を送出して明示的に失敗させる（誤った挙動でキーを露出させないため）。

Notes / TODO（コード内コメントから推測）
- position_sizing: price 欠損時のフォールバック価格（前日終値や取得原価）の活用や、銘柄別 lot_size の将来的拡張。
- apply_sector_cap: "unknown" セクターは上限適用除外となる設計。将来的検討事項あり。
- news_nlp: executemany 前の params 空チェック（DuckDB 制約）等、部分失敗での既存データ保護を意識した実装。
- 一部の機能（例: EngineConfig の細かいパラメータ、ExecutionEngine 内の実装詳細、monitoring の詳細スキーマ）はこの変更履歴の範囲外（実装ファイルに依存）。

以上

（この CHANGELOG はコードベース内のコメント・関数名・ログ文・仕様記述から推測して作成しています。実際のリリース履歴や日付はリポジトリの git 履歴等に基づいて更新してください。）