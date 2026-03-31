CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__ に基づきます。

Unreleased
----------

（なし）

0.1.0 - 2026-03-31
-----------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py
      - パッケージ名、バージョン ("0.1.0")、主要サブパッケージの __all__ を定義。
  - 環境設定管理
    - src/kabusys/config.py
      - .env / .env.local の自動ロード機能を追加（プロジェクトルートは .git または pyproject.toml により探索）。
      - .env パーサ実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
      - ロード順と上書きルール: OS環境変数 > .env.local > .env。OS 環境変数は保護（protected）される。
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
      - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）や
        デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）・バリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - AI（LLM）関連
    - src/kabusys/ai/news_nlp.py
      - ニュース記事を OpenAI（gpt-4o-mini）でバッチセンチメント評価し、ai_scores テーブルへ保存する処理を実装。
      - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ計算（calc_news_window）。
      - 銘柄毎に記事を集約し、トークン肥大対策として記事数および文字数でトリム（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 1 API 呼び出しで最大 20 銘柄を処理するチャンク化（_BATCH_SIZE）。
      - OpenAI 呼び出しのリトライ（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）とレスポンスバリデーション（JSON 抽出、results フォーマット検証、スコアの数値検証、スコアクリップ ±1.0）。
      - 部分失敗を考慮した DB 書き込み（対象コードのみ DELETE → INSERT。DuckDB の executemany の仕様に配慮）。
      - API キー解決は引数優先、なければ OPENAI_API_KEY 環境変数を参照。未設定時は ValueError を送出。
      - フェイルセーフ: API 失敗時は該当チャンク/銘柄をスキップして処理継続。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し日次の市場レジーム ('bull' / 'neutral' / 'bear') を判定するロジックを実装。
      - prices_daily / raw_news を参照して ma200_ratio を計算、マクロニュースはニュースタイトルでフィルタして最大 20 記事を LLM に渡す。
      - OpenAI 呼び出しは独立実装、リトライ・バックオフ・JSON パース失敗時のフォールバック（macro_sentiment = 0.0）。
      - レジームスコアの合成・クリップ後、market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
      - API キー解決ルールは news_nlp と同様。
    - src/kabusys/ai/__init__.py
      - score_news を公開 API として再エクスポート。
  - Data / ETL
    - src/kabusys/data/pipeline.py
      - ETL の結果を表す ETLResult dataclass を追加（取得件数、保存件数、品質チェック結果、エラーリスト等を保持）。
      - 差分更新・バックフィル・品質チェック・DuckDB テーブル最大日付取得ユーティリティを実装。
      - 市場カレンダー取得や品質チェック方針の記述（backfill による後出し修正吸収等）。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を再エクスポート。
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー（market_calendar）管理ユーティリティを追加。
      - 営業日判定 API: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
      - DB 登録値を優先し、未登録日は曜日ベース（平日＝営業日）でフォールバックする一貫した設計。
      - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等的に更新するバッチ処理（バックフィル、健全性チェック含む）。
      - DB が空の場合でも曜日フォールバックで動作する設計。
  - Research（ファクター計算・特徴量探索）
    - src/kabusys/research/factor_research.py
      - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20 日 ATR）、
        流動性（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を実装。
      - DuckDB 上のウィンドウ関数を活用した SQL 実装で、データ不足時の None ハンドリング等を行う。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
      - pandas 等の外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
    - src/kabusys/research/__init__.py
      - 主要関数（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）を公開。
  - パッケージ構成
    - data、ai、research モジュール群を追加し、それぞれの主要 API を __all__ 経由でエクスポート。

Security
- なし

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Removed
- 初回公開のため該当なし。

Notes / 実装上の注意点
- 再現性・バックテスト健全性:
  - ほとんどの処理（ニュース集約、レジーム判定、ファクター計算）は内部で datetime.today() / date.today() を直接参照せず、
    呼び出し側から target_date を受け取る設計（ルックアヘッドバイアスを防止）。
- OpenAI 絡み:
  - API 呼び出しには gpt-4o-mini を使用する想定。JSON mode を期待したレスポンス処理とし、不正なレスポンスは安全にスキップする。
  - API キーは引数優先、なければ環境変数 OPENAI_API_KEY を使用。未設定だと ValueError を送出するため、実行前にキーの設定が必要。
- DuckDB:
  - DuckDB を主要なストレージ/クエリ実行エンジンとして想定。executemany に空リストを渡すとエラーになるバージョン差に配慮した実装を行っている。
- 環境設定:
  - .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）に依存し、配布パッケージ化後も CWD に依存しないよう実装。
  - OS 環境変数を保護する仕組みがあるため、テスト時に .env.local で上書きしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD 等で制御可能。

今後の予定（未実装・拡張候補）
- PBR・配当利回りなどバリューファクターの拡張（現在は PER / ROE のみ実装）。
- ETL の詳細な品質チェックルールやアラートの強化（quality モジュール連携の拡張）。
- OpenAI レスポンスの堅牢化（生成物の追加検証や代替モデル対応）。
- 発注・実行（execution）・監視（monitoring）モジュールの実装（パッケージ __all__ に含まれるが未提供の可能性に注意）。

---  
（本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。動作や API の詳細は実際のランタイム・設定により変わるため、利用前にソースと環境変数を確認してください。）