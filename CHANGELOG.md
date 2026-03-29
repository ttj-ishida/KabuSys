CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。このプロジェクトは Keep a Changelog の形式に準拠し、Semantic Versioning に従います。

Unreleased
----------

- （なし）

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリース。KabuSys 日本株自動売買システムのコア機能を公開。
  - パッケージ初期化
    - kabusys/__init__.py にてバージョン 0.1.0 を設定。公開サブパッケージ: data, research, ai, execution, monitoring（モジュール構造に基づく公開意図）。
  - 設定 / 環境変数管理（kabusys.config）
    - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
      - プロジェクトルートは .git または pyproject.toml を基準に特定（CWD に依存しない実装）。
      - 読み込み順序: OS 環境変数 > .env.local > .env。
      - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env のパースは export 構文、クォート（シングル/ダブル）やバックスラッシュエスケープ、インラインコメントを考慮。
    - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等）。
      - 必須環境変数取得時は未設定なら ValueError を発生させる（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
      - デフォルトの DB パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db。
      - KABUSYS_ENV（development/paper_trading/live）・LOG_LEVEL 値検証を実装。
  - AI モジュール（kabusys.ai）
    - news_nlp（kabusys.ai.news_nlp）
      - raw_news と news_symbols を集約して銘柄ごとのニュースを LLM（gpt-4o-mini）に渡し、銘柄別センチメントを ai_scores テーブルへ書き込む機能を実装。
      - タイムウィンドウは JST ベース（前日 15:00 ～ 当日 08:30 JST）を UTC に変換して処理。
      - バッチ処理（1 バッチ最大 20 銘柄）、1 銘柄あたり記事上限・文字数トリム制御を備える。
      - API 呼び出しでの 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフ・リトライを実装。
      - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score の存在、スコア数値化、既知コードのみ採用、±1.0 クリップ）。
      - 部分成功時に既存スコアを保護するため、書き込みは対象コードに限定して DELETE → INSERT を行う（トランザクション、ROLLBACK 保護）。
      - テスト容易性: OpenAI 呼び出しは _call_openai_api を patch 可能にしている。
    - regime_detector（kabusys.ai.regime_detector）
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ書き込む機能を実装。
      - マクロニュース抽出は predefined マクロキーワードリストに基づき raw_news からタイトルを取得。
      - OpenAI 呼び出しは gpt-4o-mini を使用、JSON 出力を期待。API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフを実装。
      - レジーム判定はスコアをクリップし閾値判定（bull/bear/neutral）、書き込みは冪等トランザクション（BEGIN/DELETE/INSERT/COMMIT）で行う。
  - Data モジュール（kabusys.data）
    - calendar_management（kabusys.data.calendar_management）
      - JPX マーケットカレンダー管理（market_calendar）を提供。祝日・半日取引・SQ 日を扱うロジック。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
      - DB にカレンダーがない場合は曜日ベースのフォールバックを用意。DB 値優先・未登録日は曜日で補完する一貫した挙動。
      - calendar_update_job により J-Quants API から差分取得し冪等に保存（バックフィル・健全性チェックを実装）。
    - pipeline / etl（kabusys.data.pipeline / kabusys.data.etl）
      - ETLResult データクラスを公開（取得件数／保存件数／品質問題／エラー等の集約）。
      - ETL パイプラインの骨格を実装（差分更新、バックフィル、idempotent 保存、品質チェックの収集方針）。
      - DuckDB との最大日付取得、テーブル存在確認等のユーティリティを実装。
  - Research モジュール（kabusys.research）
    - factor_research（kabusys.research.factor_research）
      - Momentum / Value / Volatility / Liquidity 等の定量ファクター計算を実装:
        - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
        - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
        - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS が 0/欠損時は None）。
      - DuckDB の SQL ウィンドウ関数を活用し、営業日ベースのラグを扱う実装。
    - feature_exploration（kabusys.research.feature_exploration）
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）で将来リターンを計算。
      - calc_ic: スピアマンランク相関（IC）を実装（結合・欠損除外・最小有効レコード数チェック）。
      - rank: 同順位は平均ランクで扱うランク変換を実装（小数丸めで ties の誤検出を防止）。
      - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算する統計サマリー。
    - research パッケージの __all__ にて主要関数を再エクスポート。
  - 汎用実装方針（横断的）
    - ルックアヘッドバイアス回避: datetime.today() / date.today() を関数内部から直接参照しない設計（target_date を外部から受け取る）。
    - DB 書き込みはトランザクションで行い、例外発生時は ROLLBACK を試みる。ROLLBACK 失敗は警告ログ。
    - LLM 関連では API 失敗時に処理を継続する（フェイルセーフ的に 0.0 を使用、例外は上位に伝播しない）方針。
    - テスト容易性のため、内部の API 呼び出し関数は patch できるように分離。

Security / Ops
- API キー取り扱い:
  - OpenAI: OPENAI_API_KEY 環境変数または各関数の api_key 引数で指定。未設定時は ValueError。
  - 他の必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
- 自動 .env ロードを止めたい場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

Notes / Limitations
- 現バージョンでは一部指標（例: PBR・配当利回り）は未実装（calc_value 注記参照）。
- ai_scores / market_regime 等のテーブルスキーマや jquants_client 実装は外部（別モジュール）に依存。実行前に適切な DuckDB スキーマ・外部クライアント実装を用意してください。
- news_nlp/regime_detector は gpt-4o-mini を前提とした JSON Mode を期待するため、OpenAI SDK の挙動変更に注意が必要です。
- 一部 DuckDB バインド（executemany の空リスト等）への互換性考慮が実装されていますが、使用する DuckDB バージョンによって挙動差異が生じる可能性があります。

Acknowledgements
- 本実装は内部設計注釈（DataPlatform.md, StrategyModel.md）に基づくプロジェクト初期実装です。

-- End of CHANGELOG --