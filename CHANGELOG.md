CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
このファイルはコードベース（初期実装）から推測して作成しています。

[Unreleased]: -


[0.1.0] - 初回リリース
---------------------

Added
~~~~~

- パッケージ初期実装を追加（kabusys v0.1.0）。
  - パッケージの公開 API を定義（kabusys.__init__）。
  - モジュール群: data, research, ai, execution, strategy, monitoring を想定してエクスポート。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロード。
  - プロジェクトルート探索ロジックを実装（.git または pyproject.toml を基準に探索）。これにより CWD に依存しない自動ローディングが可能。
  - .env, .env.local の読み込み順序を実装（OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - export KEY=val 形式やクォート・エスケープ、行末コメントなど実用的な .env パースをサポート。
  - Settings クラスを提供し、J-Quants / kabu / LINE / DB /監視 / システム設定等をプロパティとして取得可能。
  - 環境変数値のバリデーション（KABUSYS_ENV, LOG_LEVEL 等）と is_live / is_paper / is_dev 判定を提供。
  - 必須項目未設定時は明確な ValueError を送出。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini, JSON mode）でセンチメントを付与し ai_scores テーブルへ保存する機能を実装（score_news）。
  - ニュース収集ウィンドウを JST ベースで定義（前日 15:00 JST ～ 当日 08:30 JST → UTC に変換）。
  - バッチサイズ、1銘柄あたりの最大記事数・文字数トリム、スコアの ±1.0 クリップなど実用上の制限を導入。
  - レスポンスの厳格なバリデーション実装（JSON 抽出、results 配列・型検査、未知コードの無視、数値検査）。
  - 429・タイムアウト・ネットワーク断・5xx に対する指数バックオフのリトライ実装。その他のエラーはスキップして継続するフェイルセーフ設計。
  - テスト容易性のため _call_openai_api を patch で差し替え可能に実装。
  - DuckDB への書き込みは部分失敗を避けるため、スコア取得済みコードのみ削除→挿入する冪等ロジック（BEGIN/DELETE/INSERT/COMMIT）を採用。DuckDB 特有の executemany の空リスト制約に対応。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存する機能を実装（score_regime）。
  - prices_daily と raw_news を参照して ma200_ratio とマクロ記事タイトルを取得。
  - OpenAI（gpt-4o-mini）を用いてマクロセンチメントを JSON で取得しスコア化。API エラー時は macro_sentiment=0.0 としてフェイルセーフ継続。
  - レジームスコアはクリップ処理を行い閾値に基づきラベル付け。
  - DB 書き込みは冪等（DELETE→INSERT）で行い、失敗時はロールバックし例外を伝播。

- データ（kabusys.data）
  - ETL パイプラインの結果を表現する ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を再エクスポート）。
  - calendar_management モジュールを実装:
    - JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day といった営業日関連ユーティリティ。
    - market_calendar が未取得の時は曜日ベース（土日除外）でフォールバックする設計。DB に一部データがある場合も DB 値優先で未登録日はフォールバックして一貫性を保つ。
    - 探索範囲上限 (_MAX_SEARCH_DAYS) により無限ループを防止。
    - JPX カレンダー保存は Idempotent を意識（jq.save_market_calendar を利用する想定）。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、保存（jquants_client 経由）、品質チェック（quality モジュール）を行う設計。
    - backfill を考慮した差分取得、部分失敗時にも既存データを保護する保存戦略。
    - ETLResult により取得/保存件数、品質問題、エラーを明確に返す。

- Research（kabusys.research）
  - ファクター計算（factor_research）を実装:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を参照し PER/ROE を計算（最新報告日の選択ロジックあり）。
  - 特徴量探索（feature_exploration）を実装:
    - calc_forward_returns: 任意ホライズンの将来リターンをまとめて取得する SQL を実装。horizons のバリデーションあり。
    - calc_ic: factor と将来リターンのスピアマン順位相関（IC）を実装（有効レコード <3 の場合は None）。
    - rank: 同順位時は平均ランクを返す実装（丸めで ties の検出漏れ対策）。
    - factor_summary: count/mean/std/min/max/median を算出する実装（None を除外）。

Changed
~~~~~~~

- 設計方針として全ての「日付参照」処理で datetime.today() / date.today() を直接参照しない実装方針を採用（ルックアヘッドバイアス防止）。関数は target_date を受け取りその基準で処理するようになっている点を明言。

Fixed
~~~~~

- 初期リリースのため既知の「bugfix」はなし。実装上のフェイルセーフ（API 失敗時のスコアフォールバック、DB 書き込み時のロールバック）を組み込み、部分失敗でも全体の安定性を保つ設計を適用。

Security
~~~~~~~~

- API キー・機密情報は環境変数から取得する設計。必須キー未設定時は ValueError を送出して明確化。
- .env 読み込みで OS 環境変数（既存キー）を保護する protected 機構を導入。
- KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途や秘密情報保護に有用）。

Notes / Known limitations
~~~~~~~~~~~~~~~~~~~~~~~~~

- OpenAI 呼び出しは gpt-4o-mini を前提に JSON Mode を利用する実装。将来の API 変更やモデル差し替え時は _call_openai_api の差し替え・更新が必要。
- news_nlp と regime_detector はそれぞれ独立して _call_openai_api を持ち、モジュール間でプライベート関数を共有しない設計（疎結合）。
- DuckDB のバージョン差異（executemany の空リスト不可等）に配慮した実装を行っているが、環境固有の差異は追加対応が必要となる場合がある。
- ETL / calendar 更新は外部 J-Quants クライアント（jquants_client）に依存しており、API 側の仕様変更は影響を与える可能性がある。

Compatibility
~~~~~~~~~~~~~

- DuckDB を想定した SQL 実装。
- OpenAI SDK（少なくとも chat.completions.create が利用可能な v1 系）を想定。
- Python 3.10+（型注釈に | を使用しているため）。

開発者向けメモ
~~~~~~~~~~~~~~

- テスト時は環境変数の自動ロードを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）するか、プロジェクトルート検出の挙動に注意してください。
- OpenAI への外部依存は各モジュールの _call_openai_api を patch してモック可能。
- DB 書き込みは冪等化を優先しており、部分成功時に他の既存データを消さない方針です。

---