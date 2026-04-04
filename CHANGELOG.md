CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。

Unreleased
----------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-04
-------------------

初回リリース。日本株自動売買システム "KabuSys" の基本機能を実装します。
以下はコードベースから推測される主要な追加点・設計方針・注意点の一覧です。

Added
- パッケージ公開情報
  - kabusys パッケージ初期版を公開。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を含めた公開 API 設定。

- 環境変数／設定管理
  - robust な .env ローダーを実装（src/kabusys/config.py）。
    - プロジェクトルート検出は __file__ 起点で .git または pyproject.toml を探索し、CWD に依存しない実装。
    - .env/.env.local を自動ロード（優先順位: OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - export KEY=val 形式やシングル/ダブルクォート、エスケープ、行内コメントの取り扱いをサポートするパーサを実装。
    - 読み込み時の上書き制御（override, protected）をサポート。
  - Settings クラスでアプリ設定を提供。
    - J-Quants / kabu API / LINE / データベースパス / 監視関連（PID, kill flag,閾値） / ログ・環境種別等のプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）を実装。
    - デフォルト値（例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH など）を用意。

- ニュース NLP（AI）モジュール
  - src/kabusys/ai/news_nlp.py: raw_news と news_symbols を元に OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのセンチメント ai_score を算出し ai_scores テーブルへ保存する処理を実装。
    - JST ベースのニュース収集ウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）と calc_news_window 関数。
    - 1 銘柄あたりの記事数・文字数の上限（記事数:10、文字数:3000）によるトリミング。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）での送信。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する再試行（指数バックオフ）を実装。
    - レスポンス検証ロジック（JSON 抽出、results キー/型チェック、既知のコードのみ許容、スコアの数値化・有限値チェック、±1 でクリップ）。
    - DB 書き込みは部分失敗を許容する設計：取得できた銘柄コードのみ DELETE → INSERT による置換を行う（DuckDB 互換性に配慮した executemany の扱い）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可）。

  - src/kabusys/ai/regime_detector.py: 市場レジーム判定機能を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を生成。
    - マクロニュース抽出（マクロキーワードリスト）→ OpenAI 呼び出し（gpt-4o-mini）→ JSON パース → スコア合成。
    - API 失敗時のフェイルセーフ（macro_sentiment=0.0）を採用。
    - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装。
    - テストで差し替え可能な内部 API 呼び出し関数（_call_openai_api）。

- 研究（Research）モジュール
  - src/kabusys/research/* にファクター計算・特徴量探索関数を実装。
    - factor_research: calc_momentum, calc_value, calc_volatility
      - Momentum: 1M/3M/6M リターン算出、200 日 MA 乖離（データ不足時は None）。
      - Value: PER（EPS が 0/欠損時は None）、ROE 取得（raw_financials からの最新レコードを使用）。
      - Volatility: 20 日 ATR（true range の NULL 伝播を考慮）、相対 ATR、20 日平均売買代金、出来高比など。
      - DuckDB でのウィンドウ関数・集計を活用した実装。
    - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
      - 将来リターン calc_forward_returns（デフォルト horizons=[1,5,21]）、入力バリデーション。
      - IC（Spearman）計算: rank 関数は同順位を平均ランクで扱う（round による tie 対策）。
      - 統計サマリー関数 factor_summary（count/mean/std/min/max/median）。
    - これらは外部ライブラリ（pandas 等）に依存せず、DuckDB + 標準ライブラリのみで実装。

- データ（Data）モジュール
  - calendar_management: 市場カレンダー管理と営業日判定（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を提供。
    - market_calendar データがない場合は曜日ベース（平日）でフォールバック。
    - DB 登録値優先、未登録日は曜日フォールバックで一貫した挙動。
    - calendar_update_job により J-Quants API から差分取得→保存（バックフィル、健全性チェックを含む）。
    - 最大探索範囲・バックフィル日数・先読み日数等の定数を定義。
  - ETL / pipeline: ETLResult データクラスと ETL 管理ユーティリティを実装（src/kabusys/data/pipeline.py）。
    - ETLResult により取得/保存件数、品質問題、エラー一覧を集約。to_dict() により品質問題をシリアライズ可能。
    - 差分取得・保存・品質チェックを行う ETL の設計方針に準拠する骨格を提供。
  - jquants_client 依存を想定し、fetch/save の呼び出しを統合する設計（テスト差し替え可能）。

- その他
  - モジュールのロギングと多くの箇所でのフェイルセーフ設計（例外を投げずにログ出力して継続する箇所がある）を実装。
  - DuckDB を前提にした SQL 実装（情報スキーマ参照・executemany の互換性配慮など）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの取り扱いは環境変数（OPENAI_API_KEY）経由を想定。api_key 引数で明示的に注入可能。
- 環境設定の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テストや CI の安全性確保）。

Notes / Known limitations
- OpenAI 呼び出しは外部サービスに依存するため、API の可用性やレート制限が実行に影響を与えます。モジュールは再試行やフォールバック（0.0）を実装しているが、最終的な結果は外部 API に依存します。
- 一部の DB 操作は DuckDB のバージョン互換性に配慮した実装になっている（executemany の空配列回避など）。
- 一部 public helper（_call_openai_api 等）はテスト時に差し替え可能に設計されているのでユニットテストのモック化が容易。
- strategy/ execution/ monitoring の具体的な実装はこのリリースでは参照されていない（パッケージ公開には含まれるが、詳細は別途実装想定）。

Compatibility
- このリリースは DuckDB を前提とした SQL 実装を含むため、DuckDB 環境での利用を想定しています。
- OpenAI の Python SDK を利用する想定（エラー型の扱い等は SDK のバージョン差に対してある程度の互換性を確保する実装あり）。

Acknowledgements
- 設計文書（StrategyModel.md, DataPlatform.md）や J-Quants、kabu API を想定した設計方針に基づいて実装されています（コード内ドキュメント参照）。

-----
（以降のリリースでは変更点をバージョンごとに追記してください。）