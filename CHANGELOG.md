# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、Semantic Versioning を使用します。  
このファイルはコードベースの内容から推測して作成しています。

## [0.1.0] - 2026-03-31

Added
- 初回リリース（パッケージ名: kabusys）。
- パッケージ公開 API:
  - kabusys.__init__ でのバージョン管理（__version__ = "0.1.0"）と主要サブパッケージのエクスポート: data, strategy, execution, monitoring。
- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルート判定: .git または pyproject.toml）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装（コメント・export プレフィックス・クォート内のエスケープ対応）。
  - Settings クラスで主要設定値をプロパティとして提供（J-Quants, kabuステーション, Slack, DBパス, 環境/ログレベル判定等）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL）と必須項目チェック（_require）。
- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成。
    - タイムウィンドウ定義（JST 前日 15:00 ～ 当日 08:30、内部は UTC naive で扱う）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（チャンクサイズ: 最大 20 銘柄）。
    - 出力は JSON モード期待、レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装（デフォルト最大リトライ回数）。
    - DuckDB へ冪等的に書き込む処理（DELETE → INSERT、部分失敗時の保護のため対象コードのみ操作）。
    - 公開関数: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。APIキー未設定時は ValueError。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して 'bull'/'neutral'/'bear' 判定。
    - マクロニュース抽出はマクロキーワード群でフィルタ（最大 20 記事）。
    - OpenAI（gpt-4o-mini）呼び出しとリトライ・フェイルセーフ（失敗時は macro_sentiment=0.0）。
    - レジームスコアを market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - 公開関数: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。APIキー未設定時は ValueError。
- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定ユーティリティ群:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - カレンダーデータ未取得時は曜日ベースのフォールバック（週末 = 非営業日）を使用。
    - calendar_update_job: J-Quants API からの差分取得 → market_calendar へ冪等保存、バックフィルと健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスで ETL 実行結果を集約（取得数・保存数・品質問題・エラー等）。
    - 差分取得ロジック、バックフィル、品質チェック（quality モジュール利用）を考慮した設計。
    - DuckDB を主要なストレージ/問い合わせバックエンドとして利用。
    - jquants_client を通じた API 呼び出し抽象化（fetch/save 系は外部クライアントに委譲）。
- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials を用いた PER / ROE 計算（報告日以前の最新財務を使用）。
    - 各関数は prices_daily / raw_financials のみ参照し、結果は (date, code) キーの dict リストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（不足データや ties を考慮）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクとするランク付けユーティリティ。
- 共通設計上の注意点（ドキュメント化されている挙動）
  - ルックアヘッドバイアス回避のため、いずれの処理も datetime.today()/date.today() を内部参照せず、target_date を明示的に受け取る設計。
  - OpenAI API 呼び出しは JSON パースや API エラーに対して堅牢にフォールバック（フェイルセーフ：例外を上位に伝播させずスコア 0.0 など）。
  - DuckDB による SQL 処理と冪等性（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK）を重視。
  - テスト容易性のため、OpenAI 呼び出し箇所はモック差し替えを想定した設計（内部 _call_openai_api の差替え等）。
  - ロギングを各処理に組み込み、警告・情報ログを出力。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- OpenAI API キー等の機密は Settings を通じて環境変数で管理。パスワードトークン等は明示的に必須プロパティとして扱い、未設定時は ValueError を発生させることで誤動作を防止。

Notes（補足）
- OpenAI の使用箇所はモデル名 gpt-4o-mini を想定している（news_nlp と regime_detector）。
- ニュースタイムウィンドウは JST 基準で定義され、内部では UTC naive datetime に変換して DB クエリに使用する実装。
- DuckDB バインド時の互換性を考慮し、executemany に空リストを渡さないガード等が実装されている。
- .env パーサは export プレフィックス・クォート内エスケープ・インラインコメント処理等を考慮した実装になっている。

--- 

（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース差分を基に調整してください。）