CHANGELOG
=========

全般ルール: この CHANGELOG は "Keep a Changelog" フォーマットに準拠しています。  
リリース日付はコードベースから推測して設定しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)。
- 基本パッケージ情報
  - __version__ を "0.1.0" に設定。
  - パブリックモジュール群 data, strategy, execution, monitoring を __all__ で公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定をロードする Settings クラスを追加。
  - プロジェクトルート自動検出: __file__ を基点に .git または pyproject.toml を探索してルートを特定。
  - 自動ロード優先度: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env の行パーサを実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートで囲まれた値のバックスラッシュエスケープを正しく処理。
    - クォート無しの値におけるインラインコメント認識 (直前がスペース/タブの場合) を実装。
  - ファイル読み込み時の保護:
    - override フラグと protected キーセットを使った安全な環境変数上書きロジック。
    - 読み込み失敗時は警告を出す。
  - 必須環境変数検査用の _require 関数と Settings のプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などを取得。
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパスを指定。
    - KABUSYS_ENV に対するバリデーション (development/paper_trading/live) と LOG_LEVEL 検査。
    - is_live / is_paper / is_dev のブールヘルパを提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP (kabusys.ai.news_nlp)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いてセンチメントスコア (±1.0) を算出。
    - 設計上の注意:
      - スコアリング対象ウィンドウは JST 基準で前日 15:00 ～ 当日 08:30（UTC 変換済み）を使用。calc_news_window を提供。
      - 1 銘柄あたりの記事数・文字数上限（トークン爆発対策）を実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
      - 最大バッチサイズでバッチ送信（デフォルト 20 銘柄 / 回）。
      - レート制限・ネットワーク断・タイムアウト・5xx を対象に指数バックオフでリトライ。リトライ失敗や想定外エラー時は当該チャンクをスキップし継続（フェイルセーフ）。
      - レスポンスは厳密な JSON を期待するが、前後余計なテキストが混ざる場合に最外の {} を抽出するフォールバックを実装。
      - レスポンス検証: results リスト、code と score の存在、score の数値性／有限性を確認。未知コードは無視。
      - スコアは ±1.0 にクリップ。
      - 書き込みは冪等性を保つ（DELETE → INSERT、部分失敗時に既存スコアを保護）。
    - score_news API を公開し、成功時は書き込んだ銘柄数を返す。OpenAI API キーは引数または環境変数 OPENAI_API_KEY で指定。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - 処理フロー:
      - _calc_ma200_ratio で過去 200 日の終値から MA 乖離を計算（ルックアヘッドを避けるため target_date 未満のデータのみ使用）。
      - calc_news_window で取得ウィンドウを算出し、raw_news からマクロキーワードに一致するタイトルを取得（最大 20 件）。
      - OpenAI（gpt-4o-mini）へプロンプト送信し JSON で macro_sentiment を取得。エラー時は 0.0 にフォールバック。
      - 0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment を clip(-1,1) してスコア化ししきい値でラベル付け。
      - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を再送出。
    - OpenAI 呼び出しはモジュール内の専用関数を使用しモジュール結合を防止。

- データ基盤 (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を実装。
    - DB にカレンダーがない／未取得の場合は曜日ベースで土日を非営業日扱いするフォールバックを実装。
    - next/prev_trading_day では最大探索日数を設定して無限ループを防止（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に保存。バックフィル・健全性チェック・エラーハンドリングを実装。
  - ETL パイプライン (pipeline / etl)
    - ETLResult dataclass を公開（kabusys.data.etl 経由で再エクスポート）。
    - ETLResult は取得数・保存数・品質問題（quality.QualityIssue）・エラーを保持し、辞書変換用 to_dict を提供。
    - pipeline モジュールは差分更新、保存（jquants_client 経由の idempotent 保存）、品質チェックの枠組みを示す（実装の入口）。
    - 内部ユーティリティ: テーブル存在チェックや最大日付取得を提供。
    - 市場カレンダー関連の先読み／バックフィルの規定値や最大過去日数などの定数を導入。

- リサーチ（kabusys.research）
  - ファクター計算 (research.factor_research)
    - Momentum, Volatility, Value, Liquidity に対応する関数を実装:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算。データ不足時は None を返す。
      - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
      - calc_value: raw_financials から最新の財務指標（EPS, ROE）を取得し PER / ROE を計算。EPS が 0/欠損の場合は None。
    - DuckDB 上の SQL ウィンドウ関数を多用し、ルックアヘッドバイアスを避ける。
  - 特徴量探索 (research.feature_exploration)
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。有効サンプルが 3 未満なら None を返す。
    - rank: 同順位は平均ランクとするランク化関数（round(v,12) による丸めで ties の検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー関数。
  - research パッケージは zscore_normalize（kabusys.data.stats から）を再エクスポートし、主要な計算関数を __all__ で公開。

Integration / External APIs
- OpenAI（gpt-4o-mini）を利用した JSON mode でのスコアリング・レジーム判定を導入。API 呼び出しは専用ラッパー関数を使用してテスト時に差し替え可能に設計。
- J-Quants クライアント（kabusys.data.jquants_client）を前提として calendar / ETL で利用。
- kabu ステーション API、Slack 用の環境変数設定をサポート。

Security / Safety / Reliability
- LLM/API 呼び出し失敗やレスポンスパース失敗は例外を投げずフェイルセーフでゼロスコアやスキップにフォールバック（ログ出力）。
- DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で冪等に実行。
- .env 読み込みで OS 環境変数を保護する protected キーセットを導入。

Fixed
- 初期リリースのため特定の「修正」は無し。ただし実装上の堅牢化（.env パーサの改善、API エラー時の挙動明確化、DuckDB executemany の空リスト回避など）を行い信頼性を高めた。

Changed
- 初回公開のため該当なし。

Removed
- 初回公開のため該当なし。

Notes / Breaking Changes
- これは初回公開リリースです。将来的に settings のプロパティ名や環境変数名、DB スキーマ、OpenAI モデル指定などは変更される可能性があります。特に ai.news_nlp と ai.regime_detector は OpenAI API の仕様変更やレスポンスフォーマットの違いに脆弱なので、アップデート時の互換性に注意してください。

Acknowledgements / Requirements
- 動作には DuckDB、OpenAI Python SDK（OpenAI クライアント）、J-Quants API クライアント（kabusys.data.jquants_client 実装）など外部 SDK/API との連携が必要です。
- 環境変数（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を正しく設定する必要があります。設定が足りないと Settings のプロパティアクセスで ValueError が発生します。