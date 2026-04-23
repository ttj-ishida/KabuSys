CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
初期リリース: 0.1.0。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated / Removed / Security: 該当があれば記載

[Unreleased]
-------------

（現在のスナップショットから推測される未リリースの作業や既知の注意点）
- research/factor_research.py の一部（calc_momentum 関数以降）が途中で切れており、実装未完の箇所があります。今後実装・補完予定。
- 一部の TODO コメント（価格フォールバックや lot_size を銘柄ごとに扱う拡張など）が残っています。改善予定。

[0.1.0] - 2026-04-23
--------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを __version__ = "0.1.0" として定義。
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立てを実施。
    - エンジンを別スレッドで起動し、data/stop_requested.flag により安全に停止可能。
    - 実行中の PID を data/execution.pid に書く仕組み（pid_file 経由）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 監視は本番 sqlite_path を環境にかかわらず使用。
- 環境・設定管理
  - config.py: 環境変数ロードと Settings クラスを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env/.env.local の自動ロード（OS 環境変数は保護、.env.local は上書き）。
    - .env の行パースが強化（export プレフィックス、クォート文字列のエスケープ、インラインコメント処理など）。
    - 各種設定プロパティを提供（J-Quants、kabu API、LINE、DB パス、監視閾値、環境種別バリデーションなど）。
    - PAPER_FILL_MODE に対する値検証（instant/partial/never/reject）。
  - config_setup.py: .env 作成・更新の対話式ウィザードを追加。
    - よく使う設定項目を対話で入力して .env を生成。既存 .env の読み込みとマスク表示に対応。
    - ファイルへ書き出すテンプレートを提供（Git に .env をコミットしない旨の注意を含む）。
  - validate_config.py: 設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス親ディレクトリ存在チェック、config/*.yaml の存在および YAML パース（PyYAML があれば検証）。
    - --strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築ロジック（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルソート（score 降順、signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等分配・スコア正規化配分。全スコア 0 の場合は等分配へフォールバック（警告）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限に基づく候補除外ロジック（sell_codes を考慮）。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく株数計算。
    - リスクベース計算（risk_pct、stop_loss_pct を使用）、単元株（lot_size）丸め、1 銘柄上限・全体利用上限の適用。
    - aggregate cap でスケールダウンし、残余キャッシュで fractional 残差を lot 単位で再配分するロジックを実装。
    - cost_buffer を用いた保守的見積り（スリッページ・手数料の概算）。
- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティを追加。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）の設定。
    - ログレベル・ログディレクトリ解決の優先順を実装。ファイル出力失敗時のフォールバック（コンソールのみ）。
    - 既存ハンドラの安全なクローズと再設定を行い二重設定を防止。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux/Mac/FreeBSD）差分を吸収して優先度設定（high/normal/low）を提供。
    - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の場合は警告を出してスキップ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・API レイテンシ（平均/最大/P95）を集計。
    - 各指標の閾値（稼働率 99%、成功率/送信率/レイテンシ等）を定義し、PASS/FAIL 判定のレポートを標準出力に出力。
    - --from/--to/--db オプションで期間・DB を指定可能。デフォルト DB は data/paper_trading.db。
- データ分析・研究
  - research/factor_research.py: ファクター計算モジュール（Momentum/Value/Volatility/Liquidity）を追加（DuckDB 経由で prices_daily/raw_financials を参照）。
    - モメンタム計算のイメージと定数（21/63/126 日、MA200、ATR20、volume 20）を定義。
    - 実装は DuckDB 接続を受け SQL + Python で行う設計。ただし一部関数が未完（本リリース時点で実装途中）。
- パッケージエクスポート
  - portfolio パッケージの __all__ を定義し、主要関数を top-level から import できるようにした。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Notes / Known limitations
- research/factor_research.py の calc_momentum 等が途中で切れているため、ファクター計算の完全実装は次回以降の作業が必要。
- position_sizing の price フォールバックについて TODO コメント有り（価格欠損時の過少見積りリスク）。将来的な改善予定。
- process_priority.set_cpu_affinity は権限・プラットフォームに依存するため、環境によっては動作しない（警告出力でフォールバック）。
- .env 自動ロードはプロジェクトルートが特定できない場合スキップされる。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

Security
- 機密トークン（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、LINE トークン）は .env に保存する設計だが、config_setup ウィザードは .env を Git にコミットしない旨の注意を明記。運用時は機密管理に注意。

作者注
- 本 CHANGELOG は提供されたコードスナップショットから推測して作成したものです。内部実装の詳細や未公開の変更、コミット履歴は反映されていません。必要であれば各モジュールごとに細かな変更点（関数単位の履歴やバグ修正の差分）をコミット履歴から抽出して追記してください。