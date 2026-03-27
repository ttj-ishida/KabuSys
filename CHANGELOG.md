# Changelog

すべての注目すべき変更点を記載します。フォーマットは "Keep a Changelog" に準拠しています。

全般
- 本リポジトリの初期バージョンを記録します。バージョン番号はパッケージ定義（src/kabusys/__init__.py）の __version__ に合わせて 0.1.0 としています。

[Unreleased]
- （今後の変更記録用）

[0.1.0] - 2026-03-27
=================================

Added
- パッケージの初期実装（kabusys 0.1.0）。以下の主要機能・モジュールを実装・公開。
  - 基本情報
    - パッケージ名: KabuSys - 日本株自動売買システム（src/kabusys）。
    - __all__ による公開: data, strategy, execution, monitoring（将来的に各サブパッケージを提供予定）。
  - 環境変数 / 設定管理（src/kabusys/config.py）
    - .env/.env.local 自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
    - .env のパース実装（コメント・export prefix・クォートとバックスラッシュのエスケープ等に対応）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等の用途向け）。
    - 環境値をラップする Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / env/log レベル等）。未設定時の必須チェック（ValueError）や列挙値検証を実装。
    - デフォルトの DB パス: DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db。
  - AI（自然言語処理）モジュール（src/kabusys/ai）
    - ニュースセンチメント（news_nlp.py）
      - raw_news と news_symbols を元に銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini の JSON Mode）にバッチ送信して銘柄別スコアを生成。
      - 時間ウィンドウは前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリ）を採用。calc_news_window ユーティリティを提供。
      - バッチ処理: 1APIコールあたり最大 20 銘柄（_BATCH_SIZE）、1銘柄あたり最大 10 記事・3000 文字までトリム。
      - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。その他エラーはスキップして継続（フェイルセーフ）。
      - レスポンスバリデーションを厳密化（JSONパース、"results" リスト、コード存在確認、数値判定、±1.0 でクリップ）。部分成功時は該当銘柄のみ置換（DELETE → INSERT）して既存データ保護。
      - DuckDB の executemany の互換性を考慮し、空リストの場合は executemany を呼ばない安全策を実装。
      - score_news(conn, target_date, api_key=None) を公開。返り値は書き込んだ銘柄数。
    - 市場レジーム判定（regime_detector.py）
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を実装。
      - ma200 計算は target_date 未満のデータのみ使用し、ルックアヘッドバイアスを防止。
      - マクロ記事はマクロキーワードでフィルタして取得（最大 20 件）。LLM 呼び出しは JSON モードで実施、失敗時は macro_sentiment=0.0 にフォールバック。
      - API 呼び出しはリトライ/バックオフに対応。DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
      - score_regime(conn, target_date, api_key=None) を公開。成功時は 1 を返す。
  - リサーチ（src/kabusys/research）
    - factor_research.py
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER/ROE）を DuckDB の SQL と組み合わせて計算する関数を実装。
      - 欠損・データ不足時の挙動（例えば MA200 未満のデータで None を返す等）を明確化。
      - calc_momentum / calc_volatility / calc_value を提供し、date/code をキーとする dict のリストを返す。
    - feature_exploration.py
      - 将来リターン算出（calc_forward_returns）: 指定ホライズン（デフォルト [1,5,21]）の将来終値からリターンを算出。ホライズンの妥当性チェック（正の整数かつ <=252）。
      - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装。サンプル不足時は None を返す。
      - rank(): 同順位は平均ランクとする実装（丸めで ties 検出を安定化）。
      - factor_summary(): 基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで計算（pandas 等非依存）。
    - research パッケージで zscore_normalize を data.stats から再エクスポート。
  - データ管理（src/kabusys/data）
    - calendar_management.py
      - JPX マーケットカレンダー管理（market_calendar テーブル）に基づく営業日判定ユーティリティを提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等で更新（バックフィルと先読み、健全性チェックを実装）。
      - カレンダー未取得時は曜日ベースのフォールバック（週末は休場）を採用。DB に登録済みの値を優先。
      - 最大探索日数制限（_MAX_SEARCH_DAYS）等の保護ロジックを実装。
    - ETL / パイプライン（pipeline.py, etl.py）
      - ETLResult データクラスを実装（取得件数・保存件数・品質問題リスト・エラーリスト等を保持）。data/etl モジュールで ETLResult を公開。
      - 差分取得・保存・品質チェックのフローに対応するユーティリティを一部実装。jquants_client との連携を想定（fetch/save 呼び出し）。
      - デフォルトのバックフィル日数やカレンダールックアヘッドなどの定数を定義。品質チェックの重大度（error）判定ユーティリティを実装。
  - その他
    - 各モジュールで「ルックアヘッドバイアス防止」の方針を採用（datetime.today()/date.today() を直接参照しない設計、target_date に基づく処理）。
    - DuckDB との互換性を考慮した実装（executemany の空リスト回避、日付変換ユーティリティ _to_date 等）。
    - OpenAI SDK の異常系（RateLimitError / APIConnectionError / APITimeoutError / APIError）に対する取り扱いを明確化。

Changed
- 初回リリースのためなし（初期導入）。

Fixed
- 初回リリースのためなし。

Deprecated
- 初回リリースのためなし。

Removed
- 初回リリースのためなし。

Security
- 初回リリースのため特記事項なし。ただし、OpenAI API キーや各種シークレットは Settings を通して環境変数で管理するよう設計。自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

Notes / Known limitations
- PBR や配当利回りなどのバリューファクターは現バージョンでは未実装（calc_value に注記あり）。
- AI モジュールは OpenAI の JSON Mode を利用する想定（gpt-4o-mini）。API レスポンスの不確実性に対処するためパース失敗はスキップ・フェイルセーフで処理するが、品質向上のため将来的に追加検証やリトライ方針の微調整が必要。
- strategy / execution / monitoring パッケージの中身はこのリリース時点で最小限の公開のみ（将来的に発注ロジックや監視連携を追加予定）。

参考（実装上の設計ポリシー）
- ルックアヘッドバイアス防止: すべてのバッチ処理で target_date を明示的に受け取り、DB クエリは target_date 未満 / 以前のデータのみを参照する実装を心がけています。
- フェイルセーフ設計: 外部 API 失敗時はスコアを 0.0（中立）にフォールバックする等、運用中の致命的停止を避ける方針です。
- DuckDB 互換性: executemany の挙動や日付型扱いなど実環境の差異を考慮した実装を行っています。

もし CHANGELOG に追加したい別の観点（セキュリティ、互換性、移行手順、リリースパッケージサイズなど）があれば教えてください。必要に応じて日付・カテゴリの調整や詳細説明の追記を行います。