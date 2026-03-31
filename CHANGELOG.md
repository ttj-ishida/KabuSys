CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
-------------

（次版の変更をここに記載してください）

[0.1.0] - 2026-03-31
-------------------

Added
- 初回公開リリース (0.1.0)
  - パッケージ概要: kabusys - 日本株自動売買システムの基盤モジュール群を提供。
    - パッケージエクスポート: data, strategy, execution, monitoring（src/kabusys/__init__.py）
  - 環境設定/ローダー (kabusys.config)
    - .env と .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
    - 読み込み順序: OS環境変数 > .env.local > .env。既存の OS 環境変数は protected として保護される。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - .env パーサ実装:
      - コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
      - 無効行は無視。
    - Settings クラス:
      - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを提供。
      - env（development/paper_trading/live）の検証、LOG_LEVEL の検証、便利な is_live/is_paper/is_dev プロパティ。
      - DuckDB / SQLite / PID ファイルの既定パスとしきい値 (CPU/MEM/DISK) を取得。
      - 必須変数未設定時には ValueError を送出する _require 実装。

  - データ基盤モジュール (kabusys.data)
    - カレンダー管理 (calendar_management)
      - JPX マーケットカレンダーの夜間バッチ更新ロジック（calendar_update_job）。
      - market_calendar テーブルを優先して営業日判定を行い、未登録日は曜日ベースでフォールバックする設計。
      - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供。
      - 最大探索日数制限 (_MAX_SEARCH_DAYS)、バックフィル、健全性チェック等の安全策を実装。
      - J-Quants クライアント経由で差分取得 → 冪等保存（ON CONFLICT 形式想定）。
    - ETL パイプライン (pipeline, etl)
      - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
      - 差分更新・バックフィル・品質チェック（quality モジュール連携）を想定した設計。
      - _get_max_date / _table_exists 等のユーティリティを実装（DuckDB 前提）。
      - ETLResult は品質問題やエラーの集約、has_errors / has_quality_errors や辞書化 to_dict を提供。

  - AI（自然言語）モジュール (kabusys.ai)
    - ニュース NLP（score_news）
      - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントを算出。
      - JST ベースのニュース時間窓計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供（UTC naive datetime を返す）。
      - バッチサイズ、1銘柄あたりの最大記事数・文字数トリム、最大リトライ等の定数を定義。
      - OpenAI API 呼び出しは JSON Mode（厳密 JSON）を前提とし、レスポンスの堅牢なバリデーションを実施（部分的に余分なテキストが混入するケースも復元）。
      - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフで再試行。その他エラーはスキップして継続（フェイルセーフ）。
      - スコアは ±1.0 にクリップ。取得成功銘柄のみ ai_scores テーブルの該当行を置換（DELETE→INSERT、部分失敗時に既存データを保護）。
      - テスト容易性のため、OpenAI 呼び出し関数 _call_openai_api を patch で差し替え可能。
    - 市場レジーム判定（score_regime）
      - ETF 1321（日経225連動型）の 200 日移動平均乖離 (ma200_ratio) とマクロニュース LLM センチメントを重み付き合成（MA70% / マクロ30%）してレジーム（bull/neutral/bear）を判定。
      - prices_daily から target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止する設計。
      - マクロニュースは news_nlp.calc_news_window によりウィンドウを計算して titles を抽出、OpenAI（gpt-4o-mini）で -1.0〜1.0 のスコアを取得。
      - API 呼び出し失敗時は macro_sentiment = 0.0 でフォールバック（警告ログ出力）するフェイルセーフ。
      - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
      - OpenAI 呼び出し用のクライアントはモジュール内で生成し、news_nlp と内部関数を共有しないことで結合度を下げている。
  - リサーチ（研究）モジュール (kabusys.research)
    - factor_research
      - モメンタム: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を calc_momentum で計算。
      - ボラティリティ/流動性: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を calc_volatility で計算。
      - バリュー: raw_financials と prices_daily を組み合わせて PER / ROE を calc_value で計算（EPS が 0/欠損の場合は None）。
      - DuckDB 上で SQL ウィンドウ関数を用いて効率的に計算。データ不足時は None を返す扱い。
    - feature_exploration
      - 将来リターン計算（calc_forward_returns）: 任意ホライズン（デフォルト [1,5,21]）に対応。horizons の妥当性チェックあり。
      - IC（calc_ic）: Spearman（ランク相関）に準拠してファクターの有効性を評価。データ不足時は None を返す。
      - ランク関数（rank）: 同順位は平均ランクとする実装、丸めで ties 漏れを抑制。
      - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出（None 値は除外）。
    - research パッケージは一部ユーティリティを kabusys.data.stats から再利用する設計。

Other notable implementation details
- DuckDB を主要な分析 DB として想定し、SQL と Python の組合せで処理を行う。DuckDB のバージョン差異（executemany の空リスト制約等）を考慮した実装。
- 日付/時間の扱い:
  - すべての日付は date オブジェクトで扱い、timezone 混入を避ける方針。
  - ニュースウィンドウは JST を基準に計算し、DB 比較は UTC naive datetime を使用。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を内部ロジックで参照しない設計（target_date を明示的に受け取る）。
- ロギング: 各モジュールで詳細な info/debug/warning を出力し、エラー時は stacktrace を出す箇所がある（logger.exception 等）。
- OpenAI API の取り扱い:
  - モデル: gpt-4o-mini を想定。
  - JSON Mode（response_format={"type": "json_object"}）を使用しつつ、余計なテキスト混入に耐える復元処理を実装。
  - 再試行方針（指数バックオフ）、5xx 判定、429/タイムアウト/ネットワーク断の扱いを明確化。
- フェイルセーフ設計:
  - API/外部依存の失敗時に例外で全体を止めない（代替値で継続、該当コードのみスキップ）。
  - DB 書き込みは可能な限り冪等性を保つ（DELETE→INSERT、ON CONFLICT 想定）。
- テスト支援:
  - OpenAI 呼び出し等はモジュール内 helper を patch で置き換え可能にしてユニットテストを容易にしている。

Known limitations / TODO（現時点の実装メモ）
- Strategy / Execution / Monitoring の具体的な実装はこのスナップショットでは含まれていない（パッケージエクスポートは存在）。
- 一部のユーティリティ（jquants_client, quality, data.stats など）は別モジュールを参照しており、その実装に依存する。
- PBR・配当利回り等のバリュー指標は未実装（calc_value の注記参照）。

注記
- 本 CHANGELOG はソースコードの実装内容およびモジュール内ドキュメント文字列から推測して作成しています。動作や公開 API の正式仕様は実際のリポジトリのドキュメントやテストを参照してください。