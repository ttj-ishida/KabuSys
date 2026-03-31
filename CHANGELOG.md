CHANGELOG
=========

本CHANGELOGは、提供されたコードベースの実装内容から推測して作成したものです。実際のリリースノートとは差異がある可能性があります。

フォーマット: Keep a Changelog 準拠
-----------------------------------

[Unreleased]
-------------

- （なし）

[0.1.0] - 2026-03-31
--------------------

Added
- パッケージ初期リリース。主要機能を実装。
- 基本パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポートモジュール: data, strategy, execution, monitoring（/__init__.py__/に定義）
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック: .git または pyproject.toml を親ディレクトリから探索して自動ロード対象を決定。
  - .env 読み込みの挙動:
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを抑制可能
    - export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント等に対応したパーサ実装
    - override と protected の概念による上書き制御（OS 環境変数を保護）
  - Settings クラスにより型安全に環境設定を取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック（未設定時は ValueError）
    - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等の Path 型変換
    - CPU/MEMORY/DISK の閾値やログレベル/実行環境判定（development/paper_trading/live）
- AI モジュール（kabusys.ai）
  - ニュースセンチメント（score_news）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄当たり最大記事数・文字数トリム、JSON Mode 応答のバリデーションを実装。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフ実装。
    - レスポンス検証で未知コードを無視し、スコアを ±1.0 にクリップ。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を calc_news_window として提供。
    - テスト容易性のため _call_openai_api を差し替え可能。
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に保存。
    - マクロキーワードによるタイトル抽出、OpenAI 呼び出し（gpt-4o-mini）による JSON 応答パース、リトライ・フェイルセーフ（失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス対策: date 引数ベースで過去データのみを参照（datetime.today()/date.today() を直接参照しない設計）。
- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルの利用を前提に営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録データがない/NULL の場合は曜日（土日）ベースのフォールバック処理を実装。
    - calendar_update_job: J-Quants クライアントを用いて差分取得→冪等保存（バックフィル・健全性チェック含む）。
  - ETL パイプライン基盤（pipeline, etl）
    - ETLResult データクラスを導入して ETL の取得件数・保存件数・品質問題・エラーを集約。
    - 差分更新、バックフィル、品質チェックの考え方（quality モジュールと連携）を実装する基礎を提供。
    - jquants_client（外部クライアント）に依存してデータ取得/保存を実施。
- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR/株価、20 日平均売買代金、出来高比率を計算。入力ウィンドウのスキャン幅と NULL ハンドリングを注意して実装。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS=0/欠損は None）。PBR/配当利回りは未実装。
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズン（営業日ベース、デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションを実装。
    - calc_ic: スピアマンランク相関（IC）計算。レコードが少ない場合は None を返す。
    - rank: 同順位は平均ランクとするランク付け（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計要約を返す。
- 共通
  - DuckDB を主要なローカル分析 DB として採用（各モジュールで DuckDB 接続を前提に実装）。
  - ロギングを各モジュールに導入し、情報・警告・例外・デバッグ出力を適切に出力。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- OpenAI API キーや各種トークンは必須であり、Settings の必須プロパティは未設定時に ValueError を発生させることで明示的に扱う実装。
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストや CI 向け）。

Notes / Known limitations
- 一部機能は「現フェーズ」やコメントで未実装・限定実装（例: PBR・配当利回りは未実装）。
- news_nlp と regime_detector の OpenAI 呼び出しはそれぞれ独立実装（テスト用に差し替え可能）で、内部で JSON Mode を前提としているため API 応答形式に依存する。
- DuckDB の executemany の挙動やリストバインドの互換性について注意書きがあり、実装側で空リストを渡さないガードを入れている。
- calendar_update_job や ETL パイプラインは外部 jquants_client に依存するため、実行にはそのクライアント実装（fetch/save 関数）が必要。
- ファイル末尾の pipeline._get_max_date の実装が未完/切れている箇所が見受けられる（コード提供断片に起因）。本 CHANGELOG は現状のコードから推測して作成しています。

Developers
- テスト容易性を考慮し、OpenAI 呼び出しポイント（_call_openai_api 等）をモック／パッチ可能な実装にしているためユニットテストの導入が容易。
- ルックアヘッドバイアス防止の観点から date 引数ベースでデータ参照を行う設計方針が一貫している。

（注）本 CHANGELOG は提供されたソースコードの内容を基に推測して作成しています。実際の変更履歴やリリースノートは開発者の公式ドキュメントを参照してください。