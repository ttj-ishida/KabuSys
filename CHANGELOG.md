# Changelog

すべての注目に値する変更点はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  

なお、この CHANGELOG はコードベースの内容から推測して作成しています。

## [Unreleased]

※なし

## [0.1.0] - 2026-03-28

追加 (Added)
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0 を設定。
- パッケージ公開インターフェースを定義（kabusys.__all__ に data, strategy, execution, monitoring を公開）。
- 環境設定モジュールを追加（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサー実装（コメント、export prefix、クォートとバックスラッシュエスケープ、インラインコメント処理に対応）。
  - 環境変数の保護（OS 環境変数を protected として扱い上書き制御）と上書きオプションを提供。
  - Settings クラスを追加し、J-Quants / kabu API / Slack / DB パス / 実行環境（development/paper_trading/live）などのプロパティを提供。入力値のバリデーション（env, log_level）を実施。
  - 必須環境変数未設定時に ValueError を発生させる `_require` を提供。

- AI 関連モジュールを追加（kabusys.ai）
  - news_nlp モジュール（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini）を用いたバッチセンチメント評価を実装（JSON Mode を想定）。
    - バッチ処理（最大20銘柄 / チャンク）、1銘柄当たり記事数・文字数のトリムによりトークン肥大化を抑制。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフ実装。
    - レスポンス検証ロジック（JSON抽出、results 配列の構造検証、未知コード無視、スコアの数値化と ±1.0 クリップ）。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で部分失敗時の既存スコア保護。
    - テスト容易性を考慮し、内部の OpenAI 呼び出し関数はパッチ可能（unittest.mock.patch に対応）に設計。

  - regime_detector モジュール（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）判定を実装。
    - prices_daily / raw_news / market_regime テーブルを参照・更新。
    - calc_news_window の利用、マクロキーワードで raw_news をフィルタ、OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを取得。
    - API 呼び出しのリトライ、API/パース失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - OpenAI クライアントの呼び出しロジックは news_nlp と別実装にしてモジュール結合を避ける設計。

- データプラットフォーム関連モジュールを追加（kabusys.data）
  - calendar_management
    - JPX カレンダー用の判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - market_calendar テーブルが未取得の場合は曜日ベース（土日除外）のフォールバックを採用。
    - next/prev/search は最大探索日数制限を設け無限ループを防止。
    - calendar_update_job を実装（J-Quants API から差分取得 → save_market_calendar による冪等保存、バックフィル・健全性チェック実装）。
    - DB に NULL が混入した場合のログ警告や挙動の明文化。

  - pipeline / etl
    - ETLResult データクラス（取得/保存件数、品質問題リスト、エラーリスト、ヘルパー: to_dict, has_errors, has_quality_errors）を公開。
    - ETL の内部ユーティリティ（テーブル存在確認、最大日付取得、トレーディング日調整等）を実装。
    - 差分取得、バックフィル、品質チェック（quality モジュールを利用）等を考慮した設計方針を反映（実装の一部は pipeline モジュールに集約）。

- リサーチ/ファクター関連モジュールを追加（kabusys.research）
  - factor_research
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の SQL と Python で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 設計上、prices_daily / raw_financials のみ参照し外部 API にアクセスしない。
    - データ不足時は None を返す等のフォールトトレランスを実装。
    - calc_value では PBR・配当利回りは未実装（注記あり）。

  - feature_exploration
    - 将来リターン計算（calc_forward_returns）を実装（複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient、スピアマンのランク相関）の計算（calc_ic）を実装（欠損値除外、最小有効数チェック）。
    - ランク変換ユーティリティ（rank）と統計サマリー（factor_summary）を実装。標本分散計算や中央値算出を実装し、同順位の平均ランク処理を行う。
    - pandas 等に依存しない純粋標準ライブラリ実装。

- DB とロギング方針
  - DuckDB を主要な分析 DB として想定し、多数の関数は DuckDB 接続を引数に受ける設計。
  - 各所で logger を利用し処理の開始/完了・失敗理由をログ出力。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT / ON CONFLICT 等）して安全に更新。

変更 (Changed)
- （初回リリースのため該当なし）

修正 (Fixed)
- （初回リリースのため該当なし）

注記 (Notes / Known limitations)
- OpenAI API キー未設定時は ValueError を送出する（score_news, score_regime）。テスト用に api_key を引数で注入可能。
- news_nlp と regime_detector は OpenAI 呼び出し実装を分離しており、ユニットテスト時は内部呼び出しをパッチすることを想定。
- calc_value で PBR・配当利回りは未実装（将来拡張予定）。
- DuckDB executemany のバージョン差異に配慮した実装が随所にある（空リスト渡しの回避等）。
- 全体設計としてルックアヘッドバイアス対策（datetime.today()/date.today() の直接参照回避、クエリの排他条件など）を優先している。

セキュリティ (Security)
- （初回リリースのため該当なし）

----

以上。必要であれば各機能ごとに詳細な変更点や使用例、互換性・移行ガイドを追記します。