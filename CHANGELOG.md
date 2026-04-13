Keep a Changelog
=================

すべての注目すべき変更をこのファイルで管理します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 未リリースの変更は "Unreleased" に記載します。
- 各リリースには日付を付与します（YYYY-MM-DD）。

Unreleased
----------

なし

[0.1.0] - 2026-04-13
-------------------

初回リリース — 基本機能一式を実装。

Added
- パッケージ基本情報
  - kabusys パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
- 設定管理
  - 環境変数 / .env 自動読み込み機能を実装（.env/.env.local、OS環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサーを実装し、クォートやエスケープ、コメントや "export KEY=val" 形式に対応。
  - Settings クラスを提供し、各種構成値をプロパティ経由で取得可能に（DB パス、API トークン、監視閾値、環境種別など）。
  - PAPER_FILL_MODE 等の値検証（有効値チェック）とデフォルト値を実装。
- 実行用エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。プロセス優先度設定、SQLite/DuckDB 接続、BrokerClientFactory によるブローカー切替（paper_trading 時は専用 DB に記録）を実装。ExecutionEngine のセッション実行フローを起動。
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する実装。
- 監視関連
  - monitoring 側初期化ユーティリティ（init_monitoring_db）を組み込み、冪等にテーブルを作成して監視データ収集を保証。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。期間フィルタ (--from/--to/--db) に対応し、稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数などを集計・判定（PASS/FAIL）して標準出力へ出力。
  - P95 算出ユーティリティを実装（_p95）。
- ポートフォリオ構築（純粋関数群）
  - portfolio モジュールを追加:
    - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を提供。スコアが全て 0 の場合は等金額にフォールバック。
    - risk_adjustment: セクター集中制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を実装。未知のレジーム時はフォールバック処理を行う。
    - position_sizing: 株数決定ロジック（calc_position_sizes）を実装。risk_based / equal / score の配分手法に対応、単元株（lot_size）丸め、aggregate cap（利用可能現金でスケールダウン）、cost_buffer を考慮した安全弁を実装。
- 研究・ファクター計算
  - research モジュールを追加:
    - factor_research: Momentum（1M/3M/6M, MA200 乖離）、Volatility（ATR20, 相対ATR, 20日平均売買代金, 出来高比率）、Value（PER, ROE）を DuckDB を使って計算する関数を実装。prices_daily / raw_financials テーブル参照。
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（スピアマン順位相関）計算（calc_ic）、rank / factor_summary（基本統計）を実装。外部ライブラリに依存せず純 Python 実装。
  - research パッケージの公開 API を __all__ に設定。
- ニュース NLP（AI）モジュール
  - ai/news_nlp.py を追加:
    - raw_news を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込むフローを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に相当する UTC 範囲）を実装（calc_news_window）。
    - API 再試行ロジック（429 / ネットワーク / 5xx に対する指数バックオフ）やバリデーション、スコアクリッピング（±1.0）を実装。
    - OpenAI API キー未設定時の明確な例外（ValueError）を用意。
    - バッチサイズ・最大記事数・最大文字数などトークン肥大化対策を導入。
- ユーティリティ
  - utils/process_priority.py: プラットフォーム差分を吸収するプロセス優先度設定ユーティリティを実装（Windows / POSIX 対応）。CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。アクセス権や未対応環境では警告を出して安全にスキップ。
- DB ドライバー
  - sqlite3 / duckdb を組み合わせて使用する設計。Execution / Monitoring / Research / AI で適切に接続を行い、終了時にクローズする実装。
- その他
  - ロギングを各スクリプトで基本設定（INFO）して情報を出力。
  - 各モジュールで入出力の検証や欠損データ（None）に対するフォールトトレランスを実装（例: factor 関数、position sizing の価格欠損時のスキップなど）。

Changed
- （初回リリースにつきなし）

Fixed
- 環境変数パーサーの堅牢化
  - クォート内部のバックスラッシュエスケープに対応し、インラインコメントを適切に無視する実装を導入。
  - コメント判定の条件（'#' の直前がスペース/タブの場合のみコメント）を明記して実装。
- 設定値の妥当性チェック
  - MONITOR_POLL_INTERVAL の不正値（0 や負値、非数）を検出してデフォルトへフォールバックし、警告ログを出す処理を追加。
  - PAPER_FILL_MODE や LOG_LEVEL、KABUSYS_ENV の不正値に対する明示的な例外処理を実装。
- DB 初期化の冪等性
  - init_monitoring_db を起動時に呼び出し、監視テーブルが存在しない場合のみ作成することで複数起動時やテスト実行での安全性を確保。
- レポート関連の堅牢化
  - paper_verification_report の各クエリで sqlite3.OperationalError を捕捉し、テーブル欠如時でもスクリプトが壊れず N/A 相当でレポートを生成するようにした。
  - レイテンシ集計で NULL 値を除外し P95 を正しく計算する処理を実装。

Notes / Implementation details
- design notes（コード内コメント）で将来の拡張（銘柄別 lot_size、前日終値フォールバック、部分的なスケール戦略など）や既知の制約（DuckDB の executemany の制約、AI API の再試行ポリシー等）が明記されています。
- 多くの関数は「DB 参照なし」かつ「純粋関数」として実装されており、単体テストが容易になるよう設計されています。

未解決 / TODO（コード内コメントより抜粋）
- position_sizing: price が欠損した場合のフォールバック価格（前日終値や取得原価など）を導入する検討。
- 将来的に銘柄毎の lot_size を stocks マスタに持たせる設計への拡張。
- ai/news_nlp の部分的失敗時の永続化戦略やレート制限最適化の細部改善。

ライセンス
- （このリポジトリのライセンス表記が別途無い場合、適切なライセンスを付与することを推奨します）

----------------------------------------
補足:
- 本 CHANGELOG は現行のソースコードから推測して作成しています。実際のコミット履歴や開発ノートがあればそれを元に詳細な変更履歴を作成してください。