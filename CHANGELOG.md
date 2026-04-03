KEEP A CHANGELOG
=================

すべての重要な変更点をこのファイルに記録します。
このプロジェクトは「Keep a Changelog」フォーマットに従います。
比較的安定なリリース履歴を提供するため、各リリースに対して "Added/Changed/Fixed/Security" 等のセクションで要点を記載しています。

[Unreleased]
-----------

- なし（初期リリース: 0.1.0 に全機能を集約しています）

[0.1.0] - 2026-04-03
-------------------

Added
- パッケージ初期リリース。本システムは日本株自動売買支援のためのデータ取得・特徴量計算・AIセンチメント評価・カレンダー管理・ETL ユーティリティ等を含みます。
- kabusys.config
  - Settings クラスを提供し、環境変数から構成値を取得する API を公開。
  - .env 自動ロード機能を追加（優先順位: OS 環境 > .env.local > .env）。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 必須の環境変数取得用のヘルパー _require を実装（未設定時は ValueError）。
  - 設定項目（例）: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、LINE_CHANNEL_ACCESS_TOKEN、PID/FLAG/閾値、DUCKDB/SQLITE パス、KABUSYS_ENV（development/paper_trading/live）等。
- kabusys.ai
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄単位のセンチメント（-1.0〜1.0）を算出。
    - チャンク処理（最大 20 銘柄/API コール）、1銘柄あたり最大記事数・文字数のトリム、レスポンスのバリデーション、スコアのクリッピング、部分失敗時の DB 書き換え（DELETE → INSERT）により冪等性とロバスト性を確保。
    - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30）を UTC に変換して DB クエリに適用。calc_news_window を公開。
    - ネットワーク・レート制限・5xx 等に対する指数バックオフ・リトライを実装。API キーは引数または環境変数 OPENAI_API_KEY。
  - regime_detector.score_regime
    - ETF(1321) の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロキーワードによる raw_news のフィルタリング、OpenAI 呼び出し（JSON Mode）と堅牢な例外・リトライ処理を実装。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - lookahead バイアス防止のため内部処理で datetime.today()/date.today() を参照しない設計。
- kabusys.data
  - calendar_management
    - JPX カレンダー管理ロジックを実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が空または未登録日の場合は曜日ベース（土日除外）でフォールバック。DB 登録がある場合は DB 値を優先。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックを含む）。
  - pipeline / etl / ETLResult
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラー一覧を含む）。
    - ETL パイプラインの設計に基づく差分取得・保存・品質チェックの方針を実装（jquants_client 経由での保存処理、バックフィル等）。
    - SQL テーブルの存在チェックユーティリティ、最大日付取得ユーティリティ等を実装。
  - etl の公開インターフェースとして ETLResult を再エクスポート。
  - jquants_client への依存を想定（fetch/save 操作は jquants_client に委譲）。
- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（不足時は None）。
    - Volatility: 20 日 ATR、相対ATR、平均売買代金、出来高比率。
    - Value: raw_financials から最新財務データを取得して PER/ROE を計算（EPS が無効な場合は None）。
    - すべて DuckDB の prices_daily / raw_financials を参照して SQL レイヤで計算し、(date, code) をキーとする dict のリストを返す。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン入力検証あり（1〜252）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を実装（有効レコードが 3 件未満なら None）。
    - rank / factor_summary: ランク化（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を算出するユーティリティを提供。
    - pandas 等の外部依存を用いず、標準ライブラリのみで実装。
- パッケージ構成
  - src/kabusys 以下に AI、data、research、config 等のモジュールを整備。__init__.py で主要サブパッケージをエクスポート。
- OpenAI 連携
  - gpt-4o-mini を想定した Chat Completions JSON Mode を使用するインターフェースを実装。テスト容易性のため _call_openai_api を各モジュールでローカル定義しモック差し替え可能。

Changed
- N/A（初期リリース）

Fixed
- N/A（初期リリース）

Security
- AI 機能（score_news, score_regime）は OpenAI API キーが必須（引数あるいは OPENAI_API_KEY 環境変数）。キー未設定時は ValueError を発生させる仕様。
- 環境変数の読み込みはデフォルトで自動実行されるため、CI/テスト環境で影響が出る場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化してください。
- 機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env/.env.local または環境変数で管理する想定。README / .env.example を参考にキーを準備してください。

Notes / Implementation details / 限界
- DuckDB をデータ操作の中心に使用しています。DuckDB バージョン差による executemany の空リスト扱いなどに注意（コード内で安全側のガードあり）。
- 全ての関数はルックアヘッドバイアス防止のため、内部で date.today() を直接参照しない設計です。呼び出し側から明示的に target_date を渡してください。
- LLM レスポンスは JSON Mode を期待するが、念のため前後に余計なテキストが混ざるケースを考慮したパース回復ロジックを実装しています。レスポンスの形式が変わるとパースに失敗してスコア算出がスキップされる場合があります。
- jquants_client の具体的実装（API 呼び出しや保存処理）は本リリースでは外部モジュールに委譲しているため、実運用時は対応するクライアント実装を用意してください。

移行 / 利用ガイド（簡易）
- 環境変数の設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。AI を使う場合は OPENAI_API_KEY を設定。
- DuckDB 接続を作成し、各テーブル（prices_daily, raw_news, news_symbols, raw_financials, market_calendar, ai_scores, market_regime 等）を準備してから各関数を呼び出してください。
- ETLResult を受け取る ETL パイプラインを組み、calendar_update_job / pipeline の呼び出しでデータ収集と品質チェックを行ってください。

問い合わせ / 貢献
- 初期リリースにつき、API 使い勝手やエッジケースの報告・プルリクエストを歓迎します。テストコード・ドキュメントの追加は今後の優先課題です。