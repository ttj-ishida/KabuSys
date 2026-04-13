# Changelog

すべての重要な変更点をここに記載します。本ファイルは「Keep a Changelog」仕様に準拠します。

フォーマット:
- 変更はカテゴリ別に整理（Added, Changed, Fixed, Deprecated, Removed, Security）。
- 各リリースはバージョンと日付を付記。

## [Unreleased]
（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-04-13

初回公開リリース。本リリースでは自動売買システム「KabuSys」のコア機能および開発・検証向けのユーティリティ群を実装しています。

### Added
- 一般
  - パッケージ初期バージョンを定義。__version__ = "0.1.0" を追加。
  - アプリケーション設定管理モジュール（kabusys.config）を実装。
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - 環境変数パーサ（export 文対応、クォート文字とバックスラッシュエスケープ、インラインコメント処理）。
    - Settings クラスで各種設定プロパティを提供（DBパス、PID/killフラグ、閾値、環境判定など）。
    - 設定値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
- 実行スクリプト / ランタイム
  - 実行用スクリプトを追加。
    - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite を使用し MockBroker を利用する設計（本番 DB と分離）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。
  - プロセス優先度 / CPU 固定ユーティリティ（kabusys.utils.process_priority）を提供。
    - Windows / POSIX を吸収した優先度設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定するユーティリティ。
    - 権限不足や未対応環境時は警告を出してスキップするフェールセーフ実装。
- データベース / モニタリング
  - duckdb 統合（DuckDBPyConnection を使用する研究・AIモジュール向け）。
  - monitoring 用 DB 初期化ユーティリティ呼び出し（init_monitoring_db）。
  - 監視処理は本番の sqlite_path を使用して動作（run_monitoring の挙動として明示）。
- Execution（発注）関連
  - ExecutionEngine 周りの組立て処理（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）を組み込む起動フローを実装。
  - RiskManager のデフォルト設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を反映。
- Portfolio 構築
  - portfolio モジュールを実装。
    - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights。スコア合計が 0 の場合は等配分へフォールバック）。
    - position_sizing: 各銘柄の発注株数算出（risk_based / equal / score）。単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash に応じたスケールダウン）、cost_buffer を考慮した保守的見積もりと端数配分ロジックを実装。
    - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier。未登録レジームは警告してフォールバック）。
- リサーチ（ファクター計算 / 特徴量探索）
  - research モジュールを実装。
    - factor_research: モメンタム（1/3/6M リターン、MA200 乖離）、ボラティリティ（ATR、相対 ATR、出来高指標）、バリュー（PER、ROE）を DuckDB SQL で計算する関数を提供。
    - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）、ファクター要約統計量を実装。外部依存（pandas 等）を使わず標準ライブラリで計算。
- AI（ニュース NLP）
  - ai.news_nlp モジュールを実装。
    - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価フローを実装。
    - タイムウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 を UTC に変換）。
    - 記事集約、銘柄ごとのトリム（記事数・文字数制限）、バッチ処理（最大 20 銘柄/回）、レスポンスバリデーション、スコアクリッピング（±1.0）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）。
    - ai_scores テーブルへの部分置換（対象コードのみ DELETE → INSERT）で部分失敗に強い更新戦略。
- ツール
  - tools/paper_verification_report.py を追加。Paper Trading 用 DB を解析し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を算出して PASS/FAIL 判定するレポートを CLI で出力。閾値や出力フォーマットを定義。

### Changed
- 起動時ログ/優先度設定
  - run_execution / run_monitoring の起動フローは最初に set_process_priority("high") を呼ぶことでプロセス優先度を上げる設計に統一。
- DB パスの取り扱い
  - run_execution は paper_trading 環境を検出して専用 SQLite を使用する（settings.is_paper）。一方 run_monitoring は環境にかかわらず本番 sqlite_path を使用する旨を明示。
- 環境変数ロード優先度
  - OS 環境変数 > .env.local > .env の順でロード。システム側の既存環境変数は保護され、.env.local は上書き可能だが OS 環境変数は優先。

### Fixed
- 環境変数パーサの堅牢化
  - export プレフィックス、クォート付き値内のバックスラッシュエスケープ、インラインコメントの取り扱いを改善して .env の柔軟性と安全性を向上。
  - _parse_env_line の無効行処理やキー存在チェックを明示化。
- モニタリング間隔の堅牢化
  - MONITOR_POLL_INTERVAL の値が整数でない、または 0 以下の場合は警告を出してデフォルト（60 秒）にフォールバックする処理を追加（run_monitoring._get_poll_interval）。
- ポジションサイズ計算の安全弁
  - calc_position_sizes における aggregate cap 適用時のスケーリングと端数配分を lot_size 単位で行い、合計コストが available_cash を超える場合でも安全にスケールダウンするロジックを実装。
- スコア加重配分のフォールバック
  - calc_score_weights で合計スコアが 0 の場合は等金額配分にフォールバックし、警告を出すように修正。
- レジーム乗数のフォールバック
  - calc_regime_multiplier は未知のレジーム値を受けた際に警告を出し、デフォルト multiplier=1.0 でフォールバックするように変更。
- process_priority の例外処理強化
  - 権限不足や未実装 API に対する例外（psutil.AccessDenied, AttributeError, NotImplementedError）を捕捉して警告を出し、プロセスを継続させるようにした。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（本版ではセキュリティ関連の変更は記載なし）

---

注意:
- 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際の変更履歴（コミットログやリリースノート）がある場合は、それを優先して反映してください。
- 将来的なリリースでは、セキュリティ修正や API 変更（互換性破壊）が発生する可能性があります。Breaking change がある場合は「Changed」や専用の「Breaking Changes」セクションで明示してください。