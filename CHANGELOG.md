Keep a Changelog
=================

すべての注目すべき変更を時系列に記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-29
-------------------

初回リリース。KabuSys のコアライブラリを公開しました。以下のモジュール／機能を実装しています。

Added
- パッケージ
  - kabusys パッケージを追加。バージョン: 0.1.0（src/kabusys/__init__.py）。
  - パッケージの公開モジュール: data, strategy, execution, monitoring を __all__ として公開。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動ロードする機能を実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定。
    - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
  - .env ファイルの行パーサ実装:
    - コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants、kabu ステーション、Slack、データベース、システム設定のプロパティを提供。
    - env (development/paper_trading/live)・log_level のバリデーション。
    - duckdb/sqlite のデフォルトパス設定と Path 型返却。
    - 必須環境変数未設定時には ValueError を送出（明示的エラーメッセージ）。

- AI 関連 (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode で銘柄ごとのセンチメントを取得。
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と照合）。
      - バッチ処理（デフォルトで最大 20 銘柄 / API コール）、各銘柄につき最大記事数／最大文字数でトリム。
      - リトライ戦略: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ。
      - レスポンスのバリデーション（JSON 抽出、results リスト、code/score の検証、数値チェック、±1.0 にクリップ）。
      - 書き込みは部分置換（該当 date + code の DELETE → INSERT）で冪等性を確保。DuckDB の executemany の互換性考慮あり。
      - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError。
    - calc_news_window(target_date) を公開（ニュース収集ウィンドウを返すユーティリティ）。
    - テスト容易性のため _call_openai_api を内部で分離（モック可能）。
    - フェイルセーフ: API 失敗やパース失敗時はスキップして継続（例外を上げず空スコア扱い）。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321（日経225連動型）の 200 日移動平均乖離とマクロセンチメントを合成して市場レジーム（bull/neutral/bear）を判定。
      - ma200_ratio（過去 200 日、target_date 未満のデータのみを使用）計算。データ不足時は中立 (1.0) を採用。
      - マクロニュースは news_nlp.calc_news_window を利用してフィルタし、OpenAI で macro_sentiment を評価（記事がない場合は LLM 呼び出しなし）。
      - 合成スコア: 70% を MA 偏差（スケール適用）、30% をマクロセンチメントに割当。閾値で bull/neutral/bear を決定。
      - DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）で実装。
      - リトライや API エラー処理を実装し、全リトライ失敗時は macro_sentiment を 0.0 にフォールバック。
      - API キー取得は引数または環境変数 OPENAI_API_KEY。未設定時は ValueError。

- データ基盤・ETL (src/kabusys/data)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX マーケットカレンダーを管理するユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
      - calendar_update_job(conn, lookahead_days=90) により J-Quants API から差分取得して market_calendar を冪等更新（fetch/save は jquants_client に委譲）。
    - 設計ポイント:
      - market_calendar 未取得時は曜日（平日）ベースでフォールバック。
      - DB 登録がある場合は DB を優先、未登録日は曜日フォールバックで一貫性を保つ。
      - 最大探索範囲制限 (_MAX_SEARCH_DAYS=60) やバックフィル、健全性チェックを実装。

  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを追加（ETL 実行の集計／品質問題／エラー集約）。
    - pipeline モジュールの公開インターフェースとして ETLResult を再エクスポート。

  - ETL 設計（pipeline モジュールに記載の方針）
    - 差分更新、バックフィル、品質チェックの設計方針を明記。
    - DuckDB 上での最大日付取得やテーブル存在チェック等のユーティリティを実装。

- リサーチ・ファクター (src/kabusys/research)
  - factor_research.py
    - calc_momentum(conn, target_date)
      - mom_1m/3m/6m、ma200_dev（200日 MA 乖離率）を計算。データ不足時は None。
      - DuckDB のウィンドウ関数を活用して効率的に算出。
    - calc_volatility(conn, target_date)
      - atr_20（20日 ATR）、atr_pct、avg_turnover（20日平均売買代金）、volume_ratio を計算。
      - true_range 計算で high/low/prev_close の NULL 伝播を明示的に扱う実装。
    - calc_value(conn, target_date)
      - raw_financials から直近の財務データを取得し PER（EPS が有効な場合）と ROE を計算。
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=[1,5,21])
      - 指定ホライズン（営業日ベースではなく連続レコード数）の将来リターンを一度のクエリで取得。
      - horizons は正の整数（<=252）でバリデーション。
    - calc_ic(factor_records, forward_records, factor_col, return_col)
      - スピアマンのランク相関（Information Coefficient）を計算。十分な有効レコードがない場合は None。
    - rank(values)
      - 同順位は平均ランクを返す実装（丸めで ties 検出の安定化を行う）。
    - factor_summary(records, columns)
      - count/mean/std/min/max/median を計算する統計サマリー。

- その他
  - モジュール初期化子（__init__.py）で ai と research の主要関数をエクスポート。
  - DuckDB を前提にした設計と互換性対策（空リストの executemany 回避、リストバインドの注意など）を随所に反映。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーや各種シークレットは環境変数経由で取り扱う想定（Settings で必須チェック）。.env 自動ロードは明示的にオフにできる。

Notes / Known limitations
- OpenAI のモデルと JSON Mode を利用しているため、実行には OPENAI_API_KEY の設定が必要。
- J-Quants 連携の箇所は jquants_client（別モジュール）に依存。実行環境で適切にクライアント実装を用意する必要あり。
- DuckDB の仕様差分により一部 SQL バインドや executemany の取り扱いで注意（コード内に互換性対応あり）。
- strategy / execution / monitoring パッケージは __all__ で公開されているが、本リリースでの実装状況に応じて追加の実装やドキュメントが必要です。

導入・使用メモ（簡易）
- 環境変数を .env に定義してプロジェクトルートに配置するか、OS 環境に設定してください。
  - 例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など。
- settings = kabusys.config.settings から各種設定値にアクセス可能です。
- ニュースセンチメント算出例:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=None)
- レジーム判定例:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=None)

貢献
- 初回リリース。今後の機能追加・改善・バグ修正は CHANGELOG の Unreleased セクションに記載予定です。

---