CHANGELOG
=========

All notable changes to this project will be documented in this file.

The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

[0.1.0] - 2026-03-27
--------------------

Added
- 初回リリースとして基幹モジュールを追加。
  - パッケージ公開: kabusys.__init__ による主要サブパッケージのエクスポート（data, research, ai, ...）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルート検出は .git / pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装: export 先頭表記、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - override / protected を用いた上書き制御（OS環境変数保護）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /環境モード /ログレベル等のプロパティを公開。KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約し、銘柄毎に OpenAI (gpt-4o-mini・JSON Mode) へバッチでセンチメントを要求。
    - チャンク処理（デフォルト20銘柄）、1銘柄あたり記事トリム制限（記事数・文字数）を実装。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、失敗時フォールバック（部分失敗でも他コードを保護して DB を更新）。
    - リトライ（429・ネットワーク・タイムアウト・5xx）と指数バックオフを実装。
    - テスト時に置換可能な _call_openai_api フックを用意。
    - calc_news_window（JST 帳尻: 前日15:00～当日08:30 の UTC 変換）を提供。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日MA乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（bull/neutral/bear）。
    - マクロニュース抽出、OpenAI 呼び出し、合成スコアのクリップ、冪等な market_regime への書き込みを実装。
    - API エラー時は macro_sentiment=0 のフェイルセーフ、リトライ処理を実装。
- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比を計算（window バッファあり）。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算（最新財務レコードを採用）。
  - feature_exploration:
    - calc_forward_returns: 任意のホライズンで将来リターンを計算（入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装（有効レコードが少ない場合は None）。
    - factor_summary / rank: ファクターの統計サマリーとランク付けユーティリティを提供。
  - 実装方針: DuckDB 接続を受け取り SQL と標準ライブラリで完結（外部依存を極力排除）。
- Data モジュール (kabusys.data)
  - calendar_management:
    - market_calendar を基にした営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未取得時は曜日ベースのフォールバック。最大探索日数で無限ループを防止。
    - calendar_update_job により J-Quants から差分取得・バックフィル・健全性チェック・冪等保存を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（取得/保存レコード数・品質問題・エラーの集約・to_dict）。
    - 差分更新ロジック、バックフィル、品質チェック収集の設計を反映。
  - etl 公開インターフェース: ETLResult を再エクスポート。
- 共通の設計方針
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を内部ロジックで参照せず、target_date を明示的に受け取る実装。
  - DuckDB の挙動（executemany の空リスト不可等）に対する互換性考慮。
  - DB 書き込みは基本的に冪等操作（DELETE→INSERT / ON CONFLICT 相当）で実装し、部分失敗の際に既存データを保護。

Fixed / Reliability improvements
- OpenAI 呼び出し回りの堅牢化:
  - レスポンスパース失敗時に JSON の外側テキストをトリムして復元を試みるフォールバック。
  - LLM が整数でコードを返しても対応するため code を文字列化して比較。
  - APIError の status_code 有無に依存せず安全に 5xx 判定を行いリトライ制御。
- ニュース集約とスコア保存の堅牢化:
  - 1銘柄あたりのトークン/文字数対策、最大記事数制限。
  - 部分成功時に対象銘柄のみ削除→挿入することで既存スコアを保護。
- DuckDB / 日付処理の堅牢化:
  - DuckDB から返る日付値を安全に date オブジェクトへ変換するユーティリティを用意。
  - market_calendar の NULL 値や未登録日に対するログ出力とフォールバック動作を明確化。

Removed
- なし（初回リリース）

Security
- 環境変数周りは OS 環境を protected として上書きから保護する仕組みを実装。
- OpenAI API キーは引数で注入可能（テスト時の差し替え／CI環境対策）で、未設定時は ValueError を返して明示的に扱う。

Notes / 要件
- OpenAI SDK（OpenAI クライアント）および duckdb が必要。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON mode を使用する設計。
- 実行に必要な主要環境変数の例:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等。
- 本リリースは「データ処理・リサーチ・AI スコアリング」領域の基礎実装を提供するもので、
  実取引（execution）や監視（monitoring）の実装は別モジュールとして分離される想定。

-----