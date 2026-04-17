# CHANGELOG

すべての重要な変更を記録します。形式は「Keep a Changelog」に準拠しています。  
リリース日や内容は、コードベースの実装内容から推測して記載しています。

注: このファイルはコードの内容（関数・挙動・ドキュメント文字列等）から推測して作成した変更履歴です。実際のコミット履歴とは差異がある可能性があります。

Unreleased
----------
- （現時点の未リリース変更はありません。）

[0.1.0] - 2026-04-17
--------------------
Added
- 基本パッケージ情報を追加
  - kabusys パッケージのバージョンを `__version__ = "0.1.0"` として設定。
- 実行用エントリポイント
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite を使用し、本番 DB と分離。
    - BrokerClientFactory を通じたブローカークライアント生成（MockBrokerClient を利用可能）。
    - ExecutionEngine をデーモンスレッドで実行し、data/stop_requested.flag による安全停止、execution.pid の取り扱い。
    - RiskManager, OrderManager, Reconciler 組立てと初期設定（RiskConfig の既定値含む）。
  - run_monitoring.py: システム監視（SystemMonitor）ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず本番用 sqlite_path を使用する旨を明示。
    - 停止フラグファイルの検出、例外時のログ出力、接続クローズを実装。
- 設定管理
  - config.Settings クラスを追加し、環境変数から設定値を取得する API を提供。
    - 自動 .env ロード機能（プロジェクトルート検出：.git または pyproject.toml）。
    - .env と .env.local の読み込みルール（OS 環境変数を保護、.env.local が上書き）。
    - 複雑な .env パース機能（export プレフィックス、クォート内のエスケープ、行末コメント処理等）。
    - 多数のプロパティ（J-Quants / kabu API トークン、DB パス、paper_trading 関連、監視閾値、ログレベル、環境種別判定等）。
    - 入力検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の有効値チェック）。
- ポートフォリオ構築モジュール（純関数群）
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルのスコアソート／上位 N 選択。
    - calc_equal_weights / calc_score_weights: 重み付けロジック（score が全て 0 の場合は等配分にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄をエクスポージャー計算から除外可能、unknown セクターは上限適用除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数。
  - portfolio.position_sizing
    - calc_position_sizes: allocation_method に応じた株数決定ロジック（risk_based / equal / score）。
      - lot_size（単元株）丸め、per-position 上限、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer による保守的見積り。
      - スケール時には残差を lot 単位で再配分するロジックを実装。
- 研究（research）モジュール
  - research.factor_research
    - calc_momentum / calc_volatility / calc_value：DuckDB を用いたファクター計算（MA200、ATR20、PER/ROE 等）。
    - 不足データ時は None を返す設計。
  - research.feature_exploration
    - calc_forward_returns：任意ホライズンの将来リターンをまとめて取得（horizons の検証あり）。
    - calc_ic：Spearman（ランク）による IC 計算（有効レコード < 3 の場合は None を返す）。
    - rank / factor_summary：ランク付け（同順位は平均ランク）・基本統計量計算。
  - research パッケージは zscore_normalize を外部（kabusys.data.stats）からインポートして公開。
- AI ニュース NLP（OpenAI 連携）
  - ai.news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込む処理を実装。
    - ニュース収集ウィンドウ（JST 基準）計算ユーティリティ calc_news_window。
    - バッチ処理（最大銘柄 20 件/回）、1 銘柄あたり記事数/文字数上限の施策。
    - レート制限・ネットワーク障害・5xx 等に対する指数バックオフとリトライ。
    - 出力 JSON の厳密検証、スコアの ±1.0 クリップ、部分成功時のテーブル更新（対象コードに限定して置換）。
    - API キー未指定時の明示的エラー。
- ツール
  - tools.paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - コマンドライン引数 --from / --to / --db をサポート。
    - system_status / trade_logs / risk_logs を参照して稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL レポートを標準出力に出力。
    - デフォルト閾値（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200 ms）を設定。
    - P95 の計算ロジック、メトリクス欠損時の N/A ハンドリング。
- ユーティリティ
  - utils.process_priority
    - set_process_priority: Windows / POSIX を吸収したプロセス優先度設定（Windows 定数 / nice 値対応）。
    - set_cpu_affinity: カレントプロセスの CPU affinity を設定するユーティリティ（引数検証、アクセス権失敗時は警告）。
    - 例外（AccessDenied 等）発生時はログでフォールバックする堅牢な実装。

Changed
- （初版のため過去の変更はありません。上記が初期導入内容です。）

Fixed / Robustness
- 環境変数パースの堅牢化
  - .env の export プレフィックス、クォート中のバックスラッシュエスケープ、行末コメントの扱いを考慮したパーサを実装。
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- 各種フォールバック・安全策の追加
  - calc_score_weights: 全スコアが 0 の場合は等金額配分にフォールバックして警告を出力。
  - run_monitoring の MONITOR_POLL_INTERVAL は不正値であればデフォルト 60 秒にフォールバックし警告ログを出力。
  - factor / research / portfolio 関数はデータ不足時に None や空集合を返し、上位呼び出しでの安全な扱いを想定。
  - process_priority / set_cpu_affinity / OpenAI 呼び出し周りはアクセス権限や API エラーを捕捉して処理継続（警告ログ）する設計。
- run_execution/run_monitoring の停止処理を堅牢化
  - stop フラグファイルの検出で安全に終了するループ設計、スレッド join のタイムアウト付き待機を実装。
  - run_execution では起動前に停止フラグが立っている場合は起動せず終了するように。

Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で取得し、未設定時は ValueError を送出して安全に中断。

Deprecated
- （なし）

Removed
- （なし）

Notes / TODO（コード中明記の将来改善点）
- position_sizing: 銘柄別 lot_size を将来的にサポートするための設計メモあり（現在は共通 lot_size を使用）。
- risk_adjustment.apply_sector_cap: price 欠損時（0.0）だとエクスポージャーが過少見積りされる問題に対する注記。
- ai.news_nlp: 処理途中の実装がファイル末尾で未完の箇所（切れ）を示唆（実装の継続が必要）。

ライセンス・貢献
- 本 CHANGELOG はコードベースから推測して作成したものであり、実際の変更履歴・リリースノートはリポジトリのコミット履歴を基に作成することを推奨します。