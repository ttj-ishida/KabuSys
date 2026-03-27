Keep a Changelog に準拠した変更履歴です。

すべての記載はリポジトリ内のソースコード（コメント、docstring、実装）から推測して作成しています。

注意: 日付は本CHANGELOG作成日です。

Unreleased
----------
- なし（次のリリースでの変更をここに記載してください）

[0.1.0] - 2026-03-27
--------------------
Added
- 初回リリース: KabuSys — 日本株自動売買システムのコアライブラリを追加。
- パッケージメタ:
  - バージョン情報を src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - 公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。
- 環境設定管理 (kabusys.config):
  - .env ファイルや環境変数から設定値を読み込むユーティリティを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）に基づく .env 自動読み込み。
  - .env のパースにおいて export プレフィックス、クォート文字列、インラインコメント処理などに対応。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグの追加。
  - 必須環境変数チェック用の _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）とヘルパープロパティ（is_live / is_paper / is_dev）。
  - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）を設定。
- AI 関連（kabusys.ai）:
  - ニュース NLP スコアリング (kabusys.ai.news_nlp):
    - raw_news と news_symbols を用いて銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）により銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 20 銘柄／Call）、件数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によるトリム。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢な検証（JSON 抽出、results リスト、コード検証、数値チェック）を実装し、スコアは ±1.0 にクリップ。
    - DuckDB への書き込みは冪等化（DELETE → INSERT）し、部分失敗時に既存のスコアを保護する実装。
    - テスト用に _call_openai_api をモック差替え可能。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）で、calc_news_window を提供（ルックアヘッド対策のため datetime.today() を直接参照しない設計）。
  - 市場レジーム判定 (kabusys.ai.regime_detector):
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を用いて日次でレジーム（bull/neutral/bear）を判定。
    - ma200_ratio を DuckDB の prices_daily から算出（target_date 未満のデータのみ使用、データ不足時は中立値を採用）。
    - raw_news からマクロキーワードで記事タイトルを抽出し、OpenAI により macro_sentiment を算出（記事なしや API 失敗時は 0.0 にフォールバック）。
    - OpenAI 呼び出しは独立実装でモジュール結合を低く保ち、リトライとフェイルセーフを実装。
    - 判定結果は market_regime テーブルに冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
- データプラットフォーム（kabusys.data）:
  - カレンダー管理 (calendar_management):
    - JPX カレンダー（market_calendar テーブル）の管理、営業日判定、前後営業日取得、期間内営業日取得、SQ 判定を提供。
    - DB 登録値優先、未登録は曜日ベースのフォールバック（週末は非営業日）で一貫した振る舞いを実装。
    - 次/前営業日の探索は最大探索日数制限（_MAX_SEARCH_DAYS）で無限ループを防止。
    - 夜間バッチ用の calendar_update_job を実装（J-Quants API から差分取得、バックフィル、健全性チェック）。
  - ETL パイプライン (pipeline):
    - ETLResult データクラスを公開（取得・保存件数、品質問題、エラー一覧などを含む）。
    - 差分取得、バックフィル、品質チェックの設計方針に沿ったユーティリティを実装（jquants_client と quality モジュールに依存）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
  - jquants_client を使用する箇所の参照（fetch/save の呼び出しポイントを含む）。
- Research（kabusys.research）:
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Value（PER、ROE）などのファクター計算関数を実装。
    - 関数は DuckDB の prices_daily / raw_financials を参照し、(date, code) をキーとする dict のリストを返す。
    - データ不足時の None 処理、ログ出力を実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic: Spearman ランク相関）、ファクター統計サマリー（factor_summary）、ランク変換（rank）を実装。
    - pandas 等外部ライブラリに依存しない純標準実装。
- 共通設計と運用上の配慮:
  - ルックアヘッドバイアス防止: date 引数ベースで計算し、datetime.today()/date.today() を直接参照しない設計が複数モジュールで採用されている。
  - DuckDB を主要なオンディスク DB として利用。SQL とウィンドウ関数を多用した実装。
  - OpenAI 呼び出しは gpt-4o-mini モデル + JSON mode を前提に実装。
  - API エラーやレスポンス不整合に対するフェイルセーフ（ログ警告・スコア 0.0 など）を多くの箇所で実装。
  - テスト容易性: API 呼び出し関数の差し替えポイントや KABUSYS_DISABLE_AUTO_ENV_LOAD による環境制御などを用意。
  - 実装は冪等性・部分失敗対策を重視（DB の DELETE→INSERT、executemany の空リスト処理などの注意点を反映）。

Changed
- なし（初回リリースのため該当なし）

Fixed
- なし（初回リリースのため該当なし）

Removed
- なし

Security
- なし（特別なセキュリティ修正は含まれない。環境変数に API キーやトークンを設定する運用上の注意はドキュメントで管理してください）

Notes / Known limitations (実装から推測)
- OpenAI API の利用には環境変数 OPENAI_API_KEY または各関数呼び出し時の api_key 引数が必要。未設定時は ValueError を送出する設計。
- DuckDB の executemany に空リストを渡せない点を考慮したガードがある（互換性対策）。
- raw_financials による Value 計算は EPS が 0 または欠損の場合は PER を None にする等の保守的処理を行う。
- calendar_update_job は J-Quants のクライアント実装 (jquants_client) に依存。API 側のエラーやネットワーク障害時はロギングして 0 を返す。
- 一部の設計判断（例: ETF 1321 を市場レジーム判定の代表として使用）は現フェーズの方針による固定選択であり、将来のパラメータ化・拡張が想定される。

Authors
- 実装に基づく初期機能群（ソースコード内のコメント/実装を元にCHANGELOGを作成）

--- end of CHANGELOG ---