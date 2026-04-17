CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（現時点で未リリースの変更はありません）

0.1.0 - 2026-04-17
-----------------

Added
- プロジェクト初期リリース。
- 実行/監視用スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイント。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用して本番 DB と完全分離する挙動を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグファイル検出による安全停止処理を実装。
- 設定管理モジュールを追加（kabusys.config）
  - .env 自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml）。
  - .env/.env.local の読み込み順や既存 OS 環境変数の保護を考慮したロードロジック。
  - export KEY=val、クォート文字列、インラインコメント等に対応する堅牢なパーサ実装。
  - Settings クラスに各種プロパティ（DBパス、Paper Trading 設定、監視閾値、環境判定等）を実装。PAPER_FILL_MODE 等の入力検証を追加。
- Paper Trading 検証レポートツールを追加（kabusys.tools.paper_verification_report）
  - 指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ等を集計してレポート出力。
  - P95 計算、閾値（稼働率/成功率/レイテンシ）に基づく PASS/FAIL 判定を実装。
  - CLI オプション --from/--to/--db をサポート。
- ポートフォリオ構築モジュールを追加（kabusys.portfolio）
  - portfolio_builder: シグナル選別（select_candidates）、等配分/スコア加重（calc_equal_weights / calc_score_weights）。
    - スコア同点のタイブレークは signal_rank の昇順で決定。
    - 全銘柄スコアが 0 の場合は等配分へフォールバック（警告ログ）。
  - risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
    - 不明セクターはセクター上限の対象外として扱う等の詳細挙動を実装。
    - 未知のレジームはフォールバック multiplier=1.0（警告ログ）。
  - position_sizing: 株数決定ロジック（risk_based / equal / score）、単元株丸め、per-stock および aggregate cap（利用可能現金へのスケーリング）を実装。
    - lot_size 単位で丸め、コストバッファ（手数料/スリッページ想定）を考慮した安全な配分調整を実装。
- 研究・リサーチ機能を追加（kabusys.research）
  - factor_research: Momentum / Volatility / Value ファクター算出（DuckDB を用いた SQL 実装）。
    - mom_1m/3m/6m、MA200 乖離、ATR20、平均売買代金等を計算。
    - データ不足時の None 返却、ウィンドウサイズとスキャン緩衝の実装を含む。
  - feature_exploration: 将来リターン算出（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ファクター統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）。
    - horizons の入力検証、重複排除、単一クエリでの取得などを実装。
  - research パッケージから主要関数をエクスポート。
- ニュース NLP モジュールを追加（kabusys.ai.news_nlp）
  - raw_news を OpenAI（gpt-4o-mini）でセンチメント解析して ai_scores に書き込む処理フローを設計・実装（バッチ化、トークン肥大化対策、バリデーション、スコアクリップ、リトライ等）。
  - calc_news_window および score_news の骨子を実装。API キー解決とタイムウィンドウ計算を実装。
  - （注）ソースは大きいため一部処理はモジュール内に実装済み／設計済だが、外部依存のテスト・実行は環境依存。
- ユーティリティ
  - process_priority（kabusys.utils.process_priority）: Windows / POSIX の差を吸収するプロセス優先度設定、CPU affinity 固定機能を実装。アクセス権限や未対応 OS の場合は安全にスキップして警告ログを出力。
- DB 関連
  - DuckDB と SQLite の両方を利用する設計を導入（prices_daily 等は DuckDB、監視/実行ログは SQLite）。init_monitoring_db による監視テーブル初期化処理を実行箇所で保証。

Changed
- なし（初回リリースのため履歴なし）

Fixed
- なし（初回リリースのため履歴なし）

Security
- なし

Notes / 実装上の注意点
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。プロジェクトルートが特定できない場合は自動ロードをスキップする安全設計。
- run_monitoring は KABUSYS_ENV にかかわらず「本番 sqlite_path」を監視用 DB に使用する挙動（意図的な運用仕様）。
- run_execution は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と分離するよう明確に実装。
- position_sizing や risk_adjustment のいくつかの箇所は現時点で簡易フォールバック（価格欠損 → スキップ、未知値 → フォールバック）を採っており、将来的にマスタ・フォールバック価格取得などでの強化を検討。
- ai/news_nlp は外部 API（OpenAI）へ実際にアクセスするため、API キーや利用制限、レスポンスフォーマットの変更に注意が必要。

著者
- KabuSys チーム

もし特定のファイルや機能ごとにより詳細な変更ログ（例: 関数単位の細かな実装差分）を出力したい場合は、対象ファイルを指定してください。コード差分が得られれば、より細かい変更点を追記できます。