CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣習に従い、セマンティックバージョニングを使用します。

[Unreleased]
------------

- （現状なし）開発中の変更はここに記載します。

[0.1.0] - 2026-03-31
-------------------

Added
- 初回リリース。ライブラリ名: KabuSys（日本株自動売買支援ツールキット）。
- パッケージ公開インターフェース:
  - src/kabusys/__init__.py により外部から data, strategy, execution, monitoring を利用可能に設定。
- 環境設定管理:
  - src/kabusys/config.py: .env ファイルおよび環境変数の自動読み込み機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD に依存しない実装）。
    - .env パースの強化:
      - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、行末コメント判定ロジック等。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - OS 環境変数を保護する protected パラメータを用いた上書き制御。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル等のプロパティを定義（必須変数未設定時は ValueError を送出）。
    - KABUSYS_ENV と LOG_LEVEL の検証ロジックを実装。
- AI（自然言語処理）モジュール:
  - src/kabusys/ai/news_nlp.py:
    - raw_news から銘柄毎に記事を集約し OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を行い ai_scores テーブルへ書き込む処理を実装。
    - 処理内容:
      - JST ベースのニュースウィンドウ計算（calc_news_window）。
      - 1 銘柄あたり記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大バッチサイズ _BATCH_SIZE（デフォルト 20）で分割して API 呼び出し。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ。
      - レスポンスのバリデーション（JSON 抽出・results リスト・code/score チェック）とスコアの ±1.0 クリップ。
      - DuckDB executemany の互換性考慮（空リストバインド回避）。
    - テスト容易性:
      - OpenAI 呼び出し部分は _call_openai_api を patch して差し替え可能。
  - src/kabusys/ai/regime_detector.py:
    - ETF（1321）200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みを行う処理を実装。
    - 設計上の特徴:
      - ルックアヘッドバイアス防止（date 引数ベース、datetime.today() を直接参照しない）。
      - マクロキーワードで raw_news をフィルタリングして LLM に渡す。
      - OpenAI 呼び出しに対するリトライ・フォールバック（最終的に macro_sentiment=0.0）やレスポンス JSON パース保護。
      - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等操作。失敗時は ROLLBACK を試行。
    - テスト容易性:
      - news_nlp と独立して _call_openai_api を定義し、モジュール間で private 関数を共有しない設計。
- リサーチ（ファクター計算）モジュール:
  - src/kabusys/research/factor_research.py:
    - Momentum / Volatility / Value 系ファクター計算を実装:
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率（データ不足時の None ハンドリング）。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
      - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算。
    - DuckDB のウィンドウ関数を活用した SQL 中心の実装で外部 API への依存なし。
  - src/kabusys/research/feature_exploration.py:
    - 特徴量探索ユーティリティを実装:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを算出（ホライズンチェックと範囲制御）。
      - calc_ic: ファクターと将来リターンのスピアマン ランク相関（IC）計算（NA の除外、3 件未満で None）。
      - rank: 同順位は平均ランクとするランク関数（丸め処理で浮動小数点の tie を安定化）。
      - factor_summary: count/mean/std/min/max/median の統計サマリー。
    - すべて標準ライブラリのみで実装（pandas 等に依存しない）。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート。
- データ管理モジュール:
  - src/kabusys/data/calendar_management.py:
    - JPX マーケットカレンダーを扱うユーティリティを実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
      - market_calendar が未取得の場合は曜日ベース（週末除外）でのフォールバックを行う一貫した判定ロジック。
      - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック含む）。
      - _MAX_SEARCH_DAYS による探索上限で無限ループ回避。
    - jquants_client との連携を前提に実装（fetch/save を呼び出す）。
  - src/kabusys/data/pipeline.py:
    - ETL パイプラインの骨格と ETLResult データクラスを実装。
      - 差分取得、保存、品質チェック（quality モジュール）を意識した設計。
      - ETLResult は品質問題・エラーの集約、has_errors / has_quality_errors、辞書変換（監査ログ向け）をサポート。
    - 内部ユーティリティ（テーブル存在確認、最大日付取得等）を実装。
  - src/kabusys/data/etl.py:
    - pipeline.ETLResult を公開 API として再エクスポート。
  - 互換性考慮:
    - DuckDB の executemany や日時戻り値の型不確定性（date あるいは ISO 文字列）を扱うためのガードを実装。
- テスト＆運用性向上のための設計上の注意点（ドキュメントに明示）:
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を関数内部で直接参照しない実装方針を採用（target_date を引数で受ける）。
  - OpenAI 呼び出し箇所は patch で差し替え可能にしてユニットテストを容易にしている。
  - API 失敗時は例外を上位に伝播させる箇所と、フェイルセーフとして処理を継続する箇所（macro_sentiment=0、スコアスキップ等）を明確に分離。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- （該当なし）

Notes / Implementation details
- OpenAI SDK に関連する例外ハンドリング（RateLimitError / APIConnectionError / APITimeoutError / APIError）を各所で考慮しており、5xx 判定や status_code 存在しないケースへの防御を実装しています。
- DB 書き込みは可能な限り冪等性を保つ（DELETE → INSERT や ON CONFLICT 想定）実装になっています。
- DuckDB 固有の振る舞い（executemany の空リスト不可や日付型戻り値）を扱うための対処が施されています。

開発者向け補足
- 自動 .env ロードを無効化したいテストや特殊環境では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API 呼び出しをユニットテストでモックする場合は各モジュール内の _call_openai_api を patch してください（news_nlp._call_openai_api / regime_detector._call_openai_api）。
- settings の必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を適切に設定してから実行してください。未設定時は ValueError が発生します。