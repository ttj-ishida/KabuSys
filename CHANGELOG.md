CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。
日付はリリース日を示します。

[Unreleased]
-------------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回公開: kabusys パッケージ v0.1.0 リリース。
  - パッケージ概要: 日本株自動売買プラットフォーム用のデータ取得・ETL、研究（ファクター計算）、AI を用いたニュース解析／レジーム判定、カレンダー管理などのユーティリティ群を提供。
  - モジュール構成（主なもの）:
    - kabusys.config
      - .env ファイルおよび環境変数からの設定自動読み込み（プロジェクトルート検出: .git / pyproject.toml）。
      - 高機能な .env パーサ実装（export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い等に対応）。
      - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - Settings クラスにより必須変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）とデフォルト値の提供（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）。
      - KABUSYS_ENV / LOG_LEVEL の値検証ロジック（許容値チェック）。
    - kabusys.data
      - calendar_management: JPX カレンダーの管理（market_calendar テーブルの読み書き、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、calendar_update_job）。
        - DB にデータがない場合は曜日ベースのフォールバックを使用。
        - カレンダー先読み／バックフィル／健全性チェックを実装。
      - pipeline / etl: ETLResult データクラスと差分取得・保存・品質チェックのためのユーティリティ（DuckDB ベース）。
        - DuckDB のテーブル存在チェックや最大日付取得ロジックを提供。
        - ETL 実行結果のシリアライズ（to_dict）をサポート。
      - jquants_client との連携を想定した差分フェッチ／保存インターフェース設計（実装は外部モジュール想定）。
    - kabusys.ai
      - news_nlp.score_news
        - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメント（ai_score）を取得し ai_scores テーブルへ保存。
        - 時間ウィンドウ（前日15:00 JST ～ 当日08:30 JST）を calc_news_window で計算。
        - バッチ（最大20銘柄）での API 呼び出し、1銘柄当たり記事数/文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）によるトリム。
        - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
        - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。フェイルセーフとして失敗時は該当チャンクをスキップし続行。
        - DuckDB 0.10 の executemany 空パラメータ制約に配慮した安全な DELETE → INSERT フロー。
      - regime_detector.score_regime
        - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
        - OpenAI 呼び出しは独立実装とし、モジュール間結合を避ける設計。API キー注入可能。
        - データ不足時や API 失敗時の明示的フォールバック（例: ma200 データ不足 → 中立、API失敗 → macro_sentiment=0.0）。
        - 冪等性を保った DB トランザクション（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK のロギング。
    - kabusys.research
      - factor_research: calc_momentum / calc_volatility / calc_value
        - モメンタム（1M/3M/6M）、200 日 MA 乖離、20 日 ATR、流動性指標、財務指標（PER, ROE）などのファクター計算を DuckDB 上の SQL と Python の組み合わせで実装。
        - データ不足に対する None 扱い、ログ出力、スキャン範囲バッファを考慮。
      - feature_exploration: calc_forward_returns / calc_ic / rank / factor_summary
        - 将来リターン（任意ホライズン）、スピアマン IC（ランク相関）、統計サマリー等の実装。外部ライブラリに依存しない純標準ライブラリ実装。
      - research パッケージの __all__ による主要 API の再エクスポート（zscore_normalize を含む）。
  - パッケージメタ情報: __version__ = "0.1.0" を設定。

Changed
- N/A（初回リリースのため比較対象なし）。

Fixed / Robustness
- OpenAI API 呼び出し時の回復力強化:
  - RateLimitError / APIConnectionError / APITimeoutError / 5xx を対象にリトライ（指数バックオフ）。
  - 非 5xx の APIError や JSON パース失敗はフェイルセーフとしてスコア 0.0 を返す（例外を上位に伝播させない）。
  - JSON Mode でも余分な前後テキストが混入するケースを考慮し、最外の {} を抽出して復元する処理を追加。
- DuckDB との互換性: executemany に空リストを渡せないバージョンに配慮したガード（params の有無を確認してから executemany を呼ぶ）。
- 日付／時間の扱いに関するバイアス防止:
  - 各 AI / 研究関数は datetime.today() / date.today() を直接参照せず、呼び出し側が target_date を渡す設計にしてルックアヘッドバイアスを防止。
- トランザクションの失敗時に ROLLBACK を試み、ROLLBACK 失敗時は警告ログを出力。

Security
- Settings にて必須環境変数が未設定の場合に ValueError を発生させることで、実行時に明確なエラーを出す（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
- 環境変数読み込み時、OS 環境変数を保護するメカニズム（protected set）を導入。

Misc
- テスト容易性: OpenAI 呼び出しを行う内部関数（_call_openai_api）をパッチして差し替え可能にしている（unittest.mock.patch でモック可能）。
- ロギング: 各モジュールで詳細なログ出力を追加し、処理状況やフォールバック理由を記録。

Deprecated
- なし

Removed
- なし

Notes / Known limitations
- 実際の外部 API クライアント（jquants_client 等）や DB スキーマ定義は別モジュール／実行環境での提供を前提としている。
- OpenAI の利用は API キーが別途必要。API 利用時の料金・レート制限に注意。
- 本バージョンは主要ロジックを実装した初期版のため、運用前に小規模データでの検証と設定（.env、DB スキーマ）確認を推奨。

-----