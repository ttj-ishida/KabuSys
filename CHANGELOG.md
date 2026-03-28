# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」方式に準拠しています。

フォーマット: [バージョン] - リリース日
- Added: 新機能
- Changed: 変更点（後方互換性があるもの）
- Fixed: 修正・改善
- Security: セキュリティ関連

## [Unreleased]

## [0.1.0] - 2026-03-28

### Added
- パッケージ初期リリース。日本株自動売買プラットフォームの基礎機能群を実装。
- パッケージメタ情報
  - パッケージバージョン: 0.1.0
  - 主要モジュールのエクスポート: data, strategy, execution, monitoring
- 環境変数 / 設定管理 (kabusys.config)
  - .env ファイル自動読み込み（プロジェクトルートの検出: .git または pyproject.toml）
  - .env のパース強化: コメント、export KEY=val 形式、シングル/ダブルクォート内のエスケープ処理等に対応
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須設定チェック用ヘルパー _require と Settings クラスを提供
  - 設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH（default data/kabusys.duckdb）, SQLITE_PATH（default data/monitoring.db）
  - 環境値検証: KABUSYS_ENV（development / paper_trading / live のみ許容）および LOG_LEVEL の妥当性チェック
- AI（NLP）モジュール (kabusys.ai)
  - ニュースセンチメント集計 (news_nlp.score_news)
    - 前日 15:00 JST ～ 当日 08:30 JST のニュースウィンドウ計算（UTC naive datetime を返す calc_news_window）
    - 銘柄ごとに記事を集約、記事数・文字数トリム、最大 20 銘柄ずつバッチで OpenAI（gpt-4o-mini）へ送信
    - JSON Mode を用いた出力の厳密検証（results 配列・コード一致・数値チェック）
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。フォールバックで失敗した銘柄のみスキップ（他銘柄の既存スコア保護）
    - テスト容易性のため _call_openai_api を patch 可能に設計
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定
    - マクロキーワードで raw_news をフィルタし、最大件数で LLM 評価
    - LLM 呼び出し失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）
    - レジーム結果を market_regime テーブルへトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等書き込み
    - LLM 関連: gpt-4o-mini、JSON 出力、リトライ（429/ネットワーク/タイムアウト/5xx）
- Research（kabusys.research）
  - ファクター計算群を実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - calc_value: PER / ROE（raw_financials の最新レコードを使用）
  - 特徴量探索ユーティリティ
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を使用）
    - calc_ic: スピアマンランク相関による IC 計算（3 件未満で None）
    - rank: 同順位は平均ランクを返す実装（丸め処理で ties の安定化）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
  - zscore_normalize を data.stats から再エクスポート
- Data プラットフォーム（kabusys.data）
  - カレンダー管理 (calendar_management)
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 未取得時は曜日ベースのフォールバック（土日休）で一貫した結果を返す設計
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新、バックフィル・健全性チェックを実装
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（ETL 実行結果・品質問題・エラーの収集）
    - 差分取得・バックフィル・品質チェックの方針を実装（jquants_client 経由で保存）
    - DuckDB の互換性考慮（executemany の空リスト問題回避など）
  - jquants_client / quality との連携を想定した設計（API 呼び出し部分は外部モジュールに委譲）
- テスト・運用上の配慮
  - ルックアヘッドバイアス防止: 各モジュールで datetime.today()/date.today() を直接参照しない実装方針（ターゲット日を引数で与える設計）
  - OpenAI 呼び出しはモジュール毎に独立した private wrapper を持ち、テスト時に差し替え可能
  - DuckDB との相互運用性を考慮した実装（型変換ユーティリティ・行数不足時の挙動を明示）
- ドキュメント的な docstring を充実させ、設計方針・処理フロー・フォールバック動作を明記

### Changed
- 初回リリースのため変更履歴なし

### Fixed / Improvements
- 各所でのフェイルセーフ実装:
  - news_nlp / regime_detector: LLM の一時的エラー・5xx をリトライし、最終的に失敗した場合は部分スキップ（システム全体の停止を回避）
  - 設定読み込み: .env 読み込み失敗時は警告を出して継続（テストや CI での扱いを容易化）
  - DuckDB 書き込み: 部分失敗時に他データを消さないようにコード別で DELETE→INSERT を採用
- 入力検証の強化:
  - Settings.env および LOG_LEVEL の妥当性チェックで誤設定を早期に検出

### Security
- 環境変数の保護機能:
  - .env ファイル読み込み時に既存 OS 環境変数を protected として上書き防止（override 引数で制御可能）
  - 自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト環境向け）

注記:
- OpenAI API キー（OPENAI_API_KEY）を必要とする機能（news_nlp.score_news, regime_detector.score_regime）はキー未設定時に ValueError を投げます（呼び出し側でのキー注入が可能）。
- 本リリースは「ライブラリ基盤」としての提供であり、実際の発注・実行（execution/strategy/monitoring）の詳細実装は今後のリリースで拡張予定です。