# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-27
初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を実装・公開。

### Added
- パッケージ基本情報
  - パッケージ名 / 説明を追加（src/kabusys/__init__.py）。
  - バージョンを "0.1.0" に設定。

- 環境変数・設定管理
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml 基準）。
  - .env/.env.local の優先順位および OS 環境変数保護（protected）に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 行パーサ実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理などをサポート）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム設定等の値をプロパティ経由で取得。
  - KABUSYS_ENV と LOG_LEVEL の値検証（有効値のチェック）を追加。
  - デフォルトのデータベースパス（DuckDB / SQLite）を設定。

- AI（ニュース NLP / レジーム判定）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - バッチサイズ、記事数上限、文字数トリム等のトークン肥大化対策を実装。
    - JSON Mode を用いた厳密な出力期待とレスポンス検証ロジック（パース復元、results 構造の検証、コード照合、数値検証）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数的バックオフとリトライ処理。
    - スコアは ±1.0 にクリップ。成功時は ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - ユニットテスト容易化のため OpenAI 呼び出しを差し替え可能に設計（_call_openai_api を patch 可能）。
    - ルックアヘッドバイアスを避けるため内部で datetime.today() 等を参照しない設計（target_date ベース）。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）で macro_sentiment を算出。
    - API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出し、リトライ（429/タイムアウト/5xx）処理、JSON パースの頑健さを備える。

- Data（ETL / カレンダー / ETL 結果型）
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得・保存・品質チェックを想定した ETLResult データクラスを導入（取得数 / 保存数 / 品質問題 / エラー等を記録）。
    - テーブル最終日取得ユーティリティ、DuckDB 互換考慮の実装（空テーブル・テーブル未作成時の挙動）。
    - 設計上の方針（バックフィル、差分単位、品質チェックは収集して呼び出し元で判断）を反映。
  - calendar_management（src/kabusys/data/calendar_management.py）
    - JPX カレンダー（market_calendar テーブル）管理：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等のユーティリティを実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・保存（バックフィルや健全性チェックを含む）。
    - market_calendar 未取得時のフォールバックや NULL データに対する警告ログを備える。

- Research（ファクター計算・特徴量探索）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum / Volatility / Value / Liquidity 系ファクターを DuckDB 上の価格・財務データから計算する関数群を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
      - calc_value: PER（EPS が 0/欠損時は None）、ROE（最新財務データから）を計算。
    - SQL ウィンドウ関数を多用し、DuckDB 上で効率的に実行。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank: 同順位は平均ランクにするランク関数を実装（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出。
    - いずれも外部ライブラリを使わず標準ライブラリと DuckDB のみで実装。

- モジュールのエクスポート整理
  - research パッケージの __init__ で主要関数を再エクスポート。
  - data.etl で ETLResult を再エクスポート。
  - ai パッケージで score_news を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

---

注記・設計上の重要ポイント
- ルックアヘッドバイアス防止: news_nlp / regime_detector / research モジュールは内部で datetime.today() / date.today() を参照せず、すべて target_date ベースで処理する設計。
- フェイルセーフ: OpenAI API や外部 API の一時的失敗時は例外を投げずにフォールバック（スコア 0.0 や処理スキップ）して処理継続する方針。
- DuckDB 互換性考慮: executemany の空リスト制約や日付型の取り扱いなど、実行環境差異を吸収する実装を行っている。
- テスト容易性: OpenAI 呼び出し箇所は差し替え可能（patch）にしてユニットテストを行いやすくしている。

README やドキュメントに実運用上の注意（OpenAI API キーの設定、.env の構成、データベース初期化手順など）を追記することを推奨します。