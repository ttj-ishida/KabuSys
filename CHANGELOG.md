Changelog
=========
すべての重要な変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

[Unreleased]
------------

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージ初期リリースを追加。
  - パッケージバージョンは kabusys.__version__ = "0.1.0"。

- 環境設定モジュールを追加（kabusys.config）。
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダを実装。
  - 自動読み込みの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応。
  - Settings クラスを公開（settings インスタンス）。J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等を環境変数から取得。
  - 必須環境変数未設定時は _require() が ValueError を送出。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装（不正値は ValueError）。

- AI モジュールを追加（kabusys.ai）。
  - ニュースセンチメント解析モジュール（kabusys.ai.news_nlp）。
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）へ JSON mode で送信し ai_scores テーブルへ書き込み。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、1 銘柄あたりの記事/文字数制限、レスポンス検証（JSON 抽出・results 構造・コード照合・数値検証）を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ処理を実装。API 失敗時は個別チャンクをスキップしてフェイルセーフで継続。
    - DuckDB への冪等的書き込み（DELETE -> INSERT、部分失敗時に既存スコアを保護）。
    - テスト容易化のため _call_openai_api をパッチ差し替え可能に実装。
  - 市場レジーム判定モジュール（kabusys.ai.regime_detector）。
    - ETF 1321（Nikkei 225 連動型）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出。
    - prices_daily と raw_news を参照し、OpenAI を用いて macro_sentiment を取得（記事がない場合は LLM 呼び出しを行わず 0.0 を使用）。
    - API 呼び出しのリトライ/バックオフ、エラー時のフォールバック（macro_sentiment=0.0）を実装。
    - 計算結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。prices_daily のクエリは target_date 未満のデータのみを使用。

- Data モジュールを追加（kabusys.data）。
  - カレンダー管理（kabusys.data.calendar_management）。
    - JPX カレンダー（market_calendar）を扱うユーティリティ群：is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録データを優先し、未登録日は曜日ベース（平日）でフォールバックする設計。最大探索日数による安全措置を実装。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィルや健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline）。
    - ETLResult データクラスを追加（ETL の各種取得件数、品質問題、エラーの収集を可能にする）。
    - 差分取得、保存（jquants_client 経由の Idempotent save）、品質チェック（quality モジュール）を想定した設計。
    - ETLResult.to_dict() で品質問題をシリアライズ可能に実装。
  - ETLResult を再エクスポートする kabusys.data.etl を追加。

- Research モジュールを追加（kabusys.research）。
  - ファクター計算（kabusys.research.factor_research）。
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER、ROE）、Volatility（20日 ATR）等を DuckDB + SQL で実装。
    - 欠損・データ不足時に None を返す設計。結果は (date, code) をキーとした dict のリストで返却。
  - 特徴量探索（kabusys.research.feature_exploration）。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換（rank）、統計サマリー（factor_summary）を実装。
    - 外部依存（pandas 等）を使わず標準ライブラリ＋DuckDB のみで実装。
  - 研究用ユーティリティを __all__ で公開（zscore_normalize の再エクスポート等）。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で注入する設計。未設定時は ValueError を発生させ明示的に扱う。

Notes / 設計上の重要事項
- ルックアヘッドバイアス対策として多くの処理で date.today() 等を参照せず、呼び出し側から target_date を渡す方式を採用。
- DuckDB を想定した SQL 実装（ウィンドウ関数や executemany の挙動に注意）。一部の実装は DuckDB のバージョン依存の挙動（リストバインド等）を回避するため工夫あり。
- OpenAI 呼び出しは JSON mode（response_format={"type": "json_object"}）を利用。レスポンスの堅牢なパースと検証を行い、失敗時はスコアをスキップまたはデフォルト値にフォールバックして堅牢性を確保。
- DB 書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT 想定）しているため、再実行が安全な設計。
- テスト容易性のため外部呼び出し部分（OpenAI 呼び出し等）をパッチ差し替え可能に実装。

References / 既知の未実装項目
- monitoring や execution パッケージは __all__ に含まれているが、このリリースに該当する詳細実装は含まれていません（将来追加予定）。

--- 

（この CHANGELOG はコードベースの内容から推測して作成しています。実リリース日やリリースノートは実際のリリースプロセスに応じて調整してください。）