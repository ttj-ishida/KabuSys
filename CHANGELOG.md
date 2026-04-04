CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」フォーマットに準拠しています。  
バージョンごとの主要な変更点を日本語で記載しています。コードベースから推測して作成したため、実際のコミット履歴と差異がある可能性があります。

Unreleased
----------

- （今後のリリースノートをここに記載します）

0.1.0 - 2026-04-04
------------------

初回リリース — 基本機能の実装と主要モジュールの追加。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - モジュール公開: data, strategy, execution, monitoring。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数からの自動ロード機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用）。
    - .env パーサは export 構文、クォート、エスケープ、インラインコメント等に対応。
    - .env と .env.local の読み込み優先度を実装（OS 環境変数は保護）。
  - Settings クラスを実装し、各種設定プロパティを提供（J-Quants トークン、kabu API 設定、LINE API、DB パス、監視設定、閾値、環境／ログレベル判定メソッド等）。
  - 設定値検証: KABUSYS_ENV / LOG_LEVEL の有効値チェックや必須値未設定時のエラー (_require)。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとにマクロ記事をまとめて OpenAI（gpt-4o-mini）に投げるバッチ処理を実装。
    - バッチサイズ、記事数・文字数上限、タイムウィンドウ（JST 基準 → UTC 変換）などの制御。
    - JSON Mode を利用したレスポンスバリデーションとスコア ±1.0 のクリップ。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで実装。
    - DuckDB 互換性のための安全な executemany 処理（空リスト回避）。
    - テストフック: _call_openai_api をパッチして差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定を実装。
    - prices_daily と raw_news を参照し、計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しは独立実装でモジュール結合を避け、API 失敗時はフェイルセーフ（macro_sentiment = 0.0）で継続。
    - リトライ・エラー処理、JSON パースやキー存在チェックの保護処理を実装。

- データプラットフォーム / ETL / カレンダー (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 保存（冪等）。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にカレンダー情報が無い場合の曜日ベースフォールバックを提供。最大探索日数制限で無限ループを防止。
    - 健全性チェック（将来日付過大時のスキップ）、バックフィルロジックを実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを定義（取得数／保存数／品質問題／エラーサマリなど）。
    - 差分更新・backfill・品質チェックの設計方針に基づく処理枠組みを実装（jquants_client, quality モジュールを呼び出す想定）。
    - DuckDB のテーブル存在確認や最大日付取得ユーティリティを実装。
  - etl モジュールは ETLResult を再エクスポート（kabusys.data.etl）。

- Research（kabusys.research）
  - ファクター計算群（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高変化率）、Value（PER, ROE）を DuckDB クエリベースで実装。
    - データ不足時は None を返す設計、結果は (date, code) ベースの dict リストで返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns: 複数ホライズンの取得を1 クエリで実装）。
    - IC（Information Coefficient、Spearman の ρ）計算（calc_ic）。
    - ランキング関数（rank）とファクター統計サマリー（factor_summary）を実装。
  - リサーチ用 API を package level で再エクスポート（zscore_normalize 等）。

Changed
- （初回リリースのため該当なし）

Fixed
- フェイルセーフと堅牢性の実装（注記）
  - OpenAI API 呼び出し時の各種障害に対するリトライとフォールバック（macro_sentiment=0.0 やスキップ）を実装し、API 依存部が原因で処理全体が停止しないように設計。
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。ROLLBACK に失敗した場合はログ出力して上位へ例外伝播。
  - DuckDB の executemany の空リスト制約を考慮した実装で互換性を確保。

Security
- OpenAI API キーの必須チェックを導入（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
- 環境変数読み込み時に既存 OS 環境を protected として上書きから保護する仕組みを導入。

Notes / Implementation details
- LLM 結果は JSON Mode 想定だが、実運用で前後に余計なテキストが混入するケースを想定してパース復元ロジックを持つ（最外の {} を抜き出して再パース）。
- 時刻窓は JST 基準で定義し、DuckDB 比較のため UTC naive datetime に変換して使用（ルックアヘッドバイアス防止の設計方針）。
- ほとんどの処理関数は date / datetime を引数で受け取り内部で date.today()/datetime.today() を参照しない設計（バックテストでのルックアヘッド防止）。
- テスト容易性を考慮し、OpenAI 呼び出しを内部関数として実装し unittest.mock.patch による差し替えが可能。

Compatibility / Breaking changes
- 初回リリースにつき後方互換性の変更点は無し。

―――

補足:
- 本 CHANGELOG は与えられたコードベースから機能と設計意図を推測して作成しています。実際のコミットメッセージや履歴に基づく正確な変更履歴が必要な場合は、Git の履歴やリリースノート元データを参照してください。