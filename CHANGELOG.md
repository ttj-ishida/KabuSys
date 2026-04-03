CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを使用します。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-03
--------------------

Added
- 初回リリース。日本株自動売買プラットフォームのコアコンポーネントを追加。
  - パッケージ公開情報
    - パッケージ名: kabusys
    - バージョン: 0.1.0
    - __all__ に data, strategy, execution, monitoring を公開。

  - 環境設定 / ロード
    - kabusys.config.Settings: 環境変数から設定値を取得する一元インターフェースを実装。
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須・任意の設定をプロパティで提供。
      - env 値と LOG_LEVEL の検証（許容値チェック）を実装し、不正値時は ValueError を送出。
      - パス系設定（DuckDB/SQLite/PID/kill フラグ）は Path オブジェクトとして提供。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env ロードを無効化可能。
    - .env 自動ロード機能
      - プロジェクトルートを .git または pyproject.toml から検出し、.env / .env.local を読み込む。
      - エクスポート形式（export KEY=val）、クォート・エスケープ、インラインコメントなどに対応する堅牢なパーサを実装。
      - OS 環境変数を protected として扱い .env.local では上書き可能だが、保護リストに含まれるキーは上書きしない。

  - データ関連 (kabusys.data)
    - ETL
      - pipeline.ETLResult を公開（kabusys.data.etl で再エクスポート）し、ETL 実行結果と品質問題・エラー情報を構造化。
      - ETLResult.to_dict() により品質問題を辞書化して監査ログ等に利用可能。
    - カレンダー管理
      - market_calendar を用いた JPX カレンダー管理機能を実装（calendar_update_job）。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB 登録値を優先し、未登録日は曜日ベース（日曜・土曜を休日扱い）でフォールバックする一貫した挙動。
      - 最大探索日数やバックフィル期間、健全性チェックなど安全策を実装。

  - 研究モジュール (kabusys.research)
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
      - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、平均売買代金、出来高比率を計算。
      - calc_value: raw_financials と株価から PER, ROE を計算（最新財務レコードを target_date 以前から取得）。
    - feature_exploration
      - calc_forward_returns: 指定ホライズンの将来リターン（fwd_*d）を一度のクエリで取得。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
      - rank: 同順位の平均ランクを扱うランク変換。
      - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）を計算。
    - 研究ユーティリティ
      - zscore_normalize を kabusys.data.stats から再利用して公開。

  - AI 関連 (kabusys.ai)
    - news_nlp（ニュースセンチメント）
      - score_news: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄毎に ai_scores テーブルへスコアを書き込み。
      - タイムウィンドウは前日 15:00 JST ～ 当日 08:30 JST（DB 比較は UTC naive datetime）を採用。
      - バッチサイズ、文字数/記事数トリム、結果のバリデーション、スコアクリッピング（±1.0）を実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。致命的でない失敗はスキップして継続（フェイルセーフ）。
      - レスポンス検証ロジックで JSON 抜き出しや unknown code の無視、数値チェックを行う。
      - 単体テスト向けに _call_openai_api を差し替え可能（unittest.mock.patch）。
    - regime_detector（市場レジーム判定）
      - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）と macro ニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
      - マクロニュースは news_nlp.calc_news_window により同様のウィンドウで抽出し、OpenAI を gpt-4o-mini で呼び出す。
      - API の冪等性・DB 書き込みは BEGIN/DELETE/INSERT/COMMIT を使用し失敗時は ROLLBACK を試行。
      - API 失敗やパース失敗時は macro_sentiment=0.0 にフォールバックして処理を継続。
      - LLM 呼び出しは news_nlp とは別に実装し、モジュール間の結合を低く保つ設計。

  - 実装の設計方針（全体）
    - ルックアヘッドバイアス防止のため、すべての関数が内部で datetime.today()/date.today() を参照しない設計（対象日を引数で受け取る）。
    - DuckDB を主なデータストアとして使用。SQL と Python を組み合わせた処理。
    - DB 書き込みは冪等性を意識（DELETE→INSERT、ON CONFLICT 等を想定）して実装。
    - OpenAI 呼び出しは JSON Mode を利用し、厳密な JSON 出力を期待するプロンプト設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 運用メモ
- OpenAI API キーは関数引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を送出するため運用時は設定必須。
- 自動 .env 読み込みをテスト時に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定する。
- DuckDB executemany に対する互換性配慮（空リスト渡しの回避）を行っているため、ETL 等での部分書き込みは安全に設計されています。
- デフォルトの OpenAI モデルは gpt-4o-mini。将来的なモデル差し替えは _MODEL 定数の変更で対応可能。

-----