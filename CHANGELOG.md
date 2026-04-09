CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-09
-------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0 を追加。
  - パッケージ構造:
    - kabusys: メインパッケージ。 __all__ に data / strategy / execution / monitoring を公開。
    - kabusys.config: 環境変数・設定管理（Settings クラス）を実装。
      - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
      - export KEY=val, クォート付き値（エスケープ対応）、行末コメントなどを適切にパースする堅牢な .env パーサ実装。
      - OS 環境変数を保護する protected キー概念、.env.local による上書きサポート、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
      - Settings によるプロパティ群（J-Quants / kabu API / LINE / DB パス / Paper Trading 設定 / 監視閾値 / システム env/log レベル 等）を提供。値検証（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）を実装。
    - kabusys.ai:
      - news_nlp: ニュースの NLP スコアリング機能を提供（score_news）。
        - 指定タイムウィンドウ（前日15:00 JST～当日08:30 JST）に基づく記事抽出（calc_news_window）。
        - 銘柄ごとに記事を集約し、バッチ（最大20銘柄）で OpenAI（gpt-4o-mini）へ送信、JSON モードでレスポンスを検証。
        - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ、レスポンスバリデーション、不正レスポンス時の安全なスキップ。
        - スコアの ±1.0 クリップ、取得成功銘柄のみ ai_scores テーブルに置換（DELETE → INSERT）して部分失敗時のデータ保護を実装。
        - テスト容易性のため _call_openai_api を差し替えられる設計。
      - regime_detector: 市場レジーム判定（score_regime）。
        - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily レジームを判定（bull / neutral / bear）。
        - DuckDB（prices_daily / raw_news / market_regime）を使用。LLM 呼び出しは OpenAI（gpt-4o-mini）、リトライ・バックオフ対応、API 失敗時は macro_sentiment = 0.0 のフェイルセーフ。
        - レジーム結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - kabusys.research:
      - factor_research: calc_momentum, calc_value, calc_volatility を実装。
        - Momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時は None）。
        - Volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
        - Value: PER・ROE（raw_financials から最新レコードを取得して計算）。
        - DuckDB SQL を用いた一貫した実装（prices_daily / raw_financials のみ参照）。
      - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装。
        - 将来リターンの一括取得クエリ（複数ホライズン対応）、Spearman（ランク相関）による IC 計算、統計サマリー。
        - pandas 等に依存せず標準ライブラリで実装。
      - 研究系ユーティリティ（zscore_normalize は kabusys.data.stats から再公開）。
    - kabusys.data:
      - calendar_management: JPX カレンダー管理機能を提供。
        - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API。
        - market_calendar が存在しない場合は曜日ベースのフォールバック（週末除外）を採用。
        - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新。バックフィル・健全性チェックを実装。
      - pipeline / etl:
        - ETLResult データクラス（ETL 実行の集約結果を表現）。
        - ETL 層設計方針を実装（差分更新、保存、品質チェックの組み込み）。jquants_client / quality と連携する想定。
      - etl モジュールは ETLResult を再エクスポート。
  - テスト支援:
    - 各所で API 呼び出し箇所（news_nlp/regime_detector）の内部 _call_openai_api 関数をテスト用にモック可能にしている。

Changed
- 設計方針として全 AI / 研究処理で「ルックアヘッドバイアスの排除」を徹底。
  - date.today() / datetime.today() を直接参照しない。target_date 引数に基づいて過去データのみを参照する実装。
- DuckDB とやり取りするトランザクション制御を明示的に実装（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK）し、部分失敗時の既存データ保護を考慮。
- OpenAI 呼び出しに対して堅牢なエラーハンドリング（5xx の再試行、非 5xx はスキップ）と JSON パース回復処理（前後余計なテキストを削る再パース）を導入。
- .env パーサの強化（クォート内のバックスラッシュエスケープ対応、コメントルールの解釈、export プレフィクス対応）。

Fixed
- ETL / ai スコア保存時の DuckDB executemany に関する互換性考慮:
  - DuckDB 0.10 の executemany が空リストを受け取れない点を回避するため、空チェックを追加して不要な呼び出しを避ける実装を追加。
- calendar_update_job における過剰な未来日チェック（_SANITY_MAX_FUTURE_DAYS）とバックフィル挙動を導入して、API 側の誤登録による異常な上書きを防止。
- 各種 null / 不完全データに対する耐性を強化（例: market_calendar の is_trading_day が NULL の場合のフォールバックと警告ログ）。

Security
- OpenAI API キーは関数引数または環境変数 OPENAI_API_KEY から取得する設計。キー未設定時は明確な ValueError を出して処理を中断することで誤使用を防止。
- .env 自動読込時は既存の OS 環境変数を保護する仕組みを実装。

Notes / Known limitations
- OpenAI SDK の将来の変更（例: 例外クラスや status_code の扱い）に対して一部防御コード（getattr を使った安全な status_code 参照）を入れているが、SDK 大幅変更時は見直しが必要。
- news_nlp / regime_detector は gpt-4o-mini を前提にプロンプトと JSON mode を設計しているため、別モデルや別フォーマットを使う場合はプロンプトやレスポンス検証ロジックの調整が必要。
- strategy / execution / monitoring の詳細実装はこのリリースでエクスポートの骨組みを用意（__all__ に含める）しているが、実装の追加・拡充は今後のリリースで行う予定。

以上。