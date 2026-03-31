CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-31
--------------------

Added
- 基本パッケージとバージョン情報を追加
  - パッケージルート: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
- 環境変数・設定管理を実装 (src/kabusys/config.py)
  - .env/.env.local の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサ実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 環境変数保護（protected set）により OS 環境変数の上書きを制御。
  - Settings クラスを実装し、J-Quants / kabu ステーション / Slack / DB パス /監視閾値 / 環境（development/paper_trading/live）/ログレベルの取得とバリデーションを提供。
  - 必須環境変数未設定時は _require() が ValueError を発生させる（明確なエラーメッセージ）。

- AI 関連: ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
  - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で提供。
  - バッチ処理・トリム制御: 銘柄ごと最大記事数/文字数を制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - 1API呼び出しあたり最大処理銘柄数 = _BATCH_SIZE（デフォルト20）。
  - JSON Mode での API 呼び出し、レスポンスの厳密なバリデーション(_validate_and_extract) と ±1.0 のクリップ。
  - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフで再試行。部分失敗時でも他銘柄の既存スコアを保護するため、対象コードのみを DELETE→INSERT で置換。
  - テスト容易性: _call_openai_api を patch で差し替え可能。

- AI 関連: 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（_MA_WINDOW）とマクロニュースの LLM センチメント（_MACRO_KEYWORDS）を重み付け（70% / 30%）して日次レジームを判定。
  - LLM 評価は gpt-4o-mini を利用。出力は厳密な JSON（{"macro_sentiment": ...}）を期待。
  - マクロ記事がない場合は LLM 呼び出しを行わず、macro_sentiment=0.0 を適用（フェイルセーフ）。API 失敗時も 0.0 へフォールバック。
  - ma200 比率計算でデータ不足時は中立値（1.0）を採用し、ロギングで通知。
  - 判定結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を行い例外を再送出。
  - テスト容易性: news_nlp と独立した _call_openai_api 実装（モジュール結合を避ける）。

- Research モジュール (src/kabusys/research/)
  - factor_research.py: DuckDB を用いた定量ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足時は None。
    - calc_volatility: 20日 ATR、ATR比率、20日平均売買代金、出来高比率を算出。必要行数未満は None を返す。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算。EPS が 0 または欠損時は per を None。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons 引数のバリデーションを実施。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。使用可能レコードが少ない場合は None。
    - rank: 同順位は平均ランクを与える実装（round(...,12) による ties 安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算するユーティリティ。
  - research パッケージは zscore_normalize（kabusys.data.stats 由来）等を再エクスポート。

- Data プラットフォーム (src/kabusys/data/)
  - calendar_management.py:
    - market_calendar を使った市場カレンダー管理（祝日・半日取引・SQ日）と営業日判定ユーティリティを提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。市場カレンダー未取得時には曜日ベースのフォールバック（週末除外）を行う。
    - calendar_update_job: J-Quants クライアント（jquants_client）から差分取得し market_calendar を冪等に更新。バックフィル、健全性チェック（未来日付の異常検知）を実装。
  - pipeline.py / etl.py:
    - ETLResult データクラス（ETL 実行メタ情報、品質問題、エラー一覧を格納）を実装し etl モジュールから再エクスポート。
    - ETL の差分取得・保存・品質チェックに関する設計（差分更新、backfill、品質チェックは収集して呼び出し元へ報告）を反映。
    - DuckDB のテーブル存在チェックや最大日付取得等のユーティリティを提供。
  - 実装上の互換性考慮: DuckDB の executemany が空リストを受け付けない問題を回避するため、空チェックを導入。

- その他
  - モジュールのロギングと詳細な警告/情報ログを各所に追加（データ不足・API失敗・ROLLBACK失敗等）。
  - OpenAI クライアント利用部分は例外ごとにハンドリング（RateLimitError / APIConnectionError / APITimeoutError / APIError）を行い、リトライやフォールバックを実装。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- 環境変数の取り扱いで OS 環境変数を保護する仕組みを導入（config._load_env_file の protected set）。
- API キー未設定時は明確なエラーを投げることで誤動作を防止（news_nlp.score_news / regime_detector.score_regime）。

Notes / Design decisions
- ルックアヘッドバイアス防止: AI / リサーチ関連の関数は datetime.today() / date.today() を参照せず、必ず target_date を引数で受け取る実装になっている。
- テスト容易性: 外部 API 呼び出し部分（OpenAI コール）を patch により差し替え可能に設計している。
- 部分失敗耐性: AI スコア系は部分失敗時に既存データを保護するため、書き込み対象を限定して置換する実装を採用。

今後の TODO（コード中コメントより推測）
- raw_financials からの追加ファクター（PBR、配当利回り等）の実装。
- pipeline の差分取得フローの上位 API 実装（ETL 実行のラッパーやスケジューリング向けのジョブ）。
- jquants_client のモック/統合テストの整備。