Changelog
=========

すべての重要な変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に準拠しています。
リリースごとに「Added / Changed / Fixed / Security」などのカテゴリで要約しています。

[Unreleased]
------------

- なし（初回リリースは 0.1.0）

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ初期リリース。モジュール構成と主要機能を追加。
  - kabusys パッケージのエントリポイント（__version__ = 0.1.0）を追加。
  - 公開サブパッケージ: data, strategy, execution, monitoring を __all__ に設定。

- 環境変数/設定管理（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テストで利用）。
  - .env のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを考慮。
  - Settings クラスを提供（プロパティアクセスで設定取得）。
    - J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境フラグ等のプロパティを実装。
    - 必須設定取得時は未設定で ValueError を送出（_require）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - Path を返す設定は expanduser を適用。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し ai_scores に書き込む処理を実装。
    - ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当）を calc_news_window() で提供。
    - チャンク処理（デフォルト最大 20 銘柄 / チャンク）・1銘柄あたり記事数/文字数上限でトークン肥大を抑制。
    - JSON Mode 応答を検証してスコアを抽出（_validate_and_extract）。不正応答はログを出してスキップ。
    - リトライ/バックオフ戦略（429、ネットワーク断、タイムアウト、5xx を対象）を実装。
    - テスト支援として _call_openai_api を patch して差し替え可能。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に書き込み（DELETE→INSERT、部分失敗時の保護）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して ma200_ratio を計算、マクロ記事を抽出し OpenAI に投げて macro_sentiment を取得。
    - レジームスコア合成と market_regime テーブルへの冪等書き込みを実装（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
    - API 呼び出しのリトライ/バックオフ、JSON パース失敗や API エラー時はフェイルセーフで macro_sentiment=0.0 を採用。
    - 設計上、datetime.today()/date.today() に依存せずルックアヘッドバイアスを防止。

- リサーチ（kabusys.research）
  - factor_research モジュール
    - calc_momentum: 1m/3m/6m リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時の None 扱い。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。欠損ハンドリングあり。
    - calc_value: raw_financials の最新財務データと当日終値から PER, ROE を計算。EPS=0/欠損時は None。
    - 全関数は DuckDB 接続を受け取り SQL（ウィンドウ関数等）で計算。

  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。入力検証あり（horizons は 1..252）。
    - calc_ic: ファクター値と将来リターンのスピアマン（ランク相関）を計算。サンプル不足時は None。
    - rank: 同順位は平均ランクで処理するランク変換（丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar を元に営業日判定（is_trading_day）、前後の営業日取得（next_trading_day/prev_trading_day）、期間内の営業日列挙（get_trading_days）、SQ 判定（is_sq_day）を実装。
    - market_calendar が未取得の場合は曜日ベース（土日除外）でフォールバック。
    - 夜間バッチ calendar_update_job を実装（J-Quants client 経由で差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索範囲制限や NULL 値検知時のログ出力など堅牢性を考慮。

  - pipeline / ETL
    - ETLResult dataclass を追加（イベントログ・品質チェック結果・エラー一覧を含む）。
    - ETL パイプラインの設計方針を実装（差分取得、backfill、品質チェックの取り扱い等）。（実行ロジックは pipeline モジュールとして実装開始）
    - data.etl で ETLResult を再エクスポート。

- DuckDB を主なデータ格納/問い合わせに使用する設計を採用。各モジュールは DuckDB 接続を引数に取り、SQL と Python の組合せで計算/集約を行う。

- ロギングを各モジュールに導入。重要な異常・フォールバック・処理完了は logger.info/warning/exception で出力。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Security
- OpenAI API キーの取得は引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させることで誤動作を防止。

Notes / 設計上の重要なポイント
- ルックアヘッドバイアス防止: 多くの処理（news window、regime scoring、factor 計算等）は date 引数を明示的に受け取り、内部で現在時刻を参照しない設計を採用。
- DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT の想定）にして、部分失敗時に既存データが失われないよう配慮。
- OpenAI 呼び出しは JSON Mode を想定し、レスポンスのパース・検証を厳格に行う。エラー時はログを残して処理継続（フェイルセーフ）。
- テストのために内部 API 呼び出し関数（例: _call_openai_api）を patch しやすい実装になっている。

必要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能を使う場合は必須）
- KABUSYS_ENV（development/paper_trading/live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- その他（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH 等のデフォルトあり）

既知の制約
- DuckDB のバージョン依存（executemany の空リスト扱い等）に対するワークアラウンドを実装済み。
- API（OpenAI/J-Quants）呼び出しに対するリトライを実装しているが、長時間の API 障害時は機能制限やスコア欠落が発生する可能性がある。

今後の予定（例）
- strategy / execution / monitoring の具現化と統合テスト
- ETL pipeline の具体的な差分取得・品質チェック実行フローの追加実装
- 単体テスト・統合テストの充実（外部 API をモックしたテストベッド）

--- 

（この CHANGELOG はコードベースからの推定に基づいた要約です。実際のリリースノートとして用いる場合は、リリースやパッケージ配布時に必要に応じて調整してください。）