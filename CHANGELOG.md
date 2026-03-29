CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

Unreleased
----------

- なし

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージ初期リリース。基本モジュール群を追加。
  - kabusys.config
    - .env / .env.local からの自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に検索するため、CWD に依存しない動作を実現。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。OS 環境変数を保護するため protected キーセットを導入。
    - .env パーサーは以下の仕様をサポート:
      - 行先頭のコメント行・空行を無視
      - export KEY=val 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープを処理して閉じクォートまでを値として扱う
      - クォートなしの場合、'#' の直前がスペースまたはタブの場合にのみ以降をコメントとして扱う（インラインコメント処理）
    - 自動ロードを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時に便利）。
    - Settings クラスを提供し、環境変数の必須チェック・デフォルト値・値検証（KABUSYS_ENV, LOG_LEVEL 等）を行う。
    - 必須キー例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。DB パスのデフォルトも定義（duckdb/sqlite）。

  - kabusys.ai.news_nlp
    - raw_news / news_symbols を基に銘柄別のニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む機能を実装。
    - ニュース収集ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（内部は UTC naive datetime）とする calc_news_window を実装。
    - バッチ処理: 最大 20 銘柄／API コール（_BATCH_SIZE=20）、1 銘柄あたりの記事数と文字数を制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）してトークン肥大化を抑制。
    - 再試行ロジック: 429（RateLimit）・ネットワーク断・タイムアウト・5xx サーバーエラーに対して指数バックオフでリトライ（最大回数 _MAX_RETRIES）。
    - レスポンス検証: JSON パース、"results" リストの存在、各要素の code/score 検証、未知コードの無視、スコアの数値・有限性チェック、スコアを ±1.0 にクリップ。
    - DB 書き込みは部分失敗に耐える設計: 取得済みコードのみ DELETE→INSERT の形で置換。DuckDB 0.10 の executemany 制約を考慮して空リスト時の呼び出し回避を行う。
    - テスト用の差し替えポイント: _call_openai_api を patch 可能にしてユニットテストしやすく設計。

  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドを防止（_calc_ma200_ratio）。
    - マクロニュースは news_nlp.calc_news_window に基づきウィンドウ内のタイトルを抽出し、OpenAI（gpt-4o-mini）で JSON レスポンスを期待してセンチメントを算出（_score_macro）。
    - エラー耐性: OpenAI API の障害・JSON パース失敗時は macro_sentiment を 0.0 にフォールバックして処理継続。リトライ/バックオフロジックを実装。
    - レジームスコア合成の仕様: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)、閾値により bull/bear/neutral を判定。
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で実装。失敗時は ROLLBACK を試みて例外を再送出。

  - kabusys.research
    - ファクター計算モジュールを実装（factor_research.py）:
      - calc_momentum: 約1/3/6ヶ月リターン、200日MA乖離を計算。データ不足時は None を返す。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。データ不足時の扱いを定義。
      - calc_value: raw_financials から最新の財務指標を取得し PER/ROE を計算。
    - feature_exploration モジュールを実装:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
      - calc_ic: スピアマン（ランク）相関による IC 計算（同順位は平均ランクで処理）。有効レコードが 3 未満なら None を返す。
      - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
      - rank: 値をランクに変換（同順位は平均ランク、round(..., 12) で丸めて ties の扱いを安定化）。

  - kabusys.data
    - calendar_management:
      - JPX カレンダーの保持と営業日判定ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
      - DB にカレンダーがない場合は曜日ベースのフォールバック（平日を営業日とする）。カレンダーが部分的にしか存在しない場合でも一貫した振る舞いを返す設計。
      - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等に更新。バックフィル（直近 _BACKFILL_DAYS）や健全性チェック（将来日付の異常検出）を実装。
    - pipeline / etl:
      - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
      - 差分取得・保存・品質チェックのためのパイプラインユーティリティ群（ETL の設計方針をコードに反映）。
      - 内部ユーティリティ: テーブル存在判定、最大日付取得などの補助関数を提供。
    - jquants_client との連携を想定した差分取得・保存の設計。

  - テスト支援
    - OpenAI 呼び出し（_call_openai_api）をモジュール単位で差し替え可能にしてユニットテスト容易性を確保。
    - 環境読み込みの自動化を KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

Changed
- 初版リリースのため該当なし。

Fixed
- 初版リリースのため該当なし。

Security
- センシティブな OS 環境変数の上書きを防ぐため、.env 読み込み時に既存 OS 環境変数を protected set として扱う実装を追加。

Notes / 設計上の重要点
- ルックアヘッドバイアス対策: すべての分析/スコア生成関数は内部で datetime.today()/date.today() を直接参照せず、必ず caller が指定する target_date に基づいて期間を決定します。
- OpenAI 連携は gpt-4o-mini を前提としており、JSON Mode（response_format={"type": "json_object"}）を利用して厳密な JSON を期待する設計。ただし外部エラーやフォーマット逸脱に対して堅牢なフォールバックロジックを持ちます。
- DuckDB 互換性: executemany における空リストの扱い（DuckDB 0.10）等、既知の互換性問題を回避するための実装上の配慮あり。
- 部分失敗の耐性: AI スコアの取得や ETL の一部処理が失敗しても他のデータや既存のスコアを破壊しないよう DB 書き込みは限定的に実施する方針。

Breaking Changes
- 初版リリースのため該当なし。

Deprecated
- 初版リリースのため該当なし。

Removed
- 初版リリースのため該当なし。

作者メモ / 利用者向け確認事項
- 初回利用時は .env.example を参考に必要な環境変数（OpenAI の OPENAI_API_KEY や J-Quants / kabu API の認証情報、Slack トークン等）を設定してください。Settings クラスは未設定の必須キーを参照すると ValueError を送出します。
- OpenAI の API 呼び出しはネットワークや API 側の応答に依存します。大量データで運用する場合はレート制限やコストに注意してください。

---