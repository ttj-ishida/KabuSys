CHANGELOG
=========

すべての注目すべき変更点を記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

[0.1.0] - 2026-04-13
-------------------

Added
- プロジェクト初期リリース。
- コアモジュールを追加:
  - kabusys.config: 環境変数/.env ファイル読み込み機能。.env/.env.local のロード順序と OS 環境変数保護を実装。プロジェクトルート (.git または pyproject.toml) を起点に自動検出して読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラス: 各種設定値をプロパティで提供（DB パス、API トークン、監視閾値、環境判定など）。値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を含む。
  - 実行/監視エントリポイント:
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading のときは paper_trading 用 SQLite（data/paper_trading.db 既定）を使用し MockBroker 経由で完全分離して動作。起動時にプロセス優先度を "high" に設定。
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（既定 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する設計。
  - monitoring.init_monitoring_db を呼ぶことで監視用テーブル群の存在を保証（冪等）。
  - utils.process_priority: プラットフォーム差分を吸収したプロセス優先度設定（Windows / POSIX 対応）、CPU affinity 固定ユーティリティを提供。権限不足や未対応 OS に対するフォールバックとログ出力あり。
  - portfolio:
    - portfolio_builder: シグナル選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - risk_adjustment: セクター集中制限 apply_sector_cap、レジーム乗数 calc_regime_multiplier（bull/neutral/bear）を実装。
    - position_sizing: 発注株数計算 calc_position_sizes。risk_based / equal / score の配分方式をサポートし、単元株丸め、per-position 上限、aggregate cap（available_cash に基づくスケーリング）、cost_buffer を考慮した安全なスケーリングロジックを実装。
  - research:
    - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を用いた SQL ベースの実装）。MA200, ATR20, 各種モメンタムなどを計算し、不足データ時に None を返す挙動を定義。
    - feature_exploration: 将来リターン計算 calc_forward_returns、スピアマンランク相関による IC 計算 calc_ic、rank/統計サマリー機能を実装。pandas に依存せず純標準ライブラリで実装。
    - research パッケージに zscore_normalize（kabusys.data.stats から）を公開。
  - ai.news_nlp: OpenAI を用いたニュースセンチメントスコアリング機能。処理設計として
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST 相当）で記事を集約、
    - 銘柄ごとに記事数/文字数上限を設けてトリム、
    - 最大バッチサイズ 20 銘柄で API に送信、
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ、
    - レスポンスを厳密 JSON として検証、スコアを ±1.0 にクリップ、
    - 成功した銘柄のみ ai_scores テーブルに安全に置換（部分失敗時に既存データ保護）、
    を実装。
  - tools.paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計し PASS/FAIL 判定を行う。閾値はソースに明示（稼働率 99%、成立率 90% 等）。コマンドライン引数で期間指定可能（--from/--to/--db）。
  - パッケージエクスポートを整備（kabusys.__init__, kabusys.portfolio.__init__, kabusys.research.__init__ など）。

Changed
- 設計方針・安全策を導入:
  - DB 操作・外部 API 呼び出しについてフェイルセーフにし、例外時はログを出して処理を継続する箇所を多数実装（監視ループの例外ハンドリング、AI スコア取得の個別チャンク保護など）。
  - .env のパーサーは export 構文、クォート、エスケープ、インラインコメントの扱いをサポートし、より現実的な .env スタイルに対応。
  - settings の一部で未設定時に ValueError を投げて明示的にエラーにする（必須キーの保障）。
  - run_execution では paper_trading 環境向けに DB を分離し、本番 DB と混在しない設計とした（デフォルト file: data/paper_trading.db）。
  - DuckDB と SQLite を併用するアーキテクチャ（分析用に DuckDB、トランザクション/監視に SQLite）を明示。

Fixed
- 環境値/引数検証の追加:
  - MONITOR_POLL_INTERVAL の値が 0 以下や非数の際にデフォルトへフォールバックし、ログで警告を出す実装を追加（run_monitoring）。
  - PAPER_FILL_MODE の許容値チェックを実装し、不正な値は ValueError を返すようにした。
  - calc_forward_returns の horizons 引数に対するバリデーション（正の整数かつ上限 252）を追加。
- ロバストネス向上:
  - DuckDB executemany の制約を考慮した空パラメータ回避やデータ欠損時の安全なフォールバック（ファクター計算・レポート生成等）。

Security
- OpenAI API キーの取り扱い: score_news は引数 api_key または環境変数 OPENAI_API_KEY を使用。未設定時は明示的なエラーを出す（無効な運用での誤動作防止）。

Notes / Usage highlights
- 実行/監視:
  - 監視ループのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で制御（秒）。不正値はデフォルト 60 秒にフォールバック。
  - 実行エンジンは起動時にプロセス優先度を "high" に設定しようとする（権限不足時は警告）。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH で上書き可）を使用。MockBrokerClient を用いて本番 DB と分離された検証が可能。
  - PAPER_FILL_MODE により paper の約定挙動を制御（instant|partial|never|reject）。
- 環境ファイル:
  - .env/.env.local の自動読み込みが有効（プロジェクトルート検出に成功した場合）。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Removed
- なし（初回リリース）。

Deprecated
- なし。

今後の予定（提案）
- position_sizing: 銘柄別の単元株数 lot_size を stocks マスタから取得する拡張。
- apply_sector_cap: price 欠損時のフォールバック価格（前日終値等）の導入。
- ai.news_nlp: より堅牢なスキーマ検証、レスポンス異常時の監査ログ強化。
- research: 追加ファクター（PBR、配当利回りなど）実装や計算の最適化。

---
本 CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴・リリースノートと異なる場合があります。必要であれば、実際の変更差分（git log 等）を元に追記・修正してください。