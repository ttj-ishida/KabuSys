CHANGELOG
=========
すべての変更は Keep a Changelog の形式に従って記載しています。

フォーマット:
- "Added" は新機能
- "Changed" は既存機能の変更
- "Fixed" はバグ修正
- バージョンごとに日付を付与

Unreleased
----------
（現在なし）

0.1.0 - 2026-03-29
-----------------

Added
- 初回リリース。パッケージ "kabusys" の基本機能を追加。
  - パッケージメタ:
    - バージョン: 0.1.0
    - パッケージトップで __all__ に ["data", "strategy", "execution", "monitoring"] を公開。

- 環境設定 / 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を安全に読み込む自動ローダ実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、シングル／ダブルクォート、バックスラッシュエスケープ、コメント処理等に対応。
    - .env 読み込み時に OS 側の既存環境変数を保護する仕組みを実装（protected set）。
  - Settings クラスを提供し、必要な設定値をプロパティ経由で取得:
    - J-Quants / kabu API / Slack トークン等の必須設定取得（未設定時は明示的な例外）。
    - DB パス (duckdb/sqlite)、KABUSYS_ENV 検証 (development/paper_trading/live)、LOG_LEVEL 検証。
    - is_live / is_paper / is_dev 判定プロパティ。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、銘柄ごとのニューステキストを OpenAI (gpt-4o-mini, JSON Mode) に送信してセンチメントスコアを算出。
    - 処理フロー:
      - JST 時刻ベースのニュースウィンドウ計算 (前日 15:00 ～ 当日 08:30 JST) を calc_news_window で提供（UTC naive datetime 出力）。
      - 1 銘柄あたり最大記事数／文字数でトリムし、最大 20 銘柄単位でバッチ送信。
      - レスポンスのバリデーション、スコアの ±1.0 クリップ。
      - ai_scores テーブルへ部分的に冪等的に書き込み（DELETE → INSERT を銘柄単位で実行）し、部分失敗時に既存スコアを保護。
    - 信頼性:
      - 429 / ネットワーク / タイムアウト / 5xx に対する指数バックオフとリトライ。
      - API 失敗時は該当チャンクをスキップして処理継続（フェイルセーフ）。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - 処理フロー:
      - prices_daily から 1321 の MA200 乖離を算出（target_date 未満のデータのみ使用してルックアヘッドを防止）。
      - raw_news をマクロキーワードでフィルタしてタイトルを抽出し、LLM により macro_sentiment を算出（記事なし時は LLM 呼び出しを行わず 0.0 を使用）。
      - 合成スコアを閾値でラベル化し、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバックして上位へ例外を伝播。
    - 信頼性:
      - LLM 呼び出しに対するリトライ、API エラー時は macro_sentiment=0.0 のフォールバック。

- Data モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー（market_calendar）を扱うユーティリティを追加:
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの営業日判定関数群。
      - DB にデータが無い場合は曜日ベース（土日非取引日）をフォールバックとして扱う設計。
      - next/prev の探索は最大 _MAX_SEARCH_DAYS（デフォルト 60）で打ち切る安全策。
      - calendar_update_job を提供。J-Quants API から差分取得し market_calendar を冪等的に更新（バックフィル・健全性チェック実装）。
      - market_calendar の NULL 値や未登録日に対するログとフォールバック処理。
  - pipeline / etl
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - ETL パイプラインの基盤ユーティリティ:
      - 差分取得のための最終日取得、バックフィル、品質チェック連携のための基準などを実装。
      - DuckDB の存在チェックや最大日付取得ユーティリティを提供。
    - 設計は idempotent な保存（ON CONFLICT / save_*）と品質チェックの集約を想定。

- Research モジュール (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターンおよび MA200 乖離を計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials と当日の株価から PER（EPS=0/欠損の場合 None）と ROE を算出。
    - 全関数とも DuckDB の prices_daily/raw_financials テーブルのみ参照し、現物注文などの外部副作用は無し。
  - feature_exploration
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）で将来リターンを計算。入力検証（horizons が正の整数かつ <= 252）を実装。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。十分なデータがない場合は None を返す。
    - rank: 同順位は平均ランクを与える実装（浮動小数丸めで ties を安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を算出。

Design / Reliability / Safety（設計上の主要な考慮点）
- ルックアヘッドバイアスを避けるため、モジュールは datetime.today()/date.today() をスコア算出や集計ロジックで直接参照しない（target_date を明示的に渡すインタフェース）。
- OpenAI / 外部 API 呼び出しに対してリトライとフォールバック（中立スコア）を実装し、API 障害で全体処理が停止しないように設計。
- DuckDB への書き込みは冪等性を考慮（DELETE→INSERT の組合せや個別 DELETE の executemany を利用）して部分失敗時のデータ保護を実現。
- 明確なログ出力と例外ハンドリング（ロールバック試行、警告ログ）を実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロードでは OS 環境変数を上書きしないデフォルト挙動と、.env.local による上書きオプションを採用して、意図しない環境変化によるリスクを軽減。

Notes / 今後の課題候補
- OpenAI クライアントの差し替えやローカルテスト用のモックは既に考慮されているが、より詳細なテストヘルパ（HTTP レスポンスの録再生等）を追加するとテスト性が向上します。
- 現在 strategy / execution / monitoring の公開はパッケージトップで示されているものの、今回のコードベースにはそれぞれの実装が（部分的または未掲載）含まれていないため、次フェーズでこれらの実装・統合を行うことが想定されます。