CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。
リリース日付はコードベースから推測した日付を記載しています。

フォーマットの概要:
- Added: 新機能
- Changed: 既存機能の互換性のある変更
- Fixed: バグ修正（互換性あり）
- Deprecated / Removed / Security: 必要に応じて記載

Unreleased
----------

- （現在のブランチに未リリースの変更はありません）

0.1.0 - 2026-04-01
------------------

Added
- パッケージの初回リリース: kabusys 0.1.0
  - 概要: 日本株自動売買システムの基盤モジュール群を提供。
  - 主な設計方針: DuckDB をローカル分析ストアとして使用し、外部実売買 API 呼び出しは明確に分離。ルックアヘッドバイアスを避けるため datetime.today()/date.today() を直接参照しない設計、API失敗時はフェイルセーフで継続する方針を採用。

- 環境設定:
  - kabusys.config.Settings を導入し、.env/.env.local および環境変数から設定を読み込み可能。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を順に読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - .env のパース処理は export プレフィックス、シングル/ダブルクォート中のバックスラッシュエスケープ、インラインコメント処理などに対応。
    - OS 環境変数（既存キー）は保護され、.env.local を使えば上書きが可能。
  - 設定プロパティ（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DBパス（DUCKDB_PATH, SQLITE_PATH）、監視設定（PID_FILE_PATH, CPU/MEM/DISK閾値）
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL（DEBUG/INFO/...）のバリデーションおよび is_live/is_paper/is_dev の補助プロパティ

- AI（自然言語処理）:
  - kabusys.ai.news_nlp.score_news:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を JSON mode で呼び出して銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたりの記事数・文字数制限（トリム）を実装し、トークン膨張を対策。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実施。その他のエラーは個別にスキップして処理継続（フェイルセーフ）。
    - レスポンスのバリデーション機能を実装（JSON 抽出、"results" 構造チェック、コード整合性、数値の有効性、スコアのクリップ）。
    - 成果は ai_scores テーブルへ冪等的に置換（該当コードのみ DELETE → INSERT）して部分失敗の影響を限定。
    - calc_news_window ユーティリティを提供（JSTベースのウィンドウ計算：前日15:00〜当日08:30相当のUTCレンジ）。
  - kabusys.ai.regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベース（設定済みキーワードリスト）でタイトルを収集。記事が無い場合はLLM呼び出しをスキップし macro_sentiment=0.0。
    - OpenAI 呼び出しは専用の wrapper を使用。リトライ・エラー処理・JSON パース不正時は 0.0 にフォールバックして継続。
    - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB書き込み失敗時は ROLLBACK を試み、例外を上位に伝播。

- Data（データ基盤）:
  - kabusys.data.pipeline.ETLResult:
    - ETL 実行結果を保持する dataclass を提供（取得件数、保存件数、品質チェック結果、エラーリストなど）。
    - to_dict により品質問題を辞書化して監査ログ等に利用可能。
  - kabusys.data.pipeline:
    - ETL パイプライン設計（差分更新、バックフィル、品質チェックの統合）に沿ったユーティリティを実装（jquants_client と quality モジュールを組み合わせる想定）。
    - 差分取得のデフォルトは営業日単位、バックフィル日数の指定により後出し修正を吸収。
    - 品質チェックは致命的エラーを発見しても ETL 自体は継続し、呼び出し元が判断できるように設計。
  - kabusys.data.calendar_management:
    - market_calendar を扱うユーティリティ（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
    - DB にカレンダーがない場合は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィルや健全性チェック（将来日付の異常検出）を含む。
    - 最大探索日数や見通し日数などの安全パラメータを設定して無限ループや過大取得を防止。

- Research（因子・解析）:
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR比率、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播やカウントを厳密に扱う。
    - calc_value: raw_financials から最新の財務指標（EPS, ROE）を取得し PER/ROE を計算（EPSゼロや欠損時は None）。
    - 全関数が DuckDB 上の SQL と最小限の Python ロジックで完結する設計。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを一括クエリで取得。ホライズン入力のバリデーションあり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが少ない場合は None を返す。
    - rank: 同順位は平均順位にするランク変換を実装（丸めで ties 検出の頑健性を確保）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリーを提供。
  - 研究モジュールは外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

- その他:
  - パッケージ __init__ にバージョン (0.1.0) と公開サブモジュールを設定。
  - 実装全体でログ出力（logger）を適切に配置し、重要なフォールバックやパースエラー、APIエラーを WARN/INFO/DEBUG レベルで記録。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated / Removed
- 初回リリースのため該当なし。

Security
- 環境変数の自動ロードで OS 環境変数を上書きしない保護ロジックを実装（.env.local による明示的上書きを除く）。
- OpenAI API キーや各種トークンは環境変数経由で取得し、未設定時は明示的に ValueError を発生させて誤動作を防止。

補足（設計上の注意）
- 多くの処理は「フェイルセーフ（API失敗時に処理続行・無害なデフォルトを使用）」を優先しており、完全性より可用性を重視した設計になっています。運用上はログ監視や品質チェック結果の確認が推奨されます。
- DuckDB のバージョン差（executemany の空リスト取り扱い等）を考慮した実装上のガードが多数存在します。
- OpenAI 呼び出しは JSON mode を前提に厳密なレスポンス検証を行っていますが、実際の運用ではモデル出力の揺らぎへの追加監視が推奨されます。

今後の予定（例）
- モデル運用に関するより強固な監視とレートリミット回避の改善。
- ai_scores / market_regime などの結果を参照するダッシュボードや監視アラート統合。
- ETL の並列化・パフォーマンス最適化、テストカバレッジの拡充。

---