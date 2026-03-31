CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。
リリース日はソースコードのスナップショット作成日です。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-31
------------------

Added
- 初回公開: kabusys パッケージの基礎機能を実装。
  - パッケージ構成:
    - kabusys.config: 環境変数/設定管理
      - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - .env パーサは export 形式やクォート、エスケープ、行内コメント処理に対応。
      - OS 環境変数を保護する protected 機構（.env.local の override 時にも考慮）。
      - Settings クラスを公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL のデフォルト, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV と LOG_LEVEL のバリデーション、is_live/is_paper/is_dev ユーティリティ）。
      - 必須環境変数未設定時は ValueError を送出する _require 実装。
  - kabusys.ai モジュール:
    - news_nlp:
      - 指定ターゲット日に対するニュース収集ウィンドウ計算（JST→UTC変換）。
      - raw_news と news_symbols から銘柄ごとに記事集約（件数/文字数でトリム）。
      - OpenAI（gpt-4o-mini、JSON mode）を用いたバッチセンチメント評価（1 API 呼び出しあたり最大 20 銘柄）。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他エラーはスキップするフォールバック動作。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造、既知コードのみ採用、数値チェック、±1.0 クリップ）。
      - 成功した銘柄のみを対象に ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT、DuckDB の executemany 空リスト制約に配慮）。
      - ルックアヘッドバイアス防止設計（内部で date.today() を参照しない）。
    - regime_detector:
      - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）の線形合成で市場レジーム（bull/neutral/bear）を日次判定。
      - prices_daily と raw_news を参照して ma200_ratio とマクロ記事タイトルを収集。
      - OpenAI 呼び出しは独立実装（モジュール間結合を避ける）。
      - API 呼び出し失敗時は macro_sentiment を 0.0 にフォールバックして継続（フェイルセーフ）。
      - 冪等な market_regime テーブルへの書き込み（BEGIN / DELETE / INSERT / COMMIT）と例外時の ROLLBACK 保護。
  - kabusys.data モジュール:
    - calendar_management:
      - market_calendar を元にした営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
      - DB 登録がない日や NULL 値に対して曜日ベースのフォールバックを一貫して使用。
      - カレンダーの夜間バッチ更新 job（calendar_update_job）を実装。J-Quants から差分取得して保存、バックフィルおよび健全性チェックあり。
    - pipeline / etl:
      - ETLResult データクラスを実装・公開（取得数/保存数/quality_issues/エラー収集など）。
      - 差分更新・バックフィル・品質チェック方針の設計を反映。
      - DuckDB の日付最大取得補助等ユーティリティを実装。
    - etl: pipeline.ETLResult を再エクスポート。
  - kabusys.research モジュール:
    - factor_research:
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER、ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
      - DuckDB SQL を主体とした実装で、prices_daily / raw_financials のみ参照。データ不足時は None を返す等の扱いを明示。
    - feature_exploration:
      - 将来リターン計算（calc_forward_returns、任意ホライズン対応）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
      - pandas 等外部ライブラリに依存しない純標準ライブラリ実装。
    - research パッケージ __all__ で主な関数を公開（zscore_normalize を data.stats から利用）。
  - パッケージ初期化:
    - kabusys.__init__ にて __version__="0.1.0"、公開サブパッケージを定義。

Security
- OpenAI API キーなどの機密情報は Settings 経由で環境変数から取得する設計。必須変数が未設定の場合は明示的にエラーを返します。

Notes / Known limitations
- OpenAI を使う機能（ai.news_nlp, ai.regime_detector）は OPENAI_API_KEY（または api_key 引数）の設定を必須とする。未設定時は ValueError を送出。
- DuckDB 固有の挙動（executemany に空リストを渡せない等）に配慮した実装を行っているため、古い DuckDB バージョン使用時の注意点がある可能性あり。
- JSON Mode を利用するためレスポンスパースに特殊ケース（前後に余計なテキストが混在）への耐性を持たせているが、LLM 出力のバリエーションによりパース失敗が起きる可能性は残る。パース失敗時はログを出し当該チャンク/記事はスキップする設計（例外は上げない）。
- .env パーサは shell 風の記法（export、引用、エスケープ、行内コメント）に対応するが、極端に複雑な .env 内容では想定外の挙動が起きる可能性がある。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Acknowledgements / Implementation notes
- DuckDB をデータストアとして広く利用する設計（SQL + ウィンドウ関数多用）。
- ルックアヘッドバイアス防止のため、内部処理は target_date 未満／<= のデータ選択や外部現在時刻参照を避ける方針を採用。
- OpenAI SDK の例外型（RateLimitError, APIConnectionError, APITimeoutError, APIError）を考慮した堅牢なリトライ設計を実装。

今後の予定（例）
- ai モジュールのテスト補強（モック用フックは一部用意済み）。
- ETL の品質チェックルール拡張と監査ログ出力の強化。
- PBR・配当利回り等のバリューファクターの追加実装。