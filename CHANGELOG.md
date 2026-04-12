CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

v0.1.0 - 2026-04-12
------------------

Added
- 基本パッケージ構成を追加（kabusys v0.1.0）。
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 実行用エントリスクリプトを追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority.set_process_priority を利用）。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用して DB に接続。
  - run_execution.py
    - ExecutionEngine を起動するスクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し、本番 DB と完全に分離して実行。
    - ブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせてセッションを実行。
    - 起動時にプロセス優先度を "high" に設定。
- ツール: Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - Paper Trading の SQLite ログ（デフォルト data/paper_trading.db）から検証レポートを生成する CLI。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定を出力。
    - コマンドライン引数 --from/--to/--db に対応。
    - 基準値（稼働率 99% など）はファイル内で定義。
- コンフィグ/環境変数ローダー
  - config.py
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml）を起点に自動ロードする機能を追加。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサを実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント規則に対応。
    - Settings クラスを提供し、各種設定値（DB パス、PID ファイル、監視閾値、PAPER_FILL_MODE 等）をプロパティとして取得可能に。
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）。
    - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL のバリデーション。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。スコア合計が 0 の場合は等金額配分へフォールバックし警告。
  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）。unknown セクターは制限対象外、未知レジームは 1.0 でフォールバック。
  - portfolio/position_sizing.py
    - position sizing（calc_position_sizes）。risk_based / equal / score の各方式に対応。
    - 単元（lot_size）丸め、per-stock 上限・aggregate cap スケールダウン処理、コストバッファ（cost_buffer）考慮、余剰キャッシュによる端数配分ロジックを実装。
- 研究（research）モジュール
  - research/factor_research.py
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR20、20日平均売買代金、出来高比率、バリューファクター（PER/ROE）などのファクター計算関数を DuckDB 接続を受け取って実装。
    - データ不足時の None 戻りや集計ウィンドウのバッファ（営業日→カレンダー日換算）を考慮。
  - research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、Spearman ランク相関による IC 計算（calc_ic）、ファクター統計サマリ（factor_summary）、rank ユーティリティを実装。
    - pandas 等の外部依存を使わず、標準ライブラリ + DuckDB で実装。
  - research/__init__.py に主要 API を公開。
- AI ニュース NLP（OpenAI 統合）
  - ai/news_nlp.py
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメントスコアを生成し ai_scores テーブルへ書き込む機能を実装。
    - バッチサイズ制御（最大 20 銘柄/コール）、記事数/文字数のトリム、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスバリデーション、スコアクリップ（±1.0）などを実装。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を利用。未設定時は ValueError を送出。
    - 書き込みは部分失敗時に既存データを保護するため、対象コードのみ置換（DELETE → INSERT の戦略）。
- ユーティリティ
  - utils/process_priority.py
    - Windows / POSIX の差を吸収してプロセス優先度設定（set_process_priority）と CPU affinity 設定（set_cpu_affinity）を提供。
    - 権限不足や未対応 OS の場合、安全にスキップして警告ログを出す実装。

Fixed / Robustness
- .env パースの堅牢化: クォート内部のバックスラッシュエスケープや行内コメントの扱いを明確化。
- Paper Trading レポート: DB が存在しない場合のエラー表示を改善。
- position_sizing の scaling 部分で lot_size 単位での端数処理や残余キャッシュによる追加配分を実装し、スケールダウン後の分配がより再現性を持つように改善。
- research モジュールのクエリは必要最小限のスキャン範囲（カレンダー日バッファ）に制限しパフォーマンスを配慮。

Notes / Caveats
- 監視（run_monitoring）は説明どおり「環境にかかわらず本番 sqlite_path」を使用します。開発環境での誤接続に注意してください。
- calc_news_window は UTC naive datetime を返します（設計上 JST→UTC 変換を内部で行っている点に留意）。
- apply_sector_cap 内の価格欠損処理について TODO コメントあり（price が 0.0 の場合にエクスポージャーが過少見積もられる可能性）。将来的にフォールバック価格を導入する予定。
- DuckDB の executemany に関する制約を考慮した実装（ai/news_nlp.py の置換ロジック）。
- Settings のプロパティは環境変数のバリデーションで ValueError を投げることがあります（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。デプロイ前に .env を正しく設定してください。
- utils.process_priority.set_cpu_affinity は引数に None を渡すと何もしません。cpu_count < 1 の場合は例外を投げます。
- AI モジュールは OpenAI の利用料金・レート制限の影響を受けます。API KEY 管理・レート監視を行ってください。

Security
- OpenAI API キーやその他機密情報は .env / 環境変数経由で設定します。config の .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能です。OS 環境変数は .env の上書きから保護されます。

Breaking Changes
- 本リリースは初回公開のため破壊的変更はありません。

開発者向け補足
- CLI 実行例:
  - 監視ループ起動: python -m kabusys.run_monitoring または直接スクリプト実行（環境に応じて MONITOR_POLL_INTERVAL を設定）。
  - エンジン起動: python -m kabusys.run_execution（paper_trading を使う場合は KABUSYS_ENV=paper_trading を指定）。
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルトの DB パス:
  - monitoring (sqlite): data/monitoring.db
  - paper_trading (sqlite): data/paper_trading.db
  - duckdb: data/kabusys.duckdb

今後の予定（非網羅）
- セクターエクスポージャー計算の価格フォールバック実装。
- 銘柄別 lot_size の導入。
- News NLP の部分失敗時のリトライ戦略・監視通知強化。