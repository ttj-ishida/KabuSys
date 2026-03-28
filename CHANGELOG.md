# Changelog

すべての重要な変更をここに記録します。フォーマットは "Keep a Changelog" に準拠しています。  
リリースは語彙的に安定したリリース単位で記載しています。

全般
- リリース方針: バージョンは package の __version__ に従います（現行: 0.1.0）。
- 日付: 2026-03-28

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 環境設定 / 設定管理（kabusys.config）
  - .env/.env.local 自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env を読み込む（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - OS 環境変数は protected として上書きを防止（.env.local は override=True で読み込むが OS 変数を保護）。
  - .env パーサーは export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いに対応。
  - Settings クラスを提供（settings インスタンスで使用）。
    - 必須環境変数チェック: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等。
    - DB パス設定（DUCKDB_PATH, SQLITE_PATH）と Path 型での取得。
    - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）。
    - ヘルパー: is_live / is_paper / is_dev プロパティ。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー管理: market_calendar テーブル参照／夜間バッチ更新ジョブ（calendar_update_job）。
    - 営業日判定/取得ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダーがない場合は曜日ベースのフォールバック（週末を非営業日と判断）。
    - 最大探索日数等の安全制約を実装（無限ループ防止）。
  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（etl モジュール経由で再エクスポート）。
    - 差分取得、バックフィル、品質チェックの設計を反映。
    - DuckDB のテーブル存在チェック、最大日付取得などのユーティリティ実装。
    - ETL 結果に品質問題（quality.QualityIssue）とエラーの集約機能を実装。

- 研究・ファクター（kabusys.research）
  - factor_research モジュール:
    - モメンタムファクター calc_momentum（1M/3M/6M、ma200_dev）。
    - ボラティリティ/流動性 calc_volatility（ATR20、相対ATR、平均売買代金、出来高比率）。
    - バリュー calc_value（PER, ROE。raw_financials から最新の財務データを参照）。
    - DuckDB ベースの SQL 実装で、(date, code) ベースの結果リストを返す。
  - feature_exploration モジュール:
    - calc_forward_returns（任意ホライズンの将来リターンを一括で取得）。
    - calc_ic（スピアマンランク相関に基づく IC 計算）。
    - rank（同順位は平均ランクで扱うランク関数）。
    - factor_summary（count/mean/std/min/max/median の統計サマリー）。
  - research パッケージ初期公開に伴い、研究用途の関数群をエクスポート（zscore_normalize は data.stats から再エクスポート）。

- AI 関連（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を集約して銘柄ごとに記事をまとめ、OpenAI（gpt-4o-mini）を用いてセンチメント（ai_score）を生成。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の記事を対象）を calc_news_window として提供。
    - バッチ送信（最大 _BATCH_SIZE=20 銘柄/コール）、記事トリム（_MAX_ARTICLES_PER_STOCK=10, _MAX_CHARS_PER_STOCK=3000）。
    - レスポンス検証（JSON mode を利用、レスポンスのパースと妥当性チェックを厳格に実施）。
    - エラー処理: 429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライ、それ以外はスキップ。失敗時は部分的にスコアを保護して DB 書き換え（DELETE→INSERT）を実行。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と news_nlp によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しを行い、API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームのスコア計算と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - 共通設計:
    - OpenAI の呼び出しは専用の内部関数でラップし、テスト時に差し替え可能（unittest.mock.patch が想定される点）。
    - API 呼び出しは JSON mode を使用し、厳格なレスポンス検証を行う。

Changed
- 初版のため互換性に関する変更履歴はなし。

Fixed
- 初版のためバグ修正履歴はなし。

Notes / Design decisions
- ルックアヘッドバイアス対策:
  - AI モジュール（news_nlp / regime_detector）は datetime.today() / date.today() を内部処理で参照せず、ターゲット日を引数で受け取る設計。
  - DB クエリは target_date より前（排他条件）を使うなど、将来データを参照しない工夫を行っている。
- DuckDB 互換性:
  - executemany に空リストを渡さない、安全な実装（DuckDB 0.10 への配慮）。
  - 日付型の取り扱いで str→date の変換（互換性向上）。
- フォールバック / フェイルセーフ:
  - OpenAI API の不安定性を考慮して、API エラー時は処理を継続し部分的な結果を保持する（例: macro_sentiment=0.0, スコア未取得コードは保持）。
  - market_calendar 未取得時は曜日ベースのフォールバックを行う（安全性重視）。

未実装 / TODO（明示的に記載されている点）
- research.factor_research の PBR・配当利回りの計算は未実装（注記あり）。
- monitoring モジュールは __all__ に含まれるが、該当実装は今回のスニペットには含まれていません（今後追加予定）。

開発者向けメモ
- テストしやすさのため、OpenAI 呼び出し箇所は _call_openai_api を patch することで簡単にモックできます。
- .env の自動ロードは配布後や CI 環境で副作用を避けたい場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

これが初期リリース（0.1.0）の主要な変更点・設計方針の要約です。必要であれば各モジュールごとの公開 API、関数一覧、使用例（短いコードスニペット）を追記します。どの情報を追加しますか？