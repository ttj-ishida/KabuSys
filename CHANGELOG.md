# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはコードベースから推測して生成した初期リリース向けの変更履歴です。

今後の変更は Unreleased セクションに追加してください。

## [Unreleased]
- （次回リリースに向けた変更をここに記載）

---

## [0.1.0] - 2026-03-28

初回公開リリース。日本株自動売買システム "KabuSys" の基盤機能を実装しました。主な追加点・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージルート: kabusys.__init__ を追加。バージョン情報 __version__ = "0.1.0" と公開サブパッケージ（data, research, ai, ...）を定義。

- 設定・環境変数管理（kabusys.config）
  - Settings クラスを追加し、アプリケーション設定を環境変数から取得する統一インターフェースを提供。
  - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env のパースロジックを実装（export 形式、クォート、エスケープ、インラインコメントの扱いを含む）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数保護機能（protected set）により OS 環境変数の上書きを防止。
  - 必須環境変数取得時の明確なエラー（_require による ValueError）。
  - 設定項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）を実装。

- データ（ETL / パイプライン）
  - ETLResult データクラスを追加（kabusys.data.pipeline）。ETL の実行結果・品質問題・エラー情報を構造化して保持可能。
  - DuckDB を用いた ETL ヘルパーを実装（最終取得日の取得、テーブル存在確認等）。
  - data.etl で ETLResult を再エクスポート。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーの夜間更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・冪等保存を行う。
  - 営業日判定 API を実装:
    - is_trading_day(conn, d)
    - next_trading_day(conn, d)
    - prev_trading_day(conn, d)
    - get_trading_days(conn, start, end)
    - is_sq_day(conn, d)
  - DB に登録がない場合は曜日ベース（週末除外）でフォールバックする一貫したロジックを提供。
  - 安全対策: 探索の最大日数制限 (_MAX_SEARCH_DAYS)、バックフィル日数、健全性チェック（将来日付の異常検出）を実装。

- リサーチ（ファクター計算・特徴量探索）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: PER、ROE（raw_financials と prices_daily を組合せ）を計算。
    - DuckDB の window 関数を活用し、営業日ベースのウィンドウを想定した実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。サンプル不足時は None を返す。
    - rank, factor_summary: ランク付け（同順位は平均ランク）と基本統計量の集計ユーティリティを提供。
  - research パッケージの public API を __init__ でエクスポート。

- AI（ニュース NLP / レジーム判定）
  - ニュースセンチメントスコア（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を元に銘柄ごとのセンチメント（ai_scores テーブル）を算出して保存。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（前日 15:00 ～ 当日 08:30 JST を UTC に変換）。
    - バッチ処理（1コール最大 20 銘柄）、1 銘柄あたりの記事数/文字数制限、JSON Mode を用いた OpenAI 呼び出し、レスポンス検証を実装。
    - リトライ戦略: 429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフ。その他エラーはフェイルセーフでスキップ。
    - DuckDB executemany の空パラメータ対応（DuckDB 0.10 の制約回避）。
    - レスポンスパースとバリデーションにより不正応答を無視（部分成功を許容）。
    - OpenAI 呼び出し部はテスト容易性のため差し替え可能に設計（_call_openai_api を patch 可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
    - ETF MA 計算（_calc_ma200_ratio）、マクロニュース抽出（_fetch_macro_news）、LLM 評価（_score_macro）、重み合成、閾値判定（bull/neutral/bear）を実装。
    - LLM 呼び出しは gpt-4o-mini を想定、リトライ・フェイルセーフ（失敗時 macro_sentiment = 0.0）を実装。
    - OpenAI クライアントの注入は環境変数 OPENAI_API_KEY または api_key 引数で行う（未設定時は ValueError）。

- ロギング・監査
  - 各主要処理において情報・警告・例外ログを出力。DB 操作は冪等性（DELETE→INSERT のパターンやトランザクション）を考慮。

- テスト支援
  - OpenAI 呼び出しを抽象化し unittest.mock.patch による差し替えを想定した実装（テスト容易性の向上）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 環境変数の取り扱いに配慮:
  - OS 環境変数の上書きを避ける保護機構（protected set）。
  - API キー未設定時は明示的な ValueError を出して処理を停止（OpenAI 呼び出しを行う主な関数群）。
  - .env の読み込み失敗時に警告を出す実装（無闇な例外発生を抑止）。

### Notes / Design Decisions
- ルックアヘッドバイアス防止:
  - 全てのアルゴリズム（news/ regime/ research/ ETL）は datetime.today() / date.today() を直接参照せず、外部から渡された target_date を基準に処理することで将来情報の漏洩を防止しています。
- フェイルセーフ設計:
  - AI API の失敗に対しては基本的に例外を上げず、許容できるデフォルト（例: macro_sentiment=0.0、スキップ）で継続する設計を採用しています。これにより ETL やバッチ処理の完全停止を避けます。
- DuckDB の互換性考慮:
  - executemany に空リストを渡せない制約（DuckDB 0.10 系）を回避するためのガードを実装しています。

---

開発者または運用担当者向け補足:
- OpenAI API を利用する機能（score_news / score_regime）は実行前に OPENAI_API_KEY を環境変数または関数引数で設定してください。設定がない場合は ValueError が発生します。
- .env 自動読込はプロジェクトルート検出に依存します。配布後や異なる配置環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化することができます。
- DuckDB 接続オブジェクトは各関数に明示的に渡す設計です。テストやモックを容易にするため、外部依存（ネットワーク・DB）を注入するスタイルで実装されています。

（以上）