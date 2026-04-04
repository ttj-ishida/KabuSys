Keep a Changelog
=================

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトの変更履歴は "Keep a Changelog" の慣例に従っています。  

[Unreleased]
------------

- プレースホルダ。次リリースでここから移動します。

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージ初期リリース: kabusys (日本株自動売買システム)。
  - バージョン: 0.1.0
  - パブリックモジュール: data, strategy, execution, monitoring が __all__ で公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルと OS 環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: __file__ を起点に .git または pyproject.toml を探索し、CWD に依存しない方式。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサー: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 環境変数保護: OS 環境変数を保護する protected セットを導入し、override オプションでの上書きを制御。
  - Settings クラス: 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / 監視閾値 / ランタイム環境判定 等）。
    - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値チェック）。
    - 各種パスは Path に変換して expanduser を適用。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとのニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを算出。
    - バッチ処理: 最大 20 銘柄チャンクで API へ送信。
    - 1 銘柄あたりの記事数・文字数上限（記事数: 10 件、文字数: 3000 文字）でトークン肥大を抑制。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ。
    - レスポンスの厳密なバリデーションとスコアクリップ（±1.0）。
    - 書き込み: 成功した銘柄のみを対象に ai_scores テーブルを置換（部分置換で部分失敗を保護）。
    - テスト用に _call_openai_api をパッチ可能（unittest.mock で差し替え容易）。
    - 時間ウィンドウ計算（calc_news_window）：JST 基準で前日 15:00 ～ 当日 08:30 を UTC-naive に変換して使用（ルックアヘッド防止）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベースでタイトルを取得（最大 20 件）。
    - OpenAI を gpt-4o-mini / JSON Mode で呼び出し。API 失敗時は macro_sentiment=0.0 としてフェイルセーフ処理。
    - レジームスコアの合成とクリップ、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しは独立実装でモジュール結合を避ける。リトライと 5xx ハンドリングを実装。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照せず、与えられた target_date のみを使用。

- データ基盤モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダー管理機能を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがある場合は DB を優先し、未登録日は曜日ベースのフォールバック（weekend 判定）を行う一貫した動作。
    - 夜間バッチ: calendar_update_job により J-Quants から差分取得し market_calendar を冪等更新。バックフィル・健全性チェック実装。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループを防止。
    - DuckDB から返る値を安全に date に変換するユーティリティを実装。

  - ETL パイプライン (pipeline.ETLResult, etl 再エクスポート)
    - ETLResult dataclass を導入し、ETL 実行の取得数・保存数・品質問題・エラー等を構造化して返却。
    - 差分取得、バックフィル、J-Quants クライアント経由の冪等保存（save_* 関数）を想定した設計。
    - 品質チェックは収集を優先し、呼び出し元での判断を可能にする（Fail-Fast しない）。DuckDB の executemany 空リスト制約に配慮した実装方針を明記。

- 研究（Research）モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）、バリュー（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベース実装で、prices_daily / raw_financials を参照。結果は (date, code) をキーとする dict のリストで返却。
    - データ不足時の None 扱い、ウィンドウ・スキャン日数のバッファ設計。

  - feature_exploration
    - 将来リターン計算 (calc_forward_returns) を実装（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関、少数サンプル / 同順位対応。
    - 基本統計量集計 (factor_summary) とランク変換 util (rank) を実装。外部依存を持たない純粋 Python 実装。

Changed
- 設計上の注意点・安全策をコード内に明記：
  - ルックアヘッドバイアス防止のため、全ての分析・スコアリング関数は与えられた target_date のみを参照し、現在時刻を直接参照しない実装。
  - OpenAI 呼び出しに対して厳密な JSON Mode 想定のバリデーション・パース復元処理を追加（前後余分テキストの復元等）。
  - DuckDB の互換性を考慮し、executemany に空リストを渡さないガードを導入。
  - DB 書き込みは冪等性を重視（DELETE→INSERT、ON CONFLICT などの手法で既存データ保護）。
  - API 失敗時のフェイルセーフ動作（スコア 0.0、スキップ、ログ出力）を全 AI/ETL ワークフローで採用。

Fixed
- （初期リリース）既知のバグ修正履歴はなし（初回公開時点の実装）。

Security
- OpenAI API キーや各種パスワードは環境変数で管理する設計。
  - 必須キー未設定時は ValueError を送出して明示的に失敗させる箇所がある（score_news / score_regime / Settings の必須プロパティ等）。
- .env の自動ロード時に OS の既存環境変数を誤って上書きしないよう保護設計を導入。

Testing / Developer Notes
- OpenAI 呼び出しを行う内部関数（各 ai モジュールの _call_openai_api）を unittest.mock.patch で差し替え可能にして、API 実際呼び出しをモック化しやすくしている。
- 設定の自動読み込みはテスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
- DuckDB の日付変換や executemany の制約に配慮した実装でローカルテストの再現性を向上。

注記
- 本 CHANGELOG は現行コードベースから推測して作成した初期の変更履歴です。リリースごとに Unreleased セクションから適宜移動・更新してください。