# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

次の基準に基づき項目を分類しています:
- Added: 新機能
- Changed: 既存機能の改良
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連の修正

## [0.1.0] - 2026-04-16
初回リリース。本リリースでは自動売買システムのコア機能群（実行エンジン起動スクリプト、監視、ポートフォリオ構築、研究用ファクター計算、ニュースNLPスコアリング、ユーティリティ等）をまとめて提供します。

### Added
- 実行・起動関連
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は paper 専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient を通じて発注処理を分離して実行できる。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。起動時にプロセス優先度を設定し、停止フラグファイルで安全にループを終了できる。
- 設定管理
  - config.py: .env / .env.local の自動読み込み機構を追加（プロジェクトルート検出を行い、OS 環境変数を保護するための上書きロジックを備える）。Settings クラスを提供し、各種環境変数を型・値チェック付きで取得できる（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等のバリデーションを含む）。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights：全スコアが 0 の場合は等配分にフォールバック）を実装。
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジームはフォールバックで 1.0 を返す。
  - position_sizing.py: position サイズ決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）での丸め、per-position 上限・aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer を考慮した保守的見積り、スケールダウン後の残差再配分アルゴリズムを提供。
- リサーチ/ファクター計算
  - research/factor_research.py: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、相対ATR、出来高指標）、バリュー（PER/ROE）を DuckDB を用いて計算する関数を追加。欠損データやウィンドウ不足時の NULL ハンドリングあり。
  - research/feature_exploration.py: 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、rank 関数、ファクター統計サマリー（count/mean/std/min/max/median）を追加。外部ライブラリに依存しない実装。
- AI / ニュースNLP
  - ai/news_nlp.py: raw_news を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを算出するモジュールを追加。バッチ処理、トークン肥大化対策、429/ネットワーク/5xx に対する指数バックオフ、レスポンスの厳密な JSON 検証、スコアの ±1.0 クリップ、部分失敗時の既存データ保護（該当 code のみ差し替え）などの設計方針を採用。
  - calc_news_window: ニュース収集ウィンドウ（JST -> UTC 変換）ユーティリティを追加。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成 CLI を追加。期間指定 (--from / --to) と DB パス指定 (--db) に対応。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し、閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）との比較で PASS/FAIL 判定を行う。
- ユーティリティ
  - utils/process_priority.py: Windows / POSIX（Linux/macOS/FreeBSD）に対応したプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。psutil を用いてプラットフォーム差分を吸収し、権限不足等の例外はログで安全にハンドリングする。

### Changed
- パッケージ初期化
  - __init__.py にバージョン情報 __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

### Fixed
- .env パーサーの堅牢化（config._parse_env_line）
  - export プレフィックスに対応、クォート内でのバックスラッシュエスケープ処理、インラインコメントの取り扱い、コメント判定ロジックの改良などを実装。無効な行は無視する。

### Notes / その他
- 設計方針として、研究モジュール・ポートフォリオ構築ロジック・ポジションサイズ計算などは「純粋関数」かつ DB 参照は限定的（DuckDB の prices_daily / raw_financials 等）に留め、実行時の外部副作用を最小化しています。
- Paper Trading 環境では本番 DB と完全分離するように設計されています（PAPER_TRADING_SQLITE_PATH / settings.is_paper 判定）。
- monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する仕様（run_monitoring.py）。
- calc_forward_returns の horizons 引数は 1〜252 日の正の整数のみを許容し、バリデーションを行います。

### Known limitations / 今後の改善候補
- ai/news_nlp.py は本リリース時点で API 呼び出し周りの処理が実装済みだが、実運用でのスループット・コスト制御や詳細なエラーハンドリング（部分的リトライ戦略の細分化等）は運用に応じてチューニングが必要。
- position_sizing.calc_position_sizes における price が欠損（0.0）だった場合のエクスポージャー過小評価問題は TODO コメントとして残しており、将来的に前日終値や取得原価でのフォールバックを導入する余地がある。
- apply_sector_cap は "unknown" セクターを上限適用外とする仕様だが、必要に応じて未知セクターの取り扱いポリシーを明確化する予定。

## 未分類 / 参考情報
- 環境変数による挙動切替:
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）。0 以下は無効でデフォルトにフォールバック。
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（validationあり）
  - PAPER_FILL_MODE: paper trading の fill 動作 ("instant"|"partial"|"never"|"reject")（validationあり）
  - PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH 等で DB パスを指定可能。
  - OPENAI_API_KEY: ai/news_nlp で使用。

---

（今後のリリースでは、各コンポーネントのユニットテスト追加、ドキュメント整備、運用でのログ・メトリクス強化、API レート制御の改善等を予定しています。）