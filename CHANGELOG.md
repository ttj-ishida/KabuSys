Changelog
=========
すべての重要な変更点をこのファイルに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠します。  
安定的なリリースのバージョニングは semver に従います。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-03
-------------------
初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装・公開します。

Added
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョンを 0.1.0 として公開。
  - public モジュール群を __all__ で宣言（data, strategy, execution, monitoring）。

- 環境設定管理
  - src/kabusys/config.py
    - .env/.env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
    - .env の行パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理等に対応。
    - 自動ロードの無効化は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で可能。
    - 必須環境変数取得ヘルパー _require() を提供（未設定時は ValueError）。
    - Settings クラス（settings インスタンス）を提供。J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定（env, log_level 等）等の各種プロパティを公開。
    - KABUSYS_ENV の妥当性チェックおよび LOG_LEVEL の妥当性検証を実装。

- AI（自然言語処理）機能
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）へバッチで送信して銘柄ごとのセンチメント ai_score を算出、ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（JST 前日15:00 ～ 当日08:30、内部は UTC naive）を実装（calc_news_window）。
    - バッチサイズ、1銘柄あたり記事/文字数上限、JSON-mode 応答の検証、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスバリデーションで予期しない形式を安全にスキップし、スコアを ±1.0 にクリップ。
    - 部分失敗時に既存スコアを保護するため、DELETE → INSERT の置換ロジックを実装（DuckDB の executemany の挙動を考慮して空リスト処理をガード）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みを行う。
    - マクロセンチメントは raw_news タイトルをマクロキーワードでフィルタし OpenAI により -1.0〜1.0 で評価（JSON 出力を期待）。
    - LLM 呼び出しは失敗時にフェイルセーフとして macro_sentiment=0.0 にフォールバック（例外を上げず継続）。
    - OpenAI 呼び出しは専用の内部ラッパーを用意し、モジュール間でプライベート関数を共有しない設計。
    - レトリースキーム・5xx 判定・ログ・ロールバックを備えた堅牢な DB 書き込み。

- 研究（Research）用ユーティリティ
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン / 200日 MA 乖離）、ボラティリティ（20日 ATR / 相対 ATR / 平均売買代金 / 出来高比）、バリュー（PER / ROE）などのファクター計算を実装。
    - DuckDB のウィンドウ関数を活用した SQL ベースの実装で、prices_daily / raw_financials のみ参照。データ不足時の None 返却により堅牢化。
    - 各関数は (date, code) をキーとする dict のリストを返す。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）をマルチホライズンで実装（デフォルト [1,5,21]）。
    - IC（Information Coefficient、Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を提供。
    - pandas 等に依存せず標準ライブラリのみで実装。ties の扱い・丸め対策を考慮。

- データプラットフォーム（Data）機能
  - src/kabusys/data/calendar_management.py
    - market_calendar テーブルに基づく営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録がない場合は曜日ベース（週末除外）でフォールバック。DB がまばらでも一貫性を保つよう実装。
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants から差分取得し save_market_calendar を呼ぶ）。
    - バックフィル、先読み、健全性チェック（未来日付の異常検出）をサポート。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラスを実装（取得・保存件数、品質問題、エラー等を格納、has_errors / has_quality_errors / to_dict を提供）。
    - 差分更新・バックフィル・品質チェックの方針を確定（jquants_client 経由の idempotent 保存・品質チェックは継続収集型）。

- パッケージ公開のための再エクスポート等
  - src/kabusys/data/__init__.py はデータサブパッケージの入口。pipeline.ETLResult を etl モジュールで再エクスポート。

Changed
- 設計上の方針を明確化（ソースドキュメント内）
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない実装方針を ai / research モジュールにて徹底。
  - OpenAI 呼び出しの失敗フェイルセーフ（スコア 0.0 でフォールバック）を明示。

Fixed
- （初回リリースのため該当なし、ただし実装上以下の互換性対策を反映）
  - DuckDB の executemany に空リストを渡すと失敗する挙動を考慮し、空チェックを導入して部分失敗時に既存データを保護するロジックを実装。

Security
- 重要な API キー/パスワードは環境変数によって注入（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY 等）。コード内でハードコードしない設計。

Notes / Migration / Requirements
- 必須環境変数
  - OPENAI_API_KEY: news_nlp.score_news / regime_detector.score_regime の呼び出し時に必要（api_key 引数でも注入可）。未設定時は ValueError を送出する仕様。
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等は Settings 経由で取得される（未設定時はエラー・デフォルト値の有無に注意）。

- 自動 .env 読み込み
  - パッケージインポート時にプロジェクトルートの .env / .env.local が自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env のパースは厳密な実装を行っており、クォートやエスケープ、インラインコメントに対処します。

- データベース / スキーマ前提
  - 以下のテーブルが期待されます: prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials, 等。スキーマは各機能の SQL クエリに依存します。
  - DuckDB を想定した実装（DuckDB のバージョン差異に配慮した実装パターンを一部導入）。

- タイムゾーン
  - news のウィンドウ計算などは JST ベースで定義し、DB との比較では UTC naive datetime（説明コメント参照）を使用。日時取り扱いに注意してください。

- テストフレンドリティ
  - OpenAI 呼び出しラッパー（_call_openai_api）を patch してテストを行える設計になっています。

Known Limitations / TODO
- 一部のファクションは外部 API（OpenAI / J-Quants）に依存するため、実行にはネットワーク接続と有効な API キーが必要。
- news_nlp と regime_detector は別々の _call_openai_api 実装を持ち、重複があるがモジュール結合を避ける設計意図あり。将来的に共通クライアントやユーティリティに整理する余地あり。
- Strategy / execution / monitoring の具象実装は本リリースでは公開インターフェースのみ（__all__ に含む）。今後のリリースで取引ロジック・発注実装等を追加予定。

Acknowledgements
- 初期実装における多くの設計注釈（ルックアヘッド回避、部分失敗時のデータ保護、外部 API の堅牢性）がソース内ドキュメントとして残されています。運用前に README と DataPlatform/Strategy ドキュメントの参照を推奨します。