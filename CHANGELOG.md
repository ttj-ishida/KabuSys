Keep a Changelog
=================
すべての変更はセマンティック バージョニングに従って記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-29
--------------------

Added
- 初期リリース。パッケージ名: kabusys, バージョン 0.1.0 を追加。
- パッケージ構成:
  - kabusys (パッケージエントリ: __version__ = "0.1.0", __all__ でサブパッケージを公開)
  - サブモジュール: data, research, ai, monitoring（公開リストに含む）

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local および OS 環境変数からの自動読み込みを実装。
  - プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
  - .env パーサーは以下をサポート:
    - 空行・コメント行（#）を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォートなしでのインラインコメント処理（直前がスペース/タブの場合）
  - .env と .env.local の読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途を想定）
  - Settings クラスを提供（settings インスタンス経由で取得）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（有効値: development, paper_trading, live; 不正値で ValueError）
    - LOG_LEVEL（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL; 不正値で ValueError）
    - ヘルパー: is_live / is_paper / is_dev

- AI: ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを算出。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して利用（calc_news_window 関数）。
  - バッチ処理: 最大 20 銘柄/回、1 銘柄あたり最大 10 記事・3000 文字までトリム。
  - 再試行ロジック: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（デフォルト _MAX_RETRIES=3）。
  - レスポンス検証: JSON パース、"results" キー、各要素の code/score 検証、未知コードの無視、スコアを ±1.0 にクリップ。
  - DB 書き込みは部分置換（該当コードのみ DELETE → INSERT）して部分失敗時に既存データを保護。
  - テスト容易性: _call_openai_api をモック差し替え可能。

- AI: 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定。
  - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
  - マクロキーワードで raw_news をフィルタし、最大 20 件のタイトルを LLM に渡して macro_sentiment を算出（json mode）。
  - API 失敗時のフェイルセーフ: macro_sentiment = 0.0（例外を投げず継続）。
  - レジームスコア合成と閾値判定、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - OpenAI 呼び出しは独立実装でモジュール間の結合を避ける設計。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンおよび 200 日 MA 乖離を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近の財務を取得して PER / ROE を計算（EPS=0/欠損は None）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。有効レコード < 3 の場合は None を返す。
    - rank: 同順位の平均ランクを返す。丸め処理で浮動小数の ties を安定化。
    - factor_summary: count/mean/std/min/max/median を計算。
  - zscore_normalize を data.stats から再エクスポート。

- Data（kabusys.data）
  - calendar_management:
    - market_calendar を用いた営業日判定・次/前営業日取得・期間内営業日取得・SQ 判定等のユーティリティを実装。
    - DB にデータがない場合は曜日ベース（月〜金を営業日）でフォールバック。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィルと健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを実装（取得/保存件数、品質問題、エラー、ユーティリティ）。
    - 差分取得・バックフィル・品質チェックを行う ETL の基本方針を実装（詳細は pipeline モジュールにて）。
    - kabusys.data.etl で ETLResult を再エクスポート。

- DuckDB を主たるローカル DB として想定。主要に参照・更新されるテーブル（期待されるスキーマの存在）:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar, 等。
  - DuckDB 0.10 の挙動（executemany に空リストを与えられない等）を考慮した実装。

- ロギングとエラーハンドリング:
  - 各モジュールで詳細な logger 呼び出しを追加（info/debug/warning/exception）。
  - API 呼び出し失敗やパースエラーは多くの場面でフェイルセーフにフォールバックし、処理の継続を優先。

Security
- .env の自動読み込み時、既存 OS 環境変数は保護（protected set）され、.env の上書きから守られる仕組みを実装。
- OpenAI API キーは明示的に引数で注入可能（api_key）または環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を投げて明示的に通知。
- 機密情報の取り扱いに関する注意はドキュメントで明示が必要（本 CHANGELOG には実装上の振る舞いを記載）。

Notes / 使用上の注意
- すべての関数はルックアヘッドバイアス防止の設計方針に従い、datetime.today()/date.today() を直接参照しないか、参照タイミングを制御している（target_date 引数中心の設計）。
- 時刻はモジュールにより UTC naive な datetime を使用している箇所があるため、データ格納・クエリ時の timezone 扱いに注意が必要。
- OpenAI 呼び出しに依存する機能は外部料金・レート制限を受けるため、本番運用時は API キー管理とレート制御、エラーハンドリングの調整を推奨。
- DB スキーマ（テーブル列名や型）に依存するため、導入時は期待されるテーブルが存在することを確認してください。
- 単体テスト用フック: AI 呼び出しラッパー（_call_openai_api）を patch して外部 API をモック可能。

Breaking Changes
- 初回リリースのため破壊的変更はありません。

License
- （この CHANGELOG には記載なし。ライセンス情報はリポジトリルートの LICENSE を参照してください。）

----- 
以上がコードベースから推測して作成した CHANGELOG.md（Keep a Changelog 準拠）の内容です。必要であれば、日付・表現・各項目の詳細（例: 必要な DB スキーマのカラムリスト、サンプル .env.example）を追加して更新します。