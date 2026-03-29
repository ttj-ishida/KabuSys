# CHANGELOG

全ての変更は Keep a Changelog の形式に従います。  
このファイルはコードベース（初期リリース v0.1.0）から推測して生成した変更履歴です。

## [0.1.0] - 2026-03-29

初回公開リリース。

### 追加
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。

- 設定/環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定して自動ロードを無効化可能。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理対応）。
  - OS側の既存環境変数を保護するため protected set を用いる上書きロジックを導入。
  - 必須環境変数取得ヘルパー _require を提供（未設定時は明確な ValueError を送出）。
  - アプリケーション設定 Settings クラスを追加し、以下の設定取得プロパティを実装:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（validation: development/paper_trading/live）
    - LOG_LEVEL（validation: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live/is_paper/is_dev ヘルパー

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を算出。
    - ニュース収集ウィンドウの計算（JST 基準で「前日 15:00 JST 〜 当日 08:30 JST」）を calc_news_window で実装（UTC naive datetime を返す）。
    - バッチ処理: 1回あたり最大 20 銘柄（_BATCH_SIZE=20）、銘柄ごとの最大記事数 10 件、テキストは 3000 文字にトリム。
    - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの厳密なバリデーションを実装（results 配列・code/score 検証、±1.0 にクリップ）。
    - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対して指数バックオフ、最大試行回数設定）。
    - 取得したスコアは ai_scores テーブルへ冪等的に（DELETE → INSERT）保存、部分失敗時に他銘柄の既存スコアを保護。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）に対する 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（'bull'/'neutral'/'bear'）を実施。
    - MA200 乖離の計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
    - マクロニュース収集は news_nlp.calc_news_window を利用してウィンドウを決定、最大 20 件までのタイトルを LLM に渡す。
    - LLM 呼び出しは gpt-4o-mini を使用、リトライ/バックオフを実装。API 失敗時は macro_sentiment=0.0 でフォールバックするフェイルセーフ。
    - 最終的な regime_score を計算（スケーリング・クリップ）し market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時はロールバック処理を行う。

- データ処理（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを追加（処理対象日、取得数・保存数、品質チェック結果、エラー一覧を保持）。
    - 差分更新・バックフィル方針や品質チェックの扱いに関する方針を実装。
    - DuckDB ベースのユーティリティ関数（テーブル存在確認、最大日付取得）を追加。
  - ETL インターフェース公開（kabusys.data.etl）: ETLResult を再エクスポート。
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API を実装。
    - market_calendar がない場合は曜日ベース（土日非営業）でフォールバックする堅牢なロジック。
    - calendar_update_job を実装し J-Quants API から差分取得 → market_calendar に冪等保存（バックフィル、先読み、健全性チェックを実施）。
    - max search 範囲を設定して無限ループを防ぐ実装。
    - DuckDB の日付型を安全に date オブジェクトに変換するユーティリティを提供。

- 研究/ファクター（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高変化率）およびバリュー（PER、ROE）を DuckDB の prices_daily / raw_financials から計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 扱い、SQL ウィンドウ関数を活用した実装。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）: ホライズン引数のバリデーション、1 クエリで複数ホライズンを取得する効率的実装。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンの順位相関をランクで計算（ties は平均ランク処理）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）を追加。
  - これらユーティリティは外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

### 変更
- ログ出力/診断
  - 各モジュールで詳細な logger.debug / logger.info / logger.warning を追加し、処理状況・フェイルセーフ処理を明示。
- テスト性の改善
  - OpenAI 呼び出しを行う内部ヘルパーを外から patch 可能にして単体テストを容易にする設計（news_nlp._call_openai_api / regime_detector._call_openai_api）。

### 修正（設計/堅牢性）
- ルックアヘッドバイアス対策
  - news_nlp, regime_detector, research 等のモジュールで datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計とした。
- DB 書き込みの冪等性
  - ai_scores, market_regime などへの書き込みは DELETE → INSERT または ON CONFLICT 相当で実装し、部分失敗時に既存データを保護。
  - DuckDB の executemany が空リストを受け取れない制約に対応するため、事前チェックを追加。
- OpenAI API エラー処理
  - RateLimit/接続/タイムアウト/5xx を考慮したリトライ実装、非 5xx の APIError は再試行せずフォールバックする方針を明記。

### 注意事項 / 既知の制約
- OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY により供給する必要がある。未設定時は ValueError を送出。
- 一部ロジックは J-Quants クライアント（kabusys.data.jquants_client）に依存する（実装は別モジュールで提供される想定）。
- model は gpt-4o-mini を想定（将来の変更に対して設定化の余地あり）。
- 現時点では PBR や配当利回り等の一部バリューファクターは未実装。
- DuckDB 周りはバージョン依存の振る舞い（list 型バインド等）に注意が必要。

---

この CHANGELOG は現行コードの構造・コメント・設計方針から推測して作成しています。実際の変更履歴やリリースノートとして利用する場合は、該当コミット/チケット情報と照合のうえ必要に応じて修正してください。