CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティクスは semver を想定します。

Unreleased
----------

Added
- run_monitoring スクリプトを追加/改善
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
  - 停止フラグ data/stop_requested.flag を検知して安全にループを終了。
  - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用する仕様を明確化。
  - 起動時にプロセス優先度を "high" に設定。

- run_execution スクリプトを追加/改善
  - KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し本番 DB と分離。
  - BrokerClientFactory によるブローカークライアント生成を実装し、MockBroker の利用を明確化。
  - ExecutionEngine の起動管理（PID ファイル、停止フラグ検知、デーモンスレッド実行）を実装。
  - 起動時にプロセス優先度を "high" に設定。

- 環境設定（kabusys.config）
  - .env 自動ロード機能を追加（プロジェクトルート検出: .git / pyproject.toml を基準）。
  - .env/.env.local の読み込み順序と上書きルール（OS 環境変数保護）を明確化。
  - .env 行パーサを強化（export 形式対応、クォート内エスケープ、インラインコメント処理）。
  - 各種設定プロパティを追加・検証:
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
    - DB パス、PID/kill フラグパス、監視閾値（CPU/Memory/Disk）、環境文字列（development/paper_trading/live）等。
  - settings オブジェクトを公開。

- ポートフォリオ構築モジュール（kabusys.portfolio）を追加
  - portfolio_builder:
    - select_candidates: スコア降順＋signal_rank によるタイブレークで候補選定。
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合は等分配にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中チェックによる候補除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear を定義、未知は警告の上フォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した発注株数計算。
    - 単元（lot_size）丸め、per-position 上限・aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的見積りを実装。
    - aggregate スケールダウン時の残差処理（lot 単位での追加配分）を実装。

- 研究（research）モジュールを追加
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（DuckDB を使用）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率の計算。
    - calc_value: EPS/ROE に基づく PER/ROE 計算（raw_financials の最新レコードを取得）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得。
    - calc_ic / rank / factor_summary: スピアマン IC、ランク計算（同順位の平均ランク）、ファクター統計サマリーを実装。
  - DuckDB 専用クエリと、データ不足時の None 返却等の堅牢性を考慮。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を銘柄ごとに集約して OpenAI（gpt-4o-mini）に JSON Mode で投げるスコアリングワークフローを実装。
  - バッチ処理（最大 _BATCH_SIZE=20）、トークン肥大化対策（1銘柄あたり記事数・文字数制限）、429・ネットワーク・5xx に対するエクスポネンシャルバックオフでのリトライを実装。
  - 出力検証、スコア ±1.0 にクリップ、部分更新（該当コードのみ置換）による障害耐性を確保。
  - ニュース時間ウィンドウ計算ユーティリティ calc_news_window を提供。

- ツール: Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - データベース（paper_trading.db）からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計して人間向けレポートを出力。
  - 判定基準（閾値）を定義し PASS/FAIL を表示。
  - コマンドライン引数 --from / --to / --db をサポート。

- ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level): Windows / POSIX を吸収してプロセス優先度設定（high/normal/low）。
  - set_cpu_affinity(cpu_count): 最初の N コアにピン留めするユーティリティを実装。
  - 権限不足や未対応 OS では警告を出して安全にフォールバック。

Changed
- ログ出力と初期ログレベルを各起動スクリプトで INFO に設定。
- DB 初期化処理（init_monitoring_db）を起動時に必ず呼ぶようにし、監視テーブルが存在することを保つ（冪等処理）。
- ExecutionEngine 起動フローをスレッド実行に変更し、停止フラグ検知で安全に engine.stop() を呼び出すロジックを追加。

Fixed
- MONITOR_POLL_INTERVAL の値が不正（0 以下や非数）な場合にデフォルトにフォールバックして ValueError を回避（警告ログを追加）。
- .env パーサのクォート／エスケープ対応とインラインコメント処理を改善し、より現実的な .env の記述に耐性を持たせた。

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決し、未設定時は明示的にエラーを返すようにして不正なデフォルト利用を防止。

0.1.0 - 2026-04-17
-----------------

Added
- 初期リリース: KabuSys v0.1.0 を公開。
  - 自動売買のコア機能群を実装:
    - 実行エンジン起動スクリプト（run_execution）。
    - 監視ポーリングループ（run_monitoring）。
    - 環境設定ロード/検証（kabusys.config）。
    - ポートフォリオ構築（kabusys.portfolio）。
    - 注文サイズ計算とリスク制限（position_sizing, risk_adjustment）。
    - 研究用ファクター計算 & 特徴量解析（kabusys.research）。
    - ニュース NLP ベースのセンチメントスコアリング基盤（kabusys.ai.news_nlp）。
    - Paper Trading 用検証レポート生成ツール（kabusys.tools.paper_verification_report）。
    - ユーティリティ群（プロセス優先度・CPU affinity 等）。
  - DuckDB / SQLite を用いたデータアクセス基盤を前提に設計。
  - Paper Trading と Live を分離する設計（paper_trading 用 DB の分離、MockBroker 利用）。

Changed
- パッケージの __version__ を 0.1.0 に設定。

Notes / Known issues
- news_nlp モジュールは複雑な外部 API 呼び出しを含むため、実運用前に OpenAI API のレート制限やコスト管理の確認・テストを推奨します。
- 一部の機能（例: price のフォールバックロジック、銘柄別 lot_size の扱い）は TODO コメントが残っており、将来的な拡張を想定しています。
- DuckDB の executemany の制約や SQL の存在有無に対しては defensive に扱っていますが、既存の DB スキーマが揃っていることが前提です。

履歴の書き方について
- この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴・公開リリースに応じて適宜修正・分割してください。