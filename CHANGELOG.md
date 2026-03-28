# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- 今後の変更追記領域。

## [0.1.0] - 2026-03-28
初回リリース — 日本株自動売買プラットフォームのコアライブラリを実装。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。__version__ = "0.1.0" を設定。
  - パッケージ公開インターフェースに data, strategy, execution, monitoring を想定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートの自動検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - .env パーサ実装（_parse_env_line）:
    - export KEY=val 形式対応、シングル/ダブルクォート対応、バックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォートの有無でのルール差異）を実装。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須値を _require で検証。
    - KABUSYS_ENV（development / paper_trading / live） と LOG_LEVEL を検証。
    - DuckDB / SQLite のデフォルトパス設定（Path オブジェクトを返す）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ基盤 (kabusys.data)
  - calendar_management モジュール:
    - market_calendar を用いた営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）。
    - DB 未取得時の曜日ベースフォールバック、DB 値優先の一貫した振る舞い。
    - カレンダー夜間バッチ calendar_update_job: J-Quants から差分取得し冪等保存、バックフィル・健全性チェックを実装。
  - pipeline / etl モジュール:
    - ETLResult データクラスを定義（取得・保存件数、品質チェック結果、エラー一覧を保持）。
    - ETL の差分取得方針、バックフィル、品質チェック統合の設計を反映。
    - data.etl から ETLResult を再エクスポート。

- AI / NLP (kabusys.ai)
  - news_nlp モジュール:
    - score_news(conn, target_date, api_key=None)：raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存。
    - タイムウィンドウ計算（calc_news_window）：前日15:00 JST ～ 当日08:30 JST（UTC に変換）を正確に算出。
    - バッチ処理（最大 20 銘柄/コール）、記事トリム（最大記事数/最大文字数）、レスポンスバリデーション、スコアの ±1.0 クリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフ・リトライ実装。失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
    - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
  - regime_detector モジュール:
    - score_regime(conn, target_date, api_key=None)：ETF 1321 の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成して market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し、レスポンス JSON パース、スコアクリップ、閾値に基づくラベル（bull/neutral/bear）付与。
    - API エラー時は macro_sentiment=0.0 にフォールバックする安全設計。内部での OpenAI 呼び出しは news_nlp とは独立した実装でモジュール結合を避ける。
    - テスト時の差し替えフックやリトライ/ログの整備。

- リサーチ/ファクター解析 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum：1M/3M/6M リターン、200日移動平均乖離を計算（prices_daily を SQL で集計）。データ不足の取り扱い（None）を明示。
    - calc_volatility：20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value：raw_financials と prices_daily を結合し PER / ROE を算出（EPS が無効な場合は None）。
    - 全て DuckDB 上で SQL を用いて実装。外部 API・取引系 API にはアクセスしない。
  - feature_exploration モジュール:
    - calc_forward_returns：指定日の終値から各ホライズン（デフォルト 1,5,21）までの将来リターンを LEAD によって計算。
    - calc_ic：Spearman（ランク）相関による IC 計算。必要レコード数が不足する場合は None を返す。
    - rank：同順位は平均ランクで扱う安定化実装（round による丸めで ties の検出を安定化）。
    - factor_summary：count/mean/std/min/max/median を計算する統計サマリ機能。
  - research パッケージの __all__ に主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初回リリースなので変更履歴なし）

### Fixed
- （初回リリースなので修正履歴なし）

### Security
- AI 機能（score_news / score_regime）は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）を必須にし、未設定時は ValueError を投げることで誤った呼び出しを防止。

### Notes / Implementation details
- ルックアヘッドバイアス対策:
  - AI スコアリングやレジーム判定は内部で datetime.today() / date.today() を使用せず、呼び出し側が target_date を明示する形にしている。
  - DB クエリでは target_date より前のデータのみを参照する等、データリークを防ぐ実装。
- DB 書き込みは冪等性を意識（BEGIN / DELETE / INSERT / COMMIT、失敗時に ROLLBACK）しているため、部分再実行が安全に行える。
- DuckDB の互換性（executemany の空リスト不可など）を考慮した実装を行っている。
- 可能な限り外部依存を避け、標準ライブラリと DuckDB の SQL を中心に実装。
- テスト支援:
  - OpenAI 呼び出し箇所は内部関数（_call_openai_api）をパッチ可能に実装しており単体テストが容易。
  - 環境変数自動読み込みは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト環境の汚染を防止。

---

今後のリリースでは、strategy / execution / monitoring の具体実装、テストカバレッジやドキュメントの追加、運用向け改善（監視・メトリクス・リトライ戦略の調整）などを予定しています。