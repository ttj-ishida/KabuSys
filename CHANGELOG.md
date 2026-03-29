# Changelog

すべての変更は「Keep a Changelog」形式に従い記述しています。  
フォーマットやカテゴリの意味については https://keepachangelog.com/ja/ を参照してください。

注: この CHANGELOG はリポジトリに含まれるソースコードから推測して作成しています（実装内容・設計方針の要約を含む）。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース（ベース実装）。主な追加内容・設計方針は以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化。公開モジュールとして data, strategy, execution, monitoring をエクスポート。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml に基づく）。
  - 行パーサーは export 形式、クォート（シングル/ダブル）のエスケープ、インラインコメント処理に対応。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開（settings インスタンス）。J-Quants / kabu API / Slack / DB パス / 実行環境（KABUSYS_ENV）や LOG_LEVEL の検証ロジックを含む。
  - デフォルト値（例: KABUS_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）と必須環境変数の明示（未設定時は ValueError を送出）。

- データ関連（src/kabusys/data/*.py）
  - カレンダー管理（calendar_management.py）
    - market_calendar を用いた営業日判定機能（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先・未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル、健全性チェック（将来日付の閾値）を実装。
    - 最大探索日数、先読み日数、バックフィル日数などの定数を定義。
  - ETL パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集約）。
    - 差分取得・バックフィル、品質チェックの流れを想定したユーティリティ（テーブル存在確認、最大日付取得、取引日調整等）。
    - jquants_client / quality モジュールと連携する設計（save_* の呼び出しを想定）。

- 研究（research）モジュール（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。NULL/データ不足時の扱いに注意。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。報告日以前の最新財務データを使用。
    - 全関数は DuckDB 接続を受け取り SQL ベースで実装、外部 API にアクセスしない設計。
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算。horizons の検証を実装。
    - calc_ic: スピアマンランク相関（IC）計算。必要レコードが少ない場合は None を返す。
    - rank: 同順位は平均ランクにするランク付け機能。浮動小数点丸め対策として round(v, 12) を使用。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出する統計サマリー機能。
  - research パッケージは zscore_normalize を data.stats から再利用。

- AI（src/kabusys/ai/*）
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols を元に、前日 15:00 JST ～ 当日 08:30 JST 相当の時間ウィンドウの記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でバッチ評価。
    - バッチサイズ、最大記事数、文字トリム、JSON モードでのレスポンスバリデーションを実装（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK 等）。
    - リトライ戦略（429・ネットワーク断・タイムアウト・5xx をエクスポネンシャルバックオフでリトライ）、失敗時はそのチャンクをスキップして継続（フェイルセーフ）。
    - レスポンス検証処理（_validate_and_extract）: JSON 抽出、results リスト検証、スコアの数値チェックと ±1.0 でクリップ。
    - テスト容易性: _call_openai_api を patch で差し替え可能に設計。
    - score_news 関数は取得したスコアを ai_scores テーブルへ冪等的に書き換える（DELETE → INSERT、部分失敗時に他銘柄の既存データを保護）。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出（マクロキーワードリスト）→ OpenAI（gpt-4o-mini）で macro_sentiment を算出→ 合成スコアの計算（クリップ）→ market_regime テーブルへ冪等書き込み。
    - API 呼び出しのリトライ/フォールバック方針（API 失敗時は macro_sentiment=0.0）とテスト用差し替えポイントを実装。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、DB クエリは target_date 未満のデータのみを使用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （該当なし）

---

補足: 実装上の重要な設計・安全性・運用上のポイント（リリース注記）
- ルックアヘッドバイアス防止: AI スコア算出やレジーム判定、各種指標計算で date.now を直接参照せず、外部から渡した target_date を基準にウィンドウを計算する設計が徹底されています。
- DB 書き込みは冪等化を意識（DELETE→INSERT、ON CONFLICT 想定）しており、部分失敗時に既存データを不必要に消さないよう配慮されています。
- OpenAI との通信は JSON mode を利用し、パース失敗や API エラーに対してリトライ／フォールバック（score=0.0 等）することでパイプラインの堅牢性を高めています。
- テストしやすさ: OpenAI 呼び出し関数に差し替えポイントを用意しており、ユニットテストで外部依存をモック可能です。
- DuckDB を前提に SQL を組み立てており、空の executemany を回避するなど互換性対策が取られています。

Contributing / 著者情報等はリポジトリに含まれるドキュメント（README / Developer Guide 等）を参照してください。