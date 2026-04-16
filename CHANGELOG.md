CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-04-16
--------------------

Added
- 初期リリースを追加。
- 実行・監視用エントリポイントスクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て、ExecutionEngine のスレッド実行／停止処理を実装。
    - data/execution.pid に PID を書き、 data/stop_requested.flag による停止フラグ検出に対応。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。
    - 例外発生時にもログを残して次のポーリングに進む堅牢化。
- 環境設定管理モジュールを追加（config.py）。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により .env/.env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサは export 句・クォート・インラインコメントを考慮した堅牢な実装。
  - Settings クラスで各種設定値（DB パス、API トークン、Paper Trading 関連設定、監視閾値、環境種別など）を提供。値のバリデーションあり（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。
- ポートフォリオ構築ユーティリティを追加（kabusys.portfolio）。
  - portfolio_builder.py
    - select_candidates: スコア降順＋signal_rank タイブレークによる候補選定。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア正規化配分（スコアが全て 0 の場合は等分にフォールバック）。
  - risk_adjustment.py
    - apply_sector_cap: セクター集中制限の適用（既存保有比率が閾値を超えるセクターの新規候補除外）。"unknown" セクターは上限を適用しない。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは警告後 1.0 フォールバック）。
  - position_sizing.py
    - calc_position_sizes: 重み・候補・リスクベースに応じた発注株数決定。単元株（lot_size）で丸め、per-position 上限・aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差分のロット配分ロジックを実装。
- 研究（research）モジュールを追加。
  - factor_research.py
    - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を用いたモメンタム・ボラティリティ・バリュー系ファクター計算の実装（窓サイズ・データ不足時の None ハンドリング、ログ出力）。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズンの将来リターンを一括クエリで取得（ホライズン検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装。データ不足（有効レコード < 3）時は None。
    - factor_summary / rank: 基本統計量とランク付けユーティリティを実装。
- AI ニュース NLP 初期実装（kabusys.ai.news_nlp）。
  - raw_news を集約して OpenAI API（gpt-4o-mini）へバッチ送信し、銘柄単位の ai_score を ai_scores テーブルへ書き込む設計を追加。
  - 処理設計: 時間ウィンドウ計算、記事トリム（記事数・文字数制限）、20 銘柄バッチ、リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンスバリデーション、スコアの ±1.0 クリップ、部分失敗時の安全なデータ置換（対象コードの限定削除→挿入）。
  - calc_news_window の実装（JST 基準ウィンドウを UTC naïve datetime に変換）。
- ユーティリティを追加（kabusys.utils.process_priority）。
  - set_process_priority: Windows / POSIX を抽象化してプロセス優先度（high/normal/low）を設定。失敗時は警告し続行。
  - set_cpu_affinity: 指定コア数への CPU affinity 固定機能を提供（アクセス権限や未対応 OS の場合は警告してスキップ）。
- ツール: Paper Trading 検証レポート生成スクリプトを追加（kabusys.tools.paper_verification_report）。
  - CLI で SQLite の paper_trading DB を解析し、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）などを出力。閾値判定（PASS/FAIL）を行う。
- パッケージメタ情報を追加（__init__.py の __version__ = "0.1.0"）。

Changed
- （初期リリースのため該当なし）

Fixed
- 環境変数パーサの挙動改善（クォート内のバックスラッシュエスケープ、インラインコメント処理）により .env の柔軟な記述をサポート。
- ポーリングループでの例外ハンドリングを強化（monitor.check_once() の例外をログ出力してループ継続）。
- DuckDB / SQLite クエリでの NULL やデータ不足時の安全な扱い（ファクター計算・レイテンシ計算・レポート集計）を実装し、OperationalError 発生時にデフォルト値でフォールバックする CLI 側ハンドリングを追加。

Security
- （現時点で特記事項なし）

Notes / Known issues
- news_nlp モジュールは API キーが未設定の場合に ValueError を送出する仕様（明示的設定が必要）。また、大量 API 呼び出しを伴うため運用時はレート制限・コストに注意してください。
- run_monitoring は「監視は本番 DB を参照する」設計のため、開発環境での監視実行は DB パスに注意してください。
- set_process_priority / set_cpu_affinity は権限不足や未対応プラットフォームでは警告を出してスキップする実装です。運用環境に応じて権限確認を行ってください。
- position_sizing の lot_size は現状グローバル共通で 100 を想定。将来的に銘柄毎での拡張を想定した TODO コメントあり。

作者
- KabuSys チーム

-----