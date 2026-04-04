# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
次のバージョンポリシーを仮定しています: 初期リリース v0.1.0。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04

初回公開リリース。日本株自動売買システムのデータ取得／研究／AI評価／ユーティリティ基盤を提供します。

### Added
- パッケージ全体
  - 基本パッケージ情報: kabusys (version = 0.1.0) を追加。
  - モジュール公開ポリシー: __all__ に data, strategy, execution, monitoring を定義（公開意図の宣言）。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを追加。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - プロジェクトルートの探索は本モジュール自身の __file__ を基点に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env パーサーを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内でのバックスラッシュエスケープ処理、インラインコメントの扱い（追加ルール）などを実装。
  - _load_env_file による読み込みで既存 OS 環境変数を保護する protected オプションを実装。
  - Settings クラスを提供し、アプリケーション設定をプロパティで公開（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境判定等）。
    - 必須環境変数未設定時は明示的に ValueError を送出する _require を実装。
    - env と log_level の値検証を実装（許容値セットでのチェック）。
    - is_live / is_paper / is_dev のヘルパーを追加。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール:
    - raw_news + news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄別センチメント ai_score を計算。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - バッチ処理（_BATCH_SIZE = 20）、1 銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装。
    - OpenAI 呼び出しでのリトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。
    - レスポンスの厳密バリデーションと JSON パースの頑健化（前後に余計なテキストが混ざる場合は最外側の {} を抽出して復元）。
    - スコアは ±1.0 にクリップ。部分成功時に既存スコアを消さないように DELETE → INSERT の置換方式で ai_scores テーブルを更新。
    - 外部に公開する API: score_news(conn, target_date, api_key=None)：書き込み銘柄数を返す。
    - テスト容易性: OpenAI 呼び出し点を _call_openai_api として分離して unittest.mock.patch で差し替え可能。

  - regime_detector モジュール:
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - ma200_ratio の計算ではルックアヘッドを防ぐため target_date 未満のみを参照し、データ不足時は中立値（1.0）を返す。
    - マクロニュース抽出は内部キーワードリストに基づき raw_news からタイトルを取得（最大 _MAX_MACRO_ARTICLES）。
    - OpenAI 呼び出し（gpt-4o-mini、JSON Mode）でマクロセンチメントを取得、API 障害時は macro_sentiment=0.0 でフェイルセーフ継続。
    - レジームスコア合成とラベリング（閾値判定）、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開 API: score_regime(conn, target_date, api_key=None)：成功時 1 を返す。
    - テスト容易性: news_nlp と異なる独立した _call_openai_api 実装によりモジュール結合を抑制。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱うユーティリティを追加: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が無い・不完全な場合の曜日ベースのフォールバック実装。
    - next/prev の最大探索日数上限を導入して無限ループを防止（_MAX_SEARCH_DAYS）。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得→保存を行う仕組みを実装（バックフィル・健全性チェックを実装）。
  - pipeline / etl:
    - ETLResult データクラスを導入し ETL 実行結果を構造化して返却可能に（to_dict を含む）。
    - 差分更新・バックフィル・品質チェックの処理方針を実装（jquants_client を用いた idempotent な保存、quality モジュールとの連携想定）。
    - パイプラインユーティリティをエクスポート（kabusys.data.ETLResult）。
  - 便利な内部ユーティリティ:
    - 複数の _table_exists / _get_max_date / 日付変換ユーティリティ等を実装。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20 日 ATR, atr_pct）、流動性（20 日平均売買代金, volume_ratio）、バリュー（PER, ROE）を計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB SQL を利用し、prices_daily / raw_financials のみを参照する安全設計。
  - feature_exploration:
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman ランク相関）。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）。
    - ランク変換ユーティリティ: rank(values)（同順位は平均ランク）。
    - pandas 等の外部依存を持たずに実装。

### Changed
- （初回リリースのため該当なし）

### Fixed / Robustness improvements
- OpenAI レスポンスのパースに対する耐性を確保:
  - JSON Mode の出力に前後テキストが混入するケースを想定して最外側の {} を抽出して復元するルールを実装（news_nlp）。
  - regime_detector / news_nlp 共に API の 5xx/ネットワーク/タイムアウト/429 に対するリトライと指数バックオフを実装し、全リトライ失敗時は安全側のデフォルト（macro_sentiment=0、スコアスキップ等）で継続する。
- DuckDB 関連の互換性に配慮:
  - executemany に空リストを渡さないチェックを追加して DuckDB 0.10 系の制約に対応（ai_scores 更新処理）。
  - DB 書き込みは冪等性を意識して DELETE → INSERT の置換方式を採用（部分失敗時の既存データ保護）。
- .env パーサーの堅牢化（クォート中のエスケープ、インラインコメント判定ルール）により多様な .env フォーマットを許容。

### Security
- OpenAI API キーの取り扱い:
  - API キーは明示的に引数で注入可能（api_key）か、環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を投げて早期検出。
  - .env 自動読み込み時に OS 環境変数を保護する設計（protected set）を採用。

### Known limitations / Notes
- strategy / execution / monitoring の実装は本差分に含まれていない（__all__ で将来公開予定を示唆）。
- OpenAI への実際の通信は外部サービスに依存するため、運用時は API レート制限やコストに注意が必要。
- news_nlp と regime_detector は LLM 出力に依存するため、モデル変更やアーキテクチャ変更時にプロンプト調整やバリデーションの更新が必要になる可能性がある。
- datetime.today()/date.today() を直接参照せず、target_date 引数で明示的に日付を与える設計によりルックアヘッドバイアスを防止している。
- 初期版のため Edge ケースや大規模データ下でのパフォーマンス最適化は今後の課題。

---

開発中の変更やバグ修正は本ファイルの [Unreleased] 以下に逐次記録してください。