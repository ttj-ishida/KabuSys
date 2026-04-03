CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の慣習に従い、日本語で記載しています。  
リリース日付はコードベースから推測できる最新の状態（本ファイル作成日）を使用しています。

フォーマット:
- Unreleased: 開発中の変更（現時点で未リリース）
- 各バージョン: 主な追加・変更点をカテゴリ別に列挙

Unreleased
----------
（なし）

[0.1.0] - 2026-04-03
-------------------

Added
- パッケージ基盤
  - kabusys パッケージ初期リリース。__version__ = "0.1.0" を設定。
  - パッケージの公開 API を __all__ にて data, strategy, execution, monitoring を想定。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env/.env.local の読み込み順序を実装（OS 環境変数 > .env.local > .env）。.env.local は override=True として .env の値を上書き可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env ファイルの行パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォートとバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートあり/なしでの差別化）
  - 環境変数取得用 Settings クラスを提供（J-Quants、kabuステーション、LINE、DB パス、監視閾値、ログレベル等のプロパティを定義）。
  - Settings に入力バリデーションを実装（KABUSYS_ENV, LOG_LEVEL の有効値チェック）および利便性プロパティ（is_live/is_paper/is_dev）。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へ送信して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）用の calc_news_window を公開。
    - バッチ処理（1回最大20銘柄）、1銘柄あたりの記事数／文字数上限（記事数＝10、文字数＝3000）によるトリム、JSON Mode レスポンスのバリデーションとスコア ±1.0 クリップを実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。失敗時は個別チャンクをスキップするフェイルセーフ設計。
    - テスト用に _call_openai_api をパッチで差し替え可能。

  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出はニュースタイトルにマクロキーワードでフィルタ（最大 20 件、新しい順）。
    - OpenAI 呼び出しに対するリトライ、API 失敗時は macro_sentiment=0.0 のフォールバック、合成スコアのクリップ、ラベル閾値を実装。
    - 結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み、DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - market_calendar を利用した営業日判定ユーティリティを提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB にカレンダー登録がない場合は曜日ベース（土日休）でフォールバックする一貫したロジック。
    - カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック）。
    - _MAX_SEARCH_DAYS, BACKFILL, SANITY チェックなどの安全策を導入。

  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - 差分更新・バックフィル・品質チェックを想定した設計（データ取得 → 保存（idempotent） → 品質チェック）。
    - DuckDB を前提にしたテーブル存在チェックや最大日付取得ユーティリティを実装。

- リサーチ（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER・ROE）の計算関数を提供（calc_momentum, calc_volatility, calc_value）。
    - DuckDB のウィンドウ関数を用いた実装で、データ不足時の None 扱いを明示。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：スピアマンのランク相関）計算、rank ユーティリティ、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリで実装。

Changed
- （初版のため該当なし）

Fixed
- .env パーサを強化:
  - クォート内のバックスラッシュエスケープ対応やインラインコメントの扱いを明確化。
  - export キーワードや不正行の無視処理を実装し、実用性を向上。

Security
- 環境変数の取り扱いにおいて、OS 環境変数を protected として .env による上書きを防ぐ仕組みを導入（protected set を使用）。

Notes / Implementation details
- ルックアヘッドバイアス回避:
  - news_nlp / regime_detector / research の各関数は datetime.today() / date.today() を内部で参照しない設計。判定・集計は呼び出し元から渡される target_date に基づく。
  - DB クエリでは date < target_date 等の排他条件によりルックアヘッドを防止。

- OpenAI 統合:
  - gpt-4o-mini を想定し、JSON Mode を利用して厳密な JSON を期待するプロンプト設計。
  - API 呼び出しは共通化されているが、モジュール間でプライベート関数を共有しない（各モジュールで独立した _call_openai_api を持つ）。
  - テスト用に API 呼び出し部分をパッチ可能にしている。

- DB 書き込みの冪等性とエラーハンドリング:
  - market_regime / ai_scores 等の書き込みは DELETE → INSERT の順で実行し、トランザクション（BEGIN/COMMIT/ROLLBACK）を用いて冪等性を確保。
  - DuckDB の executemany に関する互換性（空リスト不可）を考慮し、空チェックを行ってから executemany を呼ぶ。

- 必要な環境変数（代表例）
  - OPENAI_API_KEY（AI モジュール）
  - JQUANTS_REFRESH_TOKEN（J-Quants クライアント）
  - KABU_API_PASSWORD（kabu ステーション連携）
  - その他（LOG_LEVEL, KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH 等）は Settings でデフォルト値や検証を提供。

Known limitations / TODO
- strategy / execution / monitoring モジュールの実装は本リリースで想定されているものの、コードスニペットでは詳細が含まれていないため、将来的な追加実装が想定される。
- J-Quants クライアント（jquants_client）はデータ取得・保存の抽象として参照されているが、外部実装・モックが必要。
- PBR や配当利回りなどの一部バリューファクターは未実装（calc_value に注釈あり）。

参考
- 設計方針として「外部 API 呼び出し時はフェイルセーフで継続する」「ルックアヘッドバイアスを排除する」「DB 書き込みは冪等にする」などの原則が随所に反映されています。

-----------------------------------------------------------------------------
この CHANGELOG はコードベースからの推測に基づいて作成しています。追加の変更履歴やリリースノートが存在する場合は、それに合わせて更新してください。