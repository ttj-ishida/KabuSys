CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。
日付はリポジトリ内のコード（ドキュメント・コメント等）から推測できる最近の状態を用いています。

0.1.0 - 2026-04-17
-----------------

Added
- 基本バージョン情報を追加（kabusys.__version__ = "0.1.0"）。
- 実行系
  - run_execution.py: ExecutionEngine の起動スクリプトを追加。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - paper_trading 環境では専用の SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と完全分離。
    - OrderRepository、OrderManager、RiskManager、Reconciler を組み合わせて ExecutionEngine を構築・起動。
    - 停止フラグ（data/stop_requested.flag）検出により安全に停止可能。
    - 実行 PID を data/execution.pid に記録する仕組み（pid_file を渡す）。
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関係なく本番用 sqlite_path を使用して監視データを記録。
    - 停止フラグ（data/stop_requested.flag）でループを抜ける。
- 設定/環境読み込み
  - config.py:
    - .env / .env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml を基準に検出）。
    - export 形式・クォート・インラインコメント等に対応した堅牢な .env パーサを実装。
    - プロテクトオプションで OS 環境変数の上書きを制御。
    - Settings クラスを追加。各種設定（DB パス、API トークン、監視しきい値、環境判定 helper 等）をプロパティとして提供。
    - PAPER_FILL_MODE のバリデーション実装（instant/partial/never/reject）。
- ユーティリティ
  - utils/process_priority.py:
    - Windows / POSIX（Linux, Darwin, FreeBSD）に対応したプロセス優先度設定を実装（psutil ベース）。
    - CPU affinity を設定する set_cpu_affinity を追加（指定が None の場合は変更しない）。
    - 権限不足や未対応環境では警告を出して安全にフォールバック。
- ポートフォリオ建設
  - portfolio/portfolio_builder.py:
    - シグナル選定(select_candidates)、等配分(calc_equal_weights)、スコア加重(calc_score_weights)を実装。
    - スコアが全て 0 の場合は等配分にフォールバックして警告を出す。
  - portfolio/risk_adjustment.py:
    - セクター集中制限の適用関数 apply_sector_cap を実装。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマップ、未知レジームはフォールバック）。
  - portfolio/position_sizing.py:
    - allocation_method に基づく株数決定 calc_position_sizes を実装（risk_based / equal / score）。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、利用可能現金による aggregate cap、cost_buffer を考慮したスケールダウンを実装。
    - price が欠損・ゼロの場合のスキップやデバッグログを考慮。
- リサーチ（ファクター計算・解析）
  - research/factor_research.py:
    - モメンタム（1M/3M/6M・MA200乖離）、ボラティリティ（ATR20・相対ATR・出来高指標）、バリュー（PER・ROE）計算を DuckDB SQL を用いて実装。
    - データ不足に対する None ハンドリング、ウィンドウ計算などを考慮。
  - research/feature_exploration.py:
    - 将来リターン calc_forward_returns、スピアマンを用いた IC 計算 calc_ic、ファクター統計サマリ factor_summary、ランク変換ユーティリティ rank を実装。
    - pandas 等への依存を置かず標準ライブラリのみで実装。
  - research/__init__.py: 主要な関数群をパッケージ公開（zscore_normalize を kabusys.data.stats から再エクスポート）。
- AI / NLP
  - ai/news_nlp.py:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む処理を実装。
    - バッチサイズ、トークン肥大化対策（記事数・文字数上限）、最大リトライ、指数バックオフ、レスポンスバリデーション、スコアのクリッピング（±1.0）等を設計に盛り込んでいる。
    - target_date に基づいたニュースウィンドウ計算 calc_news_window を提供（JST ベースの UTC 変換を実装）。
- ツール
  - tools/paper_verification_report.py:
    - ペーパートレーディング用検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs テーブルを参照して稼働率、注文成功率、送信率、レイテンシ（平均・P95）等を集計して標準出力に整形して表示。
    - 合格/不合格の閾値とパス/フェイル判定（稼働率、fill/send rate、P95 latency）を実装。
    - コマンドライン引数 --from/--to/--db に対応。
- DB/監視
  - monitoring/monitoring_db.py の初期化を起動スクリプト側で呼び出すことで監視テーブルの存在を保証（冪等）。

Changed
- 全体
  - ログ設定や例外処理において起動スクリプトで INFO レベルの basicConfig を設定する方針を採用。
  - プロセス優先度は起動直後に「高 (high)」へ設定する処理を各起動スクリプトで実行するように統一。

Fixed
- 環境変数読み込み
  - .env のパースを強化し、export 表記・クォート・エスケープ・インラインコメントの取り扱いで従来の単純パーサに起因する問題を低減。

Notes / Known limitations
- news_nlp.py は API 呼び出し回りや DB 書き込みのフル実装が設計コメント中に詳述されているが、コード末尾が大きな関数内で途切れているため（提供されたスニペットの都合）、実行に際して追加実装・テストが必要な箇所が存在する可能性があります。
- position_sizing の price 欠損時の振る舞いに TODO コメントがあり、前日終値等によるフォールバックは将来的に検討予定。
- 一部の機能（ExecutionEngine や SystemMonitor、BrokerClientFactory 等）は起動スクリプトから利用されているが、その内部実装（別モジュール）がこの差分に含まれていないため、統合テストが必要。

Security
- 環境変数読み込みで OS 環境を保護する protected オプションを導入し、CI/本番環境の環境変数が意図せず上書きされるリスクを軽減。

---- 

今後の予定（推定）
- news_nlp の完全実装とユニット / 結合テスト整備。
- ExecutionEngine / リスクマネージャーのパラメータ調整とログ強化。
- position_sizing 周りの lot_size 銘柄別対応や価格フォールバック実装。
- DuckDB を利用したリサーチ機能のパフォーマンス最適化（インデックスや分割ロード等）。

以上。必要であれば、この CHANGELOG を英語版に翻訳する、あるいは各変更項目をさらにファイル単位で詳細化（コミットハッシュや担当者、チケット番号の紐付け）することも可能です。どの形式がよいか指示ください。