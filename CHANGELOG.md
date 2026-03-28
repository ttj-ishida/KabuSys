Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」のフォーマットに従っています。

フォーマットの意味については: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-03-28
------------------

Added
- 基本パッケージ初期実装を追加
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、主要サブモジュールを __all__ で公開（data, strategy, execution, monitoring）。
- 環境変数 / 設定管理モジュールを追加（kabusys.config）
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パーサを実装（export KEY=val 形式、シングル／ダブルクォート内のエスケープ処理、コメント扱いのルールなどをサポート）。
  - 環境変数の必須チェック（_require）と Settings クラスを提供。主な設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のヘルパー
- AI 関連モジュールを追加（kabusys.ai）
  - news_nlp.score_news
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント ai_scores に書き込む。
    - 実装の特徴:
      - JST ベースのニュースウィンドウ計算（前日 15:00 ～ 当日 08:30 JST）を提供（calc_news_window）。
      - 1チャンクあたり最大 20 銘柄、各銘柄は最大 10 記事・3000 文字にトリムして送信。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ。
      - JSON レスポンスの堅牢なパースとバリデーション（余計なテキストの前後削り取り、results キー／型検証、未知コードの無視、スコアの数値変換と ±1 クリップ）。
      - 部分失敗対策: 書き込みは対象コードのみ DELETE → INSERT（DuckDB executemany の空リスト制約を考慮）。
      - API キーは api_key 引数または環境変数 OPENAI_API_KEY から解決。
  - regime_detector.score_regime
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次で判定、market_regime テーブルへ冪等書き込み。
    - 実装の特徴:
      - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。
      - マクロニュース抽出はマクロキーワード群でフィルタ、記事がなければ LLM 呼び出しをスキップ（macro_sentiment = 0.0）。
      - OpenAI 呼び出しは再試行ロジックを持ち、API失敗時は安全に macro_sentiment=0.0 にフォールバック。
      - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT で冪等性を確保。失敗時は ROLLBACK を試行し、例外を上位に伝播。
- データプラットフォーム関連モジュールを追加（kabusys.data）
  - calendar_management
    - JPX カレンダー管理（market_calendar）用ユーティリティを実装。
    - 営業日判定 API: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB 未取得日のフォールバックは曜日ベース（週末＝非営業日）。DB登録がある場合は DB 値を優先。
    - カレンダー夜間バッチ calendar_update_job を実装（J-Quants API から差分取得、バックフィル日数・健全性チェックを実装）。
  - pipeline / etl / ETLResult
    - ETL パイプラインの結果を表す ETLResult データクラスを公開（kabusys.data.ETLResult を kabusys.data.etl で再エクスポート）。
    - パイプライン設計方針・差分取得、バックフィル、品質チェック（quality モジュール）との接続を想定したユーティリティを実装。
    - DuckDB の実装上の注意（テーブル存在確認、MAX(date) 取得など）を含む。
  - jquants_client / quality などのクライアントとの連携を想定（fetch / save 関数の利用を前提）。
- リサーチ（kabusys.research）モジュールを追加
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR・相対ATR・20日平均売買代金・出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS が 0/欠損時は None）。
    - 設計上、prices_daily / raw_financials のみ参照し、外部発注等の副作用はなし。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン先の将来リターン（デフォルト [1,5,21]）を計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（None/不足レコードは None を返す）。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸め処理で ties の誤差を低減）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - kabusys.research.__init__ で主要関数を公開。
- データ処理での安全性・互換性対策
  - DuckDB の executemany に対する空パラメータ回避などの注意点を盛り込み、部分失敗時に既存データを保護する戦略を採用。
  - 多くの処理で datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Security
- OpenAI API キーは明示的に引数で注入可能（テスト容易性と秘匿性向上）。環境変数参照は明示的（OPENAI_API_KEY）。

Notes / Implementation details
- OpenAI 呼び出しは gpt-4o-mini を指定し、JSON Mode を利用する前提で実装。API レスポンスの堅牢なパースとエラー分類（RateLimitError / APIConnectionError / APITimeoutError / APIError 等）を行っているため、外部 API の一時障害に対してフェイルセーフ動作を行います。
- .env パーサはシェル互換の export プレフィックス、クォート内のバックスラッシュエスケープ、コメントルール（クォート外での # の取り扱い）を考慮しており、OS 環境変数を保護するため既存キーの上書きを制御できます。
- DB 書き込みは基本的にトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、冪等性（DELETE→INSERT、ON CONFLICT 相当）を意識した実装になっています。

Authors
- kabusys 開発チーム

Acknowledgments
- 実装における設計ノートはプロジェクト内の StrategyModel.md / DataPlatform.md に基づいています。