CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従います。
このプロジェクトのバージョンは semantic versioning に従います。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を追加。
    - public API として data, strategy, execution, monitoring を __all__ に公開。

- 環境設定 / ロード機能 (src/kabusys/config.py)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート解除、バックスラッシュエスケープ処理、インラインコメント処理の扱いを実装。
    - 無効行・コメント行のスキップ。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化サポート（テスト等向け）。
  - Settings クラスを提供し、環境変数から各種設定値を取得:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティ
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値以外は ValueError）
    - is_live / is_paper / is_dev のヘルパーを追加

- AI 系機能 (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news・news_symbols を集約して銘柄ごとのニュースを作成。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST、内部は UTC naive datetime に変換）。
    - OpenAI (gpt-4o-mini) の JSON mode を用いたバッチ評価:
      - 1 回の API 呼び出しで最大 20 銘柄のバッチ処理。
      - 1 銘柄あたり最大 10 記事・最大 3000 文字にトリム。
    - 再試行 / バックオフ処理:
      - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ（デフォルト上限）。
      - 非リトライ系エラーはスキップして継続（フェイルセーフ）。
    - レスポンスバリデーションを実装（JSON 抽出、results キー、コード・スコアの型検査、既知コード以外は無視）。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に保存（DELETE → INSERT の手順、部分失敗で既存データ保護）。
    - テスト用に _call_openai_api を patch できるように設計。
    - score_news(conn, target_date, api_key=None) を公開。戻り値は書き込んだ銘柄数。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出は news_nlp.calc_news_window を利用してウィンドウを決定し、title ベースでマクロキーワードに合致する記事を取得。
    - OpenAI 呼び出し（gpt-4o-mini）でマクロセンチメントを得る。API 障害時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジームスコア合成と閾値判定、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト用に _call_openai_api を差し替え可能。

- 研究（Research）モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算（データ不足時は None）。
    - calc_value: raw_financials と prices_daily を組合せて PER / ROE を算出（EPS が不適切な場合は None）。
    - 全関数は DuckDB 接続を受け取り DuckDB 内のテーブルのみを参照（副作用なし）。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons のバリデーションを実施。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。十分なサンプルがない場合は None。
    - rank: 同順位は平均ランクで処理するランク変換ユーティリティ（丸め処理で ties の判定漏れを防止）。
    - factor_summary: ファクター列ごとの count/mean/std/min/max/median を算出。
  - 研究向けユーティリティをまとめてエクスポート（research.__init__）。

- データプラットフォーム / ETL (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を利用した営業日判定ロジックを実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - DB の値を優先し、未登録日は曜日ベース（土日を休日）でフォールバック。最大探索日数制限で無限ループを防止。
    - 夜間バッチ更新 calendar_update_job: J-Quants から差分取得して market_calendar を idempotent に更新（バックフィルと健全性チェックを実装）。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を導入（取得/保存件数、品質問題、エラー一覧を格納）。
    - 差分取得・バックフィル方針、品質チェック呼び出し方針の実装方針をドキュメント化。
    - DuckDB 互換性やテーブル存在チェック、最大日付取得ユーティリティを実装。
    - etl.py で ETLResult を再エクスポート。

- 設計方針 / ドキュメント（各モジュール内 docstring）
  - ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計（関数に target_date を注入）。
  - フェイルセーフ方針: API の失敗は可能な限り局所で扱い、全体処理の停止を避ける。
  - DuckDB のバージョン差異を考慮した実装（executemany の空リスト回避、ANY バインドの互換性回避など）。
  - テスト可能性への配慮: OpenAI 呼び出しの差し替えポイントを提供。

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Security
- 初回公開のため該当なし。

Notes / 注意事項
- OpenAI API を利用する機能（news_nlp, regime_detector）は api_key 引数または環境変数 OPENAI_API_KEY を必要とする。未設定時は ValueError を送出。
- settings の一部プロパティ（jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id）は必須として ValueError を発生させる仕様。
- DB 書き込み処理はトランザクション（BEGIN/COMMIT/ROLLBACK）で保護されるが、ROLLBACK に失敗した場合はログを出力して例外を再送出する実装。
- OpenAI モデルのデフォルトは gpt-4o-mini。将来変更される可能性がある。

参考
- 各モジュール内の docstring に処理フロー・設計方針・使用法が記載されています。テストでは _call_openai_api 等を patch して外部 API 呼び出しを模擬できます。