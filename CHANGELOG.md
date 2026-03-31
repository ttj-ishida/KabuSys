# CHANGELOG

このプロジェクトは「Keep a Changelog」形式に準拠して変更履歴を記載しています。  
（初期実装に基づいてコードから推測し作成しています）

全般的な方針・設計上の注意
- ルックアヘッドバイアス防止のため、日付計算やウィンドウは内部で date / datetime の引数から明示的に決定し、datetime.today() / date.today() を直接参照しない実装方針を採用しています。
- OpenAI API 呼び出しはリトライ（指数バックオフ）、フェイルセーフ（API失敗時は中立スコアにフォールバック）など耐障害性を重視した実装になっています。
- DuckDB を主要なローカルデータストアとして想定し、SQL と Python を組み合わせて計算・集計を行います。多くの処理は DuckDB 接続を引数に取ります。
- DB 書き込みは冪等性（既存行の置換 / 個別 DELETE → INSERT）を心がけています。

Unreleased
- なし

0.1.0 - 2026-03-31
------------------

Added
- 基本パッケージ情報
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探す方式。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env のパーシング:
    - export プレフィックス、クォート文字（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントルールに対応。
    - 上書き制御（override）および protected キー（OS環境変数の保護）に対応。
  - Settings クラスで主要設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path
    - 監視用設定: pid_file_path、cpu/memory/disk の閾値
    - システム設定: KABUSYS_ENV の検証（development/paper_trading/live）、LOG_LEVEL の検証、is_live/is_paper/is_dev ヘルパー

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None)
      - 指定ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST に対応した UTC 計算）に基づき raw_news と news_symbols を集約。
      - 銘柄ごとに最新記事を結合し、銘柄バッチ（最大 20 銘柄/チャンク）で OpenAI（gpt-4o-mini、JSON Mode）へ送信。
      - レスポンスを厳密にバリデーションし、スコアを ±1.0 にクリップ。
      - 部分失敗を考慮し、取得できた銘柄のみを DELETE→INSERT で置換して冪等的に ai_scores テーブルへ書き込み。
      - 429、ネットワーク断、タイムアウト、5xx は指数バックオフでリトライ。その他はスキップして継続（フェイルセーフ）。
      - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（unittest.mock.patch を想定）。
    - calc_news_window(target_date) を公開（ウィンドウ計算の再利用）。
  - レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の直近 200 日の終値から MA200 乖離（ma200_ratio）を計算（ルックアヘッド防止のため target_date 未満を使用）。
      - マクロキーワードでフィルタしたニュースを集め（最大 20 件）、OpenAI でマクロセンチメントを評価。
      - ETF MA 要素（重み 70%）とマクロセンチメント（重み 30%）を合成しレジームスコア（-1〜1）を算出して market_regime テーブルへ冪等書き込み。
      - OpenAI 呼び出しはリトライ＆ 5xx 判定を考慮。API 失敗時は macro_sentiment=0.0 を用いるフェイルセーフ。
      - 内部で使用する OpenAI 呼び出し関数は news_nlp のものと独立させ、モジュール結合を避ける設計。

- 研究（kabusys.research）
  - factor_research
    - calc_momentum(conn, target_date)
      - 1M/3M/6M リターンおよび 200 日移動平均乖離（ma200_dev）を DuckDB SQL で計算。データ不足時は None を返す動作。
    - calc_volatility(conn, target_date)
      - 20 日 ATR（true_range の平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。データ不足の取り扱いあり。
    - calc_value(conn, target_date)
      - raw_financials から直近財務を取得し PER（EPS が有効な場合）と ROE を算出。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None)
      - 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を用いて計算。ホライズン検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンのランク相関（IC）を計算する実装。有効レコードが 3 未満なら None。
    - rank(values) と factor_summary(records, columns)
      - ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を算出。外部 lib に依存しない実装。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
      - market_calendar のデータがある場合は DB 値を優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
      - next/prev は最大探索日数（_MAX_SEARCH_DAYS）を設けて無限ループを防止。
    - calendar_update_job(conn, lookahead_days=_CALENDAR_LOOKAHEAD_DAYS)
      - J-Quants API（jquants_client）から差分取得して market_calendar を冪等更新。バックフィル（直近 _BACKFILL_DAYS）の再フェッチと健全性チェックを実装。
  - ETL / pipeline
    - ETLResult dataclass を導入（ETL 実行結果の構造化、品質問題とエラーの集約、辞書化メソッドを提供）。
    - pipeline module は差分取得、jq.save_* による冪等保存、品質チェック（kabusys.data.quality 参照）を行う設計。既定の backfill 日数を持つ。
  - etl.py で ETLResult を再エクスポート。

Changed
- 設計上の明確化／堅牢化
  - 多くのモジュールで「ルックアヘッドバイアス防止」「テスト容易性（API 呼び出し差し替え）」「部分失敗からの保護（部分書き換え）」を方針として採用。
  - OpenAI 呼び出しに対してリトライ戦略（429・ネットワーク断・タイムアウト・5xx を対象）と JSON レスポンスの堅牢なパース（前後余計なテキストをトリムして JSON を抽出）を導入。
  - DuckDB executemany の互換性（空リスト不可）を考慮した実装（空チェック後に executemany を呼ぶ等）。

Fixed
- なし（初期リリース）

Notes / 既知の制限
- OpenAI API キー（OPENAI_API_KEY）が未設定の場合、score_news/score_regime は ValueError を送出します。テスト時は api_key 引数経由でキー注入が可能です。
- news_nlp / regime_detector は gpt-4o-mini の JSON Mode を前提にレスポンス形式を厳密に期待していますが、不正なレスポンスはログ出力のうえスキップして継続する実装です。
- jquants_client や quality モジュール等、外部依存部分はインターフェースを参照して呼び出す設計を取っており、実装やバージョンに依存します（コード片からの推測に基づく記述です）。
- execution や monitoring など __all__ に含まれるモジュールは本差分においてコード断片として記載がなかったため、CHANGELOG に詳細記載はありません。

将来の改善案（今後のリリース候補）
- AI モデルの切替やプロンプトの A/B テストを容易にする設定（モデル名・温度・フォーマット設定の外部化）。
- 並列化によるニューススコアリングの高速化（API レート制限とのトレードオフを考慮）。
- calendar_update_job / ETL パイプラインのジョブ監視・通知（Slack 通知等）の統合。

--- 

（この CHANGELOG は提供されたソースコード内容を基に推測して作成しています。実際のリリースノート作成時はコミット履歴やパッケージ公開情報を参照して調整してください。）