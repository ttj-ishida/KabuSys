Keep a Changelog 準拠の CHANGELOG.md（日本語）を以下に作成しました。コードベースの内容から推測して記載しています。

CHANGELOG.md
-------------

すべての変更は https://keepachangelog.com/ja/ に準拠して記載しています。

フォーマット: 年.月.日 の日付はソースから明示的に得られないため省略しています。主要リリースは __version__ に基づく v0.1.0 を初期リリースとして記載しています。

Unreleased
----------
- （今後の変更をここに記載）

v0.1.0
-----
Added
- 基本パッケージ構成を追加
  - パッケージメタ情報: kabusys/__init__.py にバージョン 0.1.0 を設定。
- 実行用エントリポイント
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト配下 data/stop_requested.flag の存在で検知。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する仕様。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderManager / OrderRepository / RiskManager / Reconciler の組み立て、ExecutionEngine の非同期実行（スレッド）を実装。
    - 停止フラグ検知でエンジン停止を安全に行う処理を追加。
    - 実行用 PID ファイル管理（data/execution.pid）。
- 設定管理
  - config.py: 環境変数/.env 読み込みおよび Settings クラスを実装。
    - プロジェクトルート検出（.git または pyproject.toml を基準）。
    - .env/.env.local の自動読み込み（OS 環境変数を保護する protected 機構）。
    - export KEY=val 形式やクォート、インラインコメントへの堅牢な対応（_parse_env_line）。
    - 各種設定プロパティを提供（DB パス、PID/kill フラグ、閾値、env/log_level 判定、paper_trading 関連など）。
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収する set_process_priority を実装。
    - set_cpu_affinity を実装（指定コア数にプロセスをピン留め）。
    - アクセス権限不足や未対応環境での安全ハンドリング（警告ログ）を備える。
- ポートフォリオ構築
  - portfolio/portfolio_builder.py: 候補選定・重み計算（等金額・スコア加重）を追加。
    - select_candidates（score 降順、signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights（スコア全ゼロ時は等金額にフォールバック）。
  - portfolio/risk_adjustment.py: セクターキャップとレジーム乗数を追加。
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合に新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market レジームのラベルに応じた投下資金乗数（bull/neutral/bear、未知はフォールバックして警告）。
  - portfolio/position_sizing.py: ポジションサイズ決定ロジックを実装。
    - allocation_method による risk_based / equal / score のサポート。
    - 単元（lot_size）で丸め、per-stock / aggregate の上限、cost_buffer による保守的コスト見積り、available_cash によるスケーリングを実装。
    - スケーリング時の残差処理（fractional remainder に基づく lot 単位での再配分）。
- リサーチ機能（DuckDB ベース）
  - research/factor_research.py: ファクター計算（Momentum / Volatility / Value）を実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（最新財務レコードの検索を含む）。
  - research/feature_exploration.py: 将来リターン・IC・統計サマリ等を実装。
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（horizons の検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装（有効レコード < 3 は None）。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量算出を提供。
  - research/__init__.py: 主要 API をエクスポート（zscore_normalize を含む）。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成 CLI を追加。
    - CLI オプション: --from / --to / --db（PAPER_TRADING_SQLITE_PATH と併用可能）。
    - 指標: 稼働率、注文成功率（fill）、送信率（send）、リスク却下数、レイテンシ（avg/max/P95）。
    - 合格基準（閾値）を定め、PASS/FAIL 判定を出力。
    - 空データやテーブル欠損時にも安全にハンドリング（OperationalError を補足して N/A を表示）。
- AI / NLP（ニュースセンチメント、OpenAI 統合）
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込む処理を実装（機能豊富）。
    - タイムウィンドウ算出（JST→UTC の変換、ルックアヘッドバイアス対策として date.today() 非依存）。
    - 記事集約、1銘柄あたり文字数・記事数のトリミング、最大バッチサイズ、バッチごとの API 呼び出し。
    - エラー（429、ネットワーク、5xx、タイムアウト）に対する指数バックオフとリトライ。
    - レスポンス検証・スコアの ±1.0 クリップ・部分更新（成功銘柄のみ置換）によりフェイルセーフを設計。
    - OpenAI API キーの引数/環境変数（OPENAI_API_KEY）解決をサポート。
    - （注意）ソースは末尾で切れている箇所があり、実装の一部が未収録の可能性あり（実運用前に全体実装の確認推奨）。
- DB 初期化
  - monitoring/monitoring_db.py（参照されている初期化関数を利用）により監視テーブルの冪等初期化を run_* スクリプトで保証。
- DuckDB/SQLite の併用設計
  - DuckDB は時系列/調査的データ（prices_daily/raw_financials など）、SQLite はランタイム監視・トレードログ等の永続化に利用する設計をコード内で明示。

Changed
- （初期リリースのため該当なし）

Fixed
- デフォルト/バリデーションに関する堅牢化を複数箇所で実施
  - MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）に対するデフォルトフォールバックと警告ログ。
  - Settings.env / LOG_LEVEL / PAPER_FILL_MODE の値検証（不正な場合は ValueError を送出）。
  - .env パーサーのクォート/エスケープ/インラインコメント処理の改善（export プレフィックス対応含む）。
  - process_priority 系で権限不足や未実装機能時の警告ログでの安全ハンドリング。
  - position_sizing の価格未取得ケースでのスキップ処理・ログ出力。

Security
- 環境変数自動読み込みに関して OS 環境変数を保護する protected 機構を導入（.env.local の上書き時でも OS の既存キーは上書きされない）。

Notes / Known Issues
- ai/news_nlp.py は堅牢な設計（バッチ・リトライ・レスポンス検証）を持つが、ソース末尾が切れているため実装が未完の可能性があります。運用前にファイル全体の確認とテストを推奨します。
- position_sizing の価格欠損時（price == 0.0）の取り扱いに TODO コメントがあり、将来的に前日終値などのフォールバック価格を導入する余地があります。
- apply_sector_cap は "unknown" セクターを制限対象外とするため、マスタに欠損があると制限が緩くなる点に注意してください。
- .env 自動読み込みはプロジェクトルートが検出できない場合はスキップされます（環境に依存しない配布後の安全設計）。

今後の改善案（参考）
- news_nlp の完全実装およびユニットテスト追加。
- position_sizing の銘柄別 lot_size サポート、価格フォールバックロジックの追加。
- ExecutionEngine / Monitoring の統合テスト、リソース制限（メモリ/CPU）に関するモニタリング強化。
- DuckDB クエリのパフォーマンス計測とインデックス・マテリアライズ方式の検討。

----------------------------------------------------------------------------- 

必要ならば、実際のコミット履歴や日付を反映した詳細版（各ファイルごとの変更点やコードの抜粋を含む）も作成できます。どの程度詳細に記載するか教えてください。