KEEP A CHANGELOG に準拠した形式で、コードベースから推測した変更履歴を作成しました（日本語）。初期リリース 0.1.0 としてまとめています。

CHANGELOG.md
=============
すべての注目すべき変更を記載します。  
フォーマットは「Keep a Changelog」を基にしています。

Unreleased
----------
（空）


0.1.0 - 2026-04-04
------------------
最初の公開リリース。

Added
- 全体
  - パッケージ初期化を追加（kabusys.__init__ に __version__ = "0.1.0"、主要モジュールを __all__ で公開）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を自動読み込みする仕組みを追加。プロジェクトルートは .git または pyproject.toml を基準に探索するため、CWD に依存しない自動読み込みを実装。
  - .env パース機能を強化（コメント、'"/" 表示、export KEY=val フォーマット、インラインコメントの扱いなどに対応）。
  - .env 読み込みの優先順位を OS 環境変数 > .env.local > .env に設定。既存の OS 環境変数を protected として保護するオプションを実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を導入（テスト用途を想定）。
  - settings オブジェクトを提供し、J-Quants / kabuステーション / LINE / DB / 監視設定 / システム設定（env、log_level）のプロパティとしてアクセス可能に。env と log_level は妥当性チェックを行い不正な値は ValueError を送出。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）や監視用ファイルパス（PID_FILE_PATH, KILL_FLAG_PATH）、リソース閾値（CPU/MEM/DISK）などの既定値を設定。
- AI モジュール（kabusys.ai）
  - ニュースの NLP スコアリング（kabusys.ai.news_nlp）を追加。
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）に JSON モードでバッチ送信してセンチメント（-1.0〜1.0）を取得。
    - タイムウィンドウの定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供（UTC 換算済み）。
    - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字にトリムすることでトークン肥大化に対処。
    - 429（RateLimit）、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライを実装。
    - レスポンスの堅牢なバリデーション（JSON抽出、results 配列チェック、コード照合、数値化、有限値チェック）と ±1.0 でのクリップ処理を実装。
    - 部分成功時に既存スコアを消さないよう、取得済みコードのみを DELETE → INSERT する冪等的な DB 書き込みを実装（DuckDB の executemany の空リスト制約に配慮）。
    - テスト容易性のため _call_openai_api を patch して差し替え可能に。
  - 市場レジーム判定（kabusys.ai.regime_detector）を追加。
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）判定。
    - ma200_ratio の計算、マクロキーワードでの raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）の実装、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - 計算結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI 呼び出しはモジュール独立の内部実装とし、テスト時に差し替え可能。
- データプラットフォーム（kabusys.data）
  - ETL パイプライン公開インターフェース（kabusys.data.etl）として ETLResult を再エクスポート。
  - pipeline モジュールを追加（kabusys.data.pipeline）:
    - ETLResult dataclass を導入し、取得数・保存数・品質問題・エラー等を構造化して報告可能に。
    - 差分取得、backfill、品質チェックの設計方針を明文化。
    - DuckDB 上でのテーブル存在チェックや最大日付取得等のユーティリティを準備。
  - カレンダー管理（kabusys.data.calendar_management）を追加:
    - JPX カレンダー（market_calendar）に基づく is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の判定ロジックを提供。
    - DB にデータがない場合は曜日ベース（土日非営業日）のフォールバック動作を提供。
    - calendar_update_job を実装し、J-Quants API から差分取得 → 保存（バックフィルや健全性チェック付き）を行う。jq クライアントとの連携を想定。
- Research（kabusys.research）
  - factor_research を追加（calc_momentum / calc_value / calc_volatility）。
    - prices_daily / raw_financials を基にモメンタム（1/3/6 ヶ月）、200日 MA 乖離、ATR20、平均売買代金などを計算。
    - データ不足時の None 扱い、DuckDB のウィンドウ関数を活用した実装。
  - feature_exploration を追加（calc_forward_returns / calc_ic / factor_summary / rank）。
    - 将来リターン計算（任意ホライズン）・スピアマン IC 計算（ランク相関）・統計サマリー等を提供。
    - pandas など外部依存を用いず標準ライブラリと DuckDB のみで実装。
- パッケージ公開 API
  - 適切な __all__ を各サブパッケージに追加（例: kabusys.ai.__all__, kabusys.research.__all__, kabusys.data.etl の再エクスポート等）。

Changed
- （初期リリースのため履歴上の既存変更なし）

Fixed
- 読み込み失敗や例外発生時に警告ログを出し、処理を継続するフェイルセーフ設計を多くの箇所に適用（.env 読み込み失敗、OpenAI レスポンスパース失敗、API リトライ上限到達時のフォールバックなど）。
- DuckDB の executemany が空リストを受け付けない点に配慮して、空のパラメータに対する分岐を挿入（ai/news_nlp, pipeline の DB 書き込み等）。

Security
- OpenAI API 呼び出しを行う関数（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY のいずれかが必須。未設定時は ValueError を送出して誤った実行を防止。

Notes / Implementation details
- OpenAI モデルは gpt-4o-mini を使用する想定（モデル名は定数化）。
- ニュースウィンドウは JST ベースで定義され、内部は UTC naive datetime に変換して DB クエリに使う設計（ルックアヘッドバイアスを回避）。
- 多くの処理は「DuckDB 接続を受け取る」設計で、外部 API（発注等）にはアクセスしないため研究環境やローカル検証に適する。
- テスト容易性を考慮して、OpenAI 呼び出し箇所はパッチ差し替えが可能に実装。

Acknowledgements / Disclaimer
- 本 CHANGELOG は与えられたソースコードから推測して作成したものです。リリース日や文言は推測に基づいています。実際のリリースノート作成時は日付と内容を確認のうえ調整してください。