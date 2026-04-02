CHANGELOG
=========

すべての重要な変更を記録します。  
このプロジェクトは Keep a Changelog の慣習に従って管理しています。  

フォーマット:
- 変更はセクション（Added / Changed / Fixed / Security / Breaking）ごとに分類しています。
- 各エントリは可能な限りモジュール名や挙動を明示しています。

Unreleased
----------
（ありません）

0.1.0 - 2026-04-02
------------------

Added
- 初期リリース: KabuSys パッケージ v0.1.0 を公開。
  - パッケージ公開用の __version__ を "0.1.0" に設定。
  - パッケージトップの __all__ に ["data", "strategy", "execution", "monitoring"] を定義。

- 環境設定 / 設定管理 (kabusys.config)
  - プロジェクトルート検出: .git または pyproject.toml を起点にプロジェクトルートを探索する自動 .env ロード機能を実装。
  - .env ファイルの自動ロード順序を実装（OS 環境変数 > .env.local > .env）。
  - .env パーサを実装:
    - export KEY=... 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント取り扱いの実装。
    - 無効行・コメント行を無視。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能に:
    - J-Quants / kabuステーション / Slack / DB パス（DuckDB / SQLite）/ 監視閾値 / 環境（development/paper_trading/live）/ログレベル等を提供。
    - 必須項目に対して _require による ValueError を投げる仕組みを導入。
    - env・log_level の値検証とヘルパー is_live / is_paper / is_dev を追加。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp.score_news)
    - raw_news と news_symbols を集約して銘柄ごとにニューステキストを作成し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄別センチメント（-1.0〜1.0）を計算、ai_scores テーブルへ書き込み。
    - 時刻ウィンドウ計算（JST 前日 15:00 ～ 当日 08:30）を calc_news_window で提供。
    - バッチ処理、銘柄単位の文字数トリム、最大記事数制限、スコアのクリップ処理を実装。
    - JSON レスポンスのバリデーション、余分な前後テキストが混ざった場合の最外殻 {} 抽出ロジックを実装。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフリトライ、失敗時は該当チャンクをスキップするフォールバックを採用。
    - DuckDB の executemany 空パラメータ制約に配慮し、空時は実行しない分岐を実装。
  - 市場レジーム判定 (kabusys.ai.regime_detector.score_regime)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、ニュースベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - raw_news からマクロキーワードでフィルタするフェーズを実装。
    - OpenAI 呼び出しは専用の内部実装を持ち、API エラーへのリトライとフェイルセーフ（API 失敗時は macro_sentiment = 0.0）を備える。
    - look-ahead バイアス防止: target_date 引数ベースで処理を行い、datetime.today()/date.today() を直接参照しない設計。

- データプラットフォーム / ETL (kabusys.data)
  - ETL の公開インターフェースである ETLResult を実装（kabusys.data.pipeline.ETLResult を再エクスポート）。
  - pipeline モジュール:
    - 差分取得・保存・品質チェック（quality モジュールとの連携）を想定した ETLResult データクラスを導入。
    - 保存件数・取得件数・品質問題・エラーの集約と to_dict 変換機能を提供。
    - DuckDB 接続の存在チェックや最大日付取得ユーティリティを実装（テーブル存在判定等）。
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - calendar_update_job を実装し、J-Quants からの差分取得・バックフィル・健全性チェック（将来日付の異常検知）・冪等保存を行うジョブを追加。
    - DB が未準備な場合の曜日ベースフォールバック（週末を非営業日扱い）を実装し、DB とフォールバックの一貫性を確保。

- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離の算出を実装（prices_daily を参照）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials と当日株価から PER, ROE を計算（EPS が 0 または欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: ランク付けユーティリティ（同順位は平均ランク）。
  - kabusys.research.__init__ で主要関数を再エクスポート。

- API クライアント連携の設計上の注意点
  - OpenAI クライアントの呼び出しを内部関数化し、テスト時にパッチして差し替え可能にしている（unittest.mock.patch により差し替え容易）。
  - DuckDB の各種バージョン差異へ配慮した実装（executemany の空リスト回避、リスト型バインドの互換性対応など）。

Changed
- 初回リリースのため該当なし。

Fixed / Improvements
- .env パーサの堅牢化:
  - 引用符内のエスケープ処理、コメント検出の正確化、export プレフィックス対応などにより実運用での互換性を強化。
- OpenAI 呼び出し耐性の強化:
  - RateLimit / 接続断 / タイムアウト / 5xx に対するリトライ（指数バックオフ）を実装。
  - 非致命的な API エラー時は例外を投げずフォールバック値（0.0）で継続し、処理全体が停止しないように設計。
- レスポンスパース耐性:
  - JSON モードでも稀に前後テキストが混入するケースを想定し、最外の {} を抽出して復元するロジックを追加。
- ルックアヘッドバイアス対策:
  - AI/ETL/Research の各処理で datetime.today()/date.today() を直接参照しない設計（必ず target_date を引数で受ける）。
- DB 書き込みの冪等性:
  - market_regime / ai_scores 等への書き込みで、DELETE → INSERT の順に行うことで置換（部分失敗時の既存データ保護）を実現。
- エラーハンドリング改善:
  - トランザクション中の例外時に ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを出すなど堅牢性を向上。

Breaking Changes
- 初期リリースのため無し。

Security
- 初版につき、重要なセキュリティ警告は特に無し。ただし OpenAI API キーや外部トークンは環境変数経由で管理することを想定している（Settings にて必須チェック）。

Notes / Implementation details
- 多くの機能は DuckDB に依存するため、DuckDB のバージョン差異に起因する動作差を考慮した実装になっています（executemany の挙動回避など）。
- OpenAI 連携は gpt-4o-mini を想定した JSON Mode を用いています。API 仕様変更に備え、レスポンスパースやステータスコードの扱いは柔軟に実装しています。
- ETL / カレンダー / リサーチ機能は「本番口座・発注 API へはアクセスしない」方針で実装されており、データ取得・前処理・解析に注力しています。

今後
- strategy / execution / monitoring の各モジュール（トップレベル __all__ に含まれる）は今後のリリースで実装・拡張予定。
- テストカバレッジ強化、外部 API 呼び出しのモック用フック整備、ドキュメント（API リファレンス・運用手順）の充実を予定。