Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。
このプロジェクトは https://keepachangelog.com/ja/ の慣例に従います。

現在バージョン
--------------

- [0.1.0] - 2026-04-04

[0.1.0] - 2026-04-04
--------------------

Added
- 基本パッケージ初期実装を追加。
  - src/kabusys/__init__.py にバージョン情報 (__version__ = "0.1.0") と公開モジュール一覧を定義。
- 環境変数 / 設定管理機能を追加（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト支援）。
  - .env パーサは export な形式やシングル/ダブルクォート、エスケープ、インラインコメントに対応。
  - Settings クラスを提供し、各種必須/任意設定（J-Quants、kabuAPI、LINE、DB パス、監視設定等）へのプロパティアクセスを提供。
  - 設定値に対するバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。
  - 必須環境変数未設定時は ValueError を発生させる _require ヘルパーを実装。
- AI 関連: ニュース NLP と市場レジーム判定を追加（src/kabusys/ai/*）。
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI (gpt-4o-mini) によりセンチメントスコアを計算して ai_scores テーブルへ書き込む。
    - JST の前日 15:00 ～ 当日 08:30 のウィンドウ計算（UTC 変換）を calc_news_window で提供。
    - バッチ処理（1 API 呼び出し当たり最大 20 銘柄）、1 銘柄あたり記事・文字数上限でトークン肥大化に対処。
    - OpenAI への呼び出しは JSON Mode を利用し、429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。
    - レスポンスの厳密なバリデーション処理とスコアの ±1.0 クリップ。
    - API 失敗時はフェイルセーフとして該当チャンクをスキップ、処理継続。
  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
    - OpenAI 呼び出しは独立実装（モジュール結合を避ける設計）。API エラー時は macro_sentiment=0.0 にフォールバックして継続。
    - レジーム算出ロジック、閾値（BULL/BEAR）を備え、market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止設計: datetime.today()/date.today() に依存しないクエリ条件（date < target_date 等）。
- 研究（research）モジュールを追加（src/kabusys/research/*）。
  - factor_research: calc_momentum / calc_value / calc_volatility を実装。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）。
    - Value: raw_financials から最新財務を取得し PER / ROE を計算。
    - Volatility: 20 日 ATR / ATR 比率 / 20 日平均売買代金 / 出来高比率。
    - DuckDB SQL を活用し、prices_daily / raw_financials のみ参照（実売買 API には接続しない）。
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank を実装。
    - 将来リターン計算（horizons の検証、単一クエリで取得）。
    - Spearman（ランク相関）ベースの IC 計算、最小有効レコード数判定。
    - 統計サマリー（count/mean/std/min/max/median）。
    - 標準ライブラリのみで実装（pandas 非依存）。
  - research パッケージは data.stats の zscore_normalize を再エクスポート。
- データ基盤（data）モジュールを追加（src/kabusys/data/*）。
  - calendar_management:
    - JPX カレンダー管理ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - market_calendar が存在しない場合は曜日ベースでフォールバック（週末を休日扱い）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェック含む）。
    - 最大探索日数などの保護ロジックを実装（無限ループ防止）。
    - jquants_client とのインターフェースを使用（fetch/save を委譲）。
  - pipeline / etl:
    - ETLResult データクラスを実装して ETL 実行結果を集約（取得数・保存数・品質問題・エラー一覧など）。
    - ETL パイプラインの設計方針（差分更新、backfill、品質チェックの集約）を定義。
    - 内部ユーティリティ（テーブル存在確認、最大日付取得ユーティリティ等）を実装。
  - etl は pipeline.ETLResult を公開（data.etl）。
- テスト容易性・堅牢性のため設計上の配慮を多数実装。
  - OpenAI 呼び出し部分はテスト時にモック可能（_call_openai_api を patch して差し替え）。
  - DB 書き込みは冪等性を重視（DELETE → INSERT のパターン、ON CONFLICT の想定）。
  - "ルックアヘッドバイアス" を避けるため、内部で現在時刻を参照しない API 設計。
  - DuckDB 0.10 の挙動（executemany 空リスト不可等）に配慮した実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 環境変数（API キー等）は Settings 経由で必須チェックを行う。未設定時は ValueError を投げ、誤った公開を防止。
- .env 自動読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。

注意事項 / 既知の挙動
- OpenAI への API 呼び出しに失敗した場合（RateLimit／タイムアウト／5xx 等）は、該当箇所を安全にデグレード（macro_sentiment=0.0 やチャンクスキップ）して処理を継続します。これにより ETL 全体やレジーム判定が停止しない設計です。
- news_nlp は raw_news.datetime が UTC で保存されている前提です。DB 側の時間基準に注意してください。
- .env のパースは一般的なケースに対応しますが、極端に特殊なフォーマットは想定外の振る舞いになる可能性があります。
- DuckDB のバージョン依存（executemany の空リスト扱い等）に配慮した実装を行っていますが、実行環境の DuckDB バージョンによっては追加調整が必要になる場合があります。

開発上の設計方針（抜粋）
- ルックアヘッドバイアス防止: 日付条件は target_date 未満/以前制約や外部渡しの target_date に依存し、date.today() を直接参照しない。
- 可観測性と堅牢性: 重要な処理はログ出力、失敗時のフォールバック、トランザクションの ROLLBACK 保護を実装。
- モジュール間結合の最小化: OpenAI 呼び出しや内部ユーティリティはモジュールごとに独立実装しテスト可能性を確保。

今後の予定（例）
- ETL 実行ラッパーの CLI / スケジューラ統合
- ai モデルの入替やプロンプト改善のためのチューニング
- more comprehensive unit/integration tests の追加
- ドキュメント（API リファレンス・運用ガイド）の拡充

署名
----
この CHANGELOG はソースコードを解析して推測に基づき作成しています。実際のリリースノートとして公開する際は、実装担当者によるレビュー・修正を推奨します。