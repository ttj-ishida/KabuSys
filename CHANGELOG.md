# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このプロジェクトの初期リリース情報は以下のとおりです。

全般的な注意
- 本リリースでは DuckDB を内部データストアとして使用し、OpenAI（gpt-4o-mini）へ API 呼び出しを行う NLP/レジーム判定機能を含みます。
- 日付処理はルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を直接参照しない設計になっています（関数呼び出し時に target_date を明示的に渡す方式）。
- OpenAI API キー未設定時には ValueError を送出して通知します（api_key 引数または環境変数 OPENAI_API_KEY を使用）。

[0.1.0] - 2026-03-29
Added
- パッケージ基盤
  - パッケージバージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API の __all__ に data, strategy, execution, monitoring を登録。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートの検出は .git または pyproject.toml を探索して行う（CWD 非依存）。
    - 読み込み優先順位は OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーは以下に対応：
    - コメント行・空行・export プレフィックスの扱い
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - クォート無し行でのインラインコメント判定（直前が空白／タブの場合）
  - 環境変数必須チェック用の _require と、Settings クラスを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などをプロパティとして提供。
    - DUCKDB_PATH / SQLITE_PATH の既定値、KABUSYS_ENV / LOG_LEVEL の検証ロジック（許容値チェック）を実装。
    - is_live / is_paper / is_dev の便利プロパティを実装。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して、銘柄毎にニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込み。
    - 処理の特徴：
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 検索）
      - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字でトリム
      - JSON Mode を用いた API 呼び出しとレスポンスバリデーション（余分な前後テキストが混在するケースの復元対策を含む）
      - リトライ（429/ネットワーク断/タイムアウト/5xx）は指数バックオフ、その他エラーはスキップして継続（フェイルセーフ設計）
      - スコアは ±1.0 にクリップ
      - DB 書き込みは冪等的（対象コードのみ DELETE → INSERT）で、部分失敗時に既存データを保護する実装
    - 公開関数:
      - calc_news_window(target_date) -> (window_start, window_end)
      - score_news(conn, target_date, api_key=None) -> 書き込んだ銘柄数
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（Nikkei-linked ETF）の 200 日 MA 乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（'bull'/'neutral'/'bear'）。
    - 処理の特徴：
      - 1321 の終値から MA200 乖離を計算（target_date 未満のデータのみ使用、データ不足時は中立扱い）
      - raw_news からマクロキーワードでフィルタしたタイトルを抽出し、OpenAI で macro_sentiment を評価（記事なし時は LLM 呼び出しを行わず 0.0）
      - API 呼び出しはリトライ（指数バックオフ）を行い、最終的に失敗した場合は macro_sentiment=0.0 で継続
      - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)
      - market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）
    - 公開関数:
      - score_regime(conn, target_date, api_key=None) -> 1（成功）
    - マクロキーワードやモデル名、リトライ回数などの定数はモジュール内に定義。

- データ（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）を使った営業日判定と夜間バッチ更新ロジックを実装。
    - 提供関数:
      - is_trading_day(conn, d): 営業日判定（DB 優先、未登録は曜日フォールバック）
      - next_trading_day(conn, d), prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
      - is_sq_day(conn, d)
      - calendar_update_job(conn, lookahead_days=90): J-Quants 経由で差分取得・保存（バックフィル、健全性チェック含む）
    - 設計上の注意:
      - market_calendar 未取得時は曜日ベース（週末を休日とする）でフォールバック
      - 最大探索日数の上限を設定し無限ループを防止
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - ETLResult は取得件数・保存件数・品質問題・エラーを格納し、has_errors / has_quality_errors / to_dict を提供。
    - pipeline モジュール内ユーティリティ：
      - テーブル存在チェック、最大日付取得、カレンダーヘルパー（_adjust_to_trading_day など）の実装方針と基本処理を準備。
    - 設計方針:
      - 差分更新（営業日単位）、バックフィル、品質チェックで問題があっても ETL を継続して問題を集約する（Fail-Fast ではない）。
  - jquants_client との連携ポイントを想定（fetch/save の呼び出しを行う実装を配置する設計）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum, Value, Volatility, Liquidity 等の計量ファクターを DuckDB 内の prices_daily / raw_financials を参照して計算。
    - 提供関数:
      - calc_momentum(conn, target_date) -> リターン類（mom_1m, mom_3m, mom_6m, ma200_dev）
      - calc_volatility(conn, target_date) -> atr_20, atr_pct, avg_turnover, volume_ratio
      - calc_value(conn, target_date) -> per, roe
    - 設計上の注意:
      - 必要データが不足する銘柄は None を返す
      - SQL ウィンドウ関数を多用して効率的に集計
  - 特徴量探索（kabusys.research.feature_exploration）
    - 研究用途のユーティリティ群を実装（外部依存は無し、標準ライブラリのみ）。
    - 提供関数:
      - calc_forward_returns(conn, target_date, horizons=None) -> 各ホライズンの将来リターン
      - calc_ic(factor_records, forward_records, factor_col, return_col) -> Spearman の rank-correlation（IC）
      - rank(values) -> ランク（同順位は平均ランク）
      - factor_summary(records, columns) -> 各カラムの count/mean/std/min/max/median
    - 入力検証やエッジケース（horizons の妥当性、最小有効件数チェックなど）に配慮。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- OpenAI/外部 API キーや各種パスワードは環境変数経由で取得する設計。自動 .env ロードを行うため、運用時は .env の管理に注意してください。

移行 / 利用上の注意
- OpenAI API を利用する機能（news_nlp, regime_detector）は API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須です。未設定時は ValueError が発生します。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など）が前提となっています。実行前に期待されるテーブル定義・型を整えてください。
- ETL / calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）を通じてデータ取得・保存を行う想定です。実運用では適切な API クレデンシャルの配置・権限管理を行ってください。
- ニュースの時間ウィンドウやレジーム判定の閾値・重みはモジュール定数として定義されています。運用要件に応じて調整が可能です。

今後
- 本リリースは基盤機能の初期実装です。今後の予定例：
  - strategy / execution / monitoring の具体実装（本パッケージの __all__ に含まれるが未実装のモジュール群の追加）
  - テストカバレッジ拡充、CI / デプロイ手順の整備
  - 設定のより柔軟な注入（例: 設定ファイルのサポート、Secrets 管理統合）
  - モデル・プロンプト改善、レスポンス信頼性向上策（校正、複数モデルのアンサンブル等）

-----

この CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして公開する前に、差し替えや補足（リリース日・著者・追加変更点など）を行ってください。