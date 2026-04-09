# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
リリース日付はコードベースの最初の公開バージョンとして作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。本バージョンは日本株自動売買システム「KabuSys」の基盤機能を提供します。

### Added
- パッケージ全体
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - public API のエクスポートを各モジュールで定義（__all__）。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動的にルートを探索して .env/.env.local を読み込む。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は override=True）。
  - 自動読み込みの無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用途）。
  - .env パーサ実装:
    - export PREFIX=... 形式対応
    - シングル/ダブルクォート内でのエスケープ処理対応
    - コメント処理（クォート有無での取り扱いの違い）対応
  - 設定オブジェクト Settings を提供（settings インスタンス）:
    - J-Quants / kabuステーション / LINE / DB / Paper Trading / 監視 / システム関連のプロパティを用意
    - 必須キー未設定時は明示的なエラー（_require）
    - PAPER_FILL_MODE のバリデーション（instant|partial|never|reject）
    - KABUSYS_ENV と LOG_LEVEL の値チェック（許可値の検証）
    - Path 型でのパス返却（expanduser 対応）
    - is_live / is_paper / is_dev のヘルパーを提供

- AI（自然言語・レジーム判定）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成
    - OpenAI（gpt-4o-mini）へのバッチ送信機能（1リクエスト最大 20 銘柄）
    - 1銘柄あたりの記事数上限・文字数トリム（記事数上限: 10 / 文字上限: 3000）
    - JSON Mode を用いたレスポンス検証と堅牢なパース処理（前後余分テキストの復元処理含む）
    - レスポンス検証ルール（results 配列、各要素 code/score、未知コードは無視、数値→クリップ）
    - 再帰的リトライ（429・ネットワーク・タイムアウト・5xx） と 指数バックオフ
    - API 失敗時は個別チャンクをスキップし、可能な範囲で処理継続（フェイルセーフ）
    - DuckDB への書き込みは冪等操作（DELETE → INSERT）を採用し、部分失敗時に既存データを保護
    - 公開関数: score_news(conn, target_date, api_key=None)
    - テスト性: _call_openai_api はパッチ可能（unittest.mock.patch で差し替え）

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と
      マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出
    - マクロキーワードによる raw_news フィルタリング（タイトル検索）
    - OpenAI（gpt-4o-mini）によるマクロセンチメント評価（JSON 出力期待）
    - API の冗長性対策: リトライ / バックオフ、5xx とその他エラーの扱いを分ける
    - API 失敗やパース失敗時は macro_sentiment = 0.0 として継続（フェイルセーフ）
    - レジームスコア合成式、閾値に基づくラベル付け、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - 公開関数: score_regime(conn, target_date, api_key=None)
    - テスト性: news_nlp と結合しない形で OpenAI 呼び出しを実装（モジュール結合低減）

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルの利用／フォールバック（未取得時は曜日ベース）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days の実装
    - calendar_update_job により J-Quants から差分取得して冪等に保存（バックフィル、健全性チェックを含む）
    - DB にない日を曜日フォールバックで扱い、next/prev/get の結果が一貫するよう設計
    - 最大探索範囲で無限ループ防止（_MAX_SEARCH_DAYS）

  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）
    - 差分更新、バックフィル、保存（jq.save_* を通じた冪等保存）および品質チェックの設計方針を実装ベースで反映
    - ETLResult は品質問題とエラーの集合を管理、辞書化用 to_dict を提供

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算
    - calc_volatility: 20日 ATR / 相対 ATR / 平均売買代金 / 出来高比率を計算
    - calc_value: raw_financials を用いた PER / ROE の計算（target_date 以前の最新財務データを使用）
    - 設計: DuckDB の SQL を中心に計算し、prices_daily / raw_financials のみ参照。外部 API に依存しない。

  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 与えられた horizon（デフォルト [1,5,21]）で将来リターンを計算
    - calc_ic: factor と forward return のスピアマンランク相関（IC）を計算（有効レコードが3未満なら None）
    - rank: 同順位は平均ランクで扱う正確なランク実装（丸めによる tie 対応）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
    - 設計: DuckDB + 標準ライブラリのみ（pandas 等に依存しない）

### Changed
- 初回リリースのため変更履歴はなし。

### Fixed
- 初回リリースのため修正履歴はなし。

### Security
- OpenAI API キー周りは環境変数 OPENAI_API_KEY または明示的な api_key 引数で解決。未設定時は ValueError を投げて誤動作を防止。

### Notes / 設計上の考慮点
- ルックアヘッドバイアス対策:
  - 全ての分析/スコアリング処理は datetime.today() / date.today() に依存せず、必ず target_date 引数を基準とする実装。
  - prices_daily クエリは target_date 未満／未満等の排他条件を用いることで将来データ参照を回避。
- フェイルセーフ設計:
  - AI 呼び出し失敗時はスコアを 0.0 にフォールバックしたり、チャンクをスキップして処理を継続する方針を採用。
- テスト性:
  - OpenAI 呼び出しは内部関数（_call_openai_api）を patch して差し替え可能にし、ユニットテストが容易。
- DuckDB 互換性:
  - executemany に空リストを渡さない等、DuckDB 0.10 系の挙動を考慮した実装。

---

今後のリリースでは、機能追加（発注実行モジュール、モニタリング/アラートの実装強化）、性能改善、より詳細な品質チェック機能を予定しています。