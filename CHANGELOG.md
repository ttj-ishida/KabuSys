CHANGELOG
=========

すべての注目すべき変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。
リリースはセマンティックバージョニングに従います。

[0.1.0] - 2026-03-29
-------------------

Added
- 基本パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
  - パッケージの主要サブパッケージを公開: data, research, ai, （および将来的な）strategy, execution, monitoring を __all__ に含める。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートの検出: .git または pyproject.toml を起点に探索するため、CWD に依存せず配布後も正しく動作。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - .env パースの強化:
      - export KEY=val 形式対応。
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
      - インラインコメント処理（クォート外、直前が空白/タブの '#' をコメントとして扱う）等。
    - .env 読み込み失敗時は警告を出し継続。
  - Settings クラス: 必須環境変数取得（_require）と多彩なプロパティを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーション。
    - データベースパスのデフォルト（DUCKDB_PATH, SQLITE_PATH）を Path オブジェクトで提供。
    - is_live / is_paper / is_dev の便宜プロパティ。

- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON mode を利用して銘柄別センチメント（ai_scores）を書き込む処理を実装。
  - 主な特徴:
    - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）: calc_news_window。
    - 銘柄ごとに最新記事を集約（1銘柄あたり上限 _MAX_ARTICLES_PER_STOCK、文字数トリム _MAX_CHARS_PER_STOCK）。
    - バッチ送信: 1回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE）。
    - リトライ/バックオフ:
      - レート制限、ネットワーク断、タイムアウト、5xx を対象に指数バックオフでリトライ（設定: _MAX_RETRIES, _RETRY_BASE_SECONDS）。
      - API 呼び出し失敗時は個別チャンクをスキップし、全体処理は継続（フェイルセーフ）。
    - レスポンス検証とスコア処理:
      - JSON の頑健なパース（前後余分テキストが混ざるケースを考慮して最外の {} を抽出）。
      - "results" リストの型・要素検証、未知コードは無視、数値チェック、±1.0 でクリップ。
    - DB への書き込みは冪等（DELETE → INSERT）かつコードを限定して部分失敗時に既存スコアを保護。
    - テストしやすさ:
      - OpenAI 呼び出しを行う内部関数 _call_openai_api は unittest.mock.patch で差し替え可能。
  - 公開 API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。API キー未設定時は ValueError。

- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321 の 200 日移動平均乖離（ウェイト 70%）とマクロ経済ニュースの LLM センチメント（ウェイト 30%）を合成して日次レジーム判定（bull/neutral/bear）を行う score_regime を実装。
  - 主な特徴:
    - MA200 乖離は過去 200 日分の終値から計算（target_date 未満のみ使用、データ不足時は中立 ma200_ratio=1.0 を採用）。
    - マクロニュース抽出は news_nlp.calc_news_window とキーワードフィルタ（_MACRO_KEYWORDS）を使用。
    - OpenAI 呼び出しは gpt-4o-mini を使用、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 合成スコアは clip して閾値でラベル付け。結果を market_regime テーブルに冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性のため _call_openai_api はモック可能。
  - 公開 API: score_regime(conn, target_date, api_key=None) → 1 を返す。API キー未設定時は ValueError。

- 研究（research）モジュール群（src/kabusys/research/）
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev を計算（必要行数不足時は None を返す）。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS 0/欠損は None）。
    - 全て DuckDB SQL ウィンドウ関数を活用して実装。
  - feature_exploration.py:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）の場合は None。
    - rank: 同順位の平均ランク処理（丸め処理で ties 対策）。
    - factor_summary: count/mean/std/min/max/median を計算する簡易統計サマリ。
  - research パッケージは zscore_normalize（kabusys.data.stats から）も再公開。

- データ処理（src/kabusys/data/）
  - calendar_management.py:
    - 市場カレンダー管理: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar が存在しない場合は曜日ベース（平日を営業日）でフォールバックする一貫した振る舞い。
    - calendar_update_job: J-Quants API（jquants_client.fetch_market_calendar）から差分取得して market_calendar を更新。バックフィルや健全性チェック（将来日付の異常検出）を実装。
  - pipeline.py / etl.py:
    - ETLResult データクラス（ETL 実行結果の集約情報）を定義し、kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート。
    - ETL パイプライン用ユーティリティ: テーブル存在チェック / 最大日付取得 / カレンダー補正等の内部関数を実装。
    - 設計として差分更新・バックフィル（既存データの数日前から再取得）・品質チェック（kabusys.data.quality を利用）を想定。品質チェックでエラーが検出されても ETL は継続し結果を収集する設計。

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス対策:
  - いずれの AI / 研究処理も内部で datetime.today() / date.today() を参照せず、呼び出し元から渡された target_date を基準に処理する設計。
  - DB クエリでは target_date 未満・以前/以降の排他条件を明示して使用。
- フェイルセーフ設計:
  - OpenAI API 呼び出しの失敗は致命的に停止させず、既定値（macro_sentiment=0.0 等）で継続することでパイプラインの健全性を保つ。
  - ニューススコア・レジームスコアともに、API 呼び出しに対してリトライ/バックオフを実装。
- テスト支援:
  - OpenAI 呼び出し箇所は内部関数（_call_openai_api）を提供し、ユニットテストでモック可能。
- DuckDB 互換性考慮:
  - DuckDB 0.10 系の executemany に対する空リスト制約を回避するため、空パラメータ群のときは executemany を呼ばないガードを導入。
- 環境変数の保護:
  - .env の読み込み時に OS 環境変数一覧を protected として扱い、.env.local の上書きでも OS 側の値を保護する仕組みを採用。

Security
- API キー（OpenAI 等）は環境変数経由で扱うことを想定。Settings では必須チェックを行い、未設定時は ValueError を発生させることで明示的な設定を促す。

Acknowledgements / TODO / 今後の改善点（メモ）
- strategy / execution / monitoring パッケージの具体実装は今後追加予定（__all__ へは既に含めている）。
- ai モデルやバッチサイズ、リトライ設定は実環境での運用に合わせてチューニング予定。
- quality モジュールのルール拡張や ETL の監査ログ出力の強化を予定。

--- 

（以降の変更はこのファイルに追記してください）