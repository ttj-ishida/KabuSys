# Keep a Changelog 準拠 CHANGELOG

すべての重要なリリース変更を記録します。フォーマットは Keep a Changelog に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

全般的な注意
- 本パッケージは DuckDB をデータストアとして想定し、openai（OpenAI Python SDK）を外部 API として利用します。
- 環境変数による設定管理を行います（必須のキーは README/.env.example を参照してください）。
- 設計方針として「ルックアヘッドバイアスを避ける」「外部 API の障害に対してフェイルセーフに振る舞う」「DB 書き込みは冪等性を重視する」等を採用しています。

Unreleased
- （なし）

[0.1.0] - 2026-03-29
Added
- 基本パッケージ構成
  - kabusys パッケージ初期版を追加。パッケージエクスポート: data, strategy, execution, monitoring（__all__）を定義。
  - バージョン: 0.1.0

- 設定管理（kabusys.config）
  - .env ファイルと環境変数を統合して読み込む自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env と .env.local の優先度ルールを実装（OS 環境変数 > .env.local > .env）。.env.local は上書き（override=True）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、クォート（シングル/ダブル）のエスケープ、行末コメント（空白直前の # をコメントと扱う）に対応。
  - 環境変数保護（既存の OS 環境変数を保護）を実装。
  - Settings クラスを提供し、主要な設定値をプロパティ経由で取得可能（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）。
  - 設定値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック、必須キー未設定時の ValueError）を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols からニュース記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを評価して ai_scores テーブルに保存する機能を実装。
  - ニュース収集ウィンドウは JST 基準で「前日 15:00 ～ 当日 08:30」を採用（UTC に変換して DB クエリに使用）。calc_news_window を提供。
  - API 呼び出しはバッチ処理（最大 20 銘柄／チャンク）で実行し、1 銘柄あたりの最大記事数および文字数を制限（トークン肥大化対策）。
  - OpenAI への呼び出しで 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他のエラーはスキップして処理継続するフェイルセーフ。
  - OpenAI の JSON Mode のレスポンスを厳密に検証（results 配列、code と score、スコアの数値性・有限性）。不正レスポンスは安全にスキップ。
  - スコアは ±1.0 にクリップして ai_scores に保存。DB 書き込みは対象コードのみを DELETE → INSERT して部分失敗時に既存データを保護。
  - テスト容易性のため OpenAI 呼び出しをラップしてモック差し替え可能（_call_openai_api を patch）。

- レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する機能を実装。
  - ma200_ratio の計算は target_date 未満のデータのみを使用することでルックアヘッドを防止（_calc_ma200_ratio）。
  - マクロニュースは news_nlp の calc_news_window と raw_news を用いてフィルタ（マクロキーワードリストに基づく）し、LLM で macro_sentiment を算出（_fetch_macro_news, _score_macro）。
  - OpenAI 呼び出しはリトライとフェイルセーフ（最終的に失敗した場合 macro_sentiment=0.0 を採用）。
  - レジームスコアの合成とクリッピング、閾値判定（bull / bear / neutral）を実装。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）を実装し、DB 操作失敗時には ROLLBACK を実施して例外を上位へ伝播。

- データ層（kabusys.data）
  - calendar_management: JPX カレンダー管理（market_calendar テーブル参照）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等を提供。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバックする一貫した挙動を実装。
    - calendar_update_job により J-Quants API（jquants_client）から差分取得 → 保存できる。
    - バックフィルや健全性チェック（将来日付の過度な偏差検出）をサポート。
  - pipeline: ETL パイプラインの基盤を実装。
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、バックフィル、品質チェック連携等の方針を実装するためのユーティリティ（_get_max_date 等）を実装。
    - API 呼び出し結果の保存は jquants_client の save_* を想定し、品質チェックは quality モジュールと連携する設計。

- 研究モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離）を計算。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio（20日平均等）を計算。
    - calc_value: PER（株価 / EPS）と ROE を raw_financials と prices_daily から計算（最新財務レコードの取得ロジックを実装）。
    - すべて DuckDB の prices_daily / raw_financials のみ参照する設計で、本番取引 API へのアクセスは行わない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）での将来リターン計算を実装（LEAD を利用した高速取得）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算するユーティリティを実装。データ不足時は None を返す。
    - rank: 同順位は平均ランクにするランク付け関数（丸めで ties 検出漏れ対策）。
    - factor_summary: 指定カラム群の count/mean/std/min/max/median を算出する統計サマリー関数。
  - 研究系関数は外部依存を抑え、標準ライブラリ＋DuckDB の SQL で実装。

Changed
- 初期リリースのため "Changed" の履歴はありません（0.1.0 で新規追加機能が主）。

Fixed
- 初期リリースのため "Fixed" の履歴はありません。

Removed
- 初期リリースのため "Removed" の履歴はありません。

Deprecated
- 初期リリースのため "Deprecated" の履歴はありません。

Security
- 現時点で特別なセキュリティ修正は記載なし。ただし、環境変数保護・必須キーチェック・外部 API キー注入の明示的取り扱いを行っています。

マイグレーションと互換性
- 0.1.0 は初回公開版のため、後続のリリースで API（関数署名、環境変数名、DB テーブル定義等）が変更される可能性があります。特に OpenAI レスポンスパースや DuckDB のバインド挙動（executemany と空リストの制約）などは将来のバージョンで変わる点に注意してください。

既知の設計上の振る舞い（重要）
- ルックアヘッドバイアス防止: すべての「日次」処理は内部で datetime.today() や date.today() を直接参照せず、必ず target_date を明示的に受け取る設計です。
- 外部 API 障害時: OpenAI 呼び出し失敗時は多くの箇所でフェイルセーフ（0.0 などの中立値）へフォールバックし、処理全体を停止させない方針です。
- DB 書き込みの冪等性: 置換操作（DELETE → INSERT）や ON CONFLICT 方針で部分失敗時に既存データを不必要に消さないよう配慮しています。

署名
- この CHANGELOG はコードの実装内容から推測して作成したもので、実際のリリースノートはリリース時の差分やドキュメントを優先してください。