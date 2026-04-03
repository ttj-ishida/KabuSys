# CHANGELOG

すべての注目すべき変更を記載します。フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0 — 初回リリース

## [Unreleased]
（今後の変更をここに記載してください）

## [0.1.0] - 2026-04-03
初回リリース。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージの初期公開。
  - バージョン情報: kabusys.__version__ = "0.1.0"。
  - 主要サブパッケージのエクスポート: data, research, ai, strategy, execution, monitoring（__all__）。

- 環境変数/設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能。
  - .env パースの堅牢化:
    - export プレフィックス対応、シングル/ダブルクォート処理、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - Settings クラスを提供し、主要設定をプロパティで取得可能:
    - J-Quants / kabu API / LINE Messaging / データベース（DuckDB/SQLite）パス / 監視関連ファイルパス / リソース閾値 / 実行環境（development, paper_trading, live）/ ログレベル判定等。
  - 必須環境変数未設定時には明示的な ValueError を送出する `_require` を用意。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news + news_symbols から指定ウィンドウ（前日15:00 JST〜当日08:30 JST 相当）の記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたり記事数上限・文字数トリム、レスポンス検証、スコアクリップ（±1.0）を実装。
    - API リトライ（429・ネットワーク断・タイムアウト・5xx）は指数バックオフで実行。致命的でない失敗はスキップして継続するフェイルセーフ設計。
    - スコアを ai_scores テーブルへ冪等的に書き込む（対象コードのみ DELETE → INSERT）。
    - 公開関数: score_news(conn, target_date, api_key=None)。
    - ユーティリティ: calc_news_window(target_date)（UTC naive datetime を返す）。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news をマクロキーワードでフィルタし、OpenAI に JSON 出力を要求して macro_sentiment を取得。
    - API 呼び出しは独立実装（news_nlp と private 関数を共有しない）で、リトライ・例外処理・パース失敗時のフォールバック（macro_sentiment=0.0）を実装。
    - DuckDB に対する書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。失敗時はロールバックを試行して上位へ例外を伝播。
    - 公開関数: score_regime(conn, target_date, api_key=None)。

  - ai パッケージのエクスポート:
    - score_news, score_regime（news_nlp の score_news は ai.__init__ でエクスポートされ、regime モジュールは個別利用）。

- データプラットフォーム (kabusys.data)
  - ETL パイプラインインターフェース (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー概要などを保持）。
    - 差分取得、バックフィル、品質チェック（quality モジュールとの連携）を想定した設計。
    - DuckDB テーブル存在チェックや最大日付取得等のユーティリティを提供（ETL 実装の基礎）。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルの存在チェック、祝日/半日/ SQ 日判定、次/前/期間内営業日取得関数を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB にカレンダー情報がない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - calendar_update_job により J-Quants API から差分取得 → 保存（バックフィル、健全性チェック含む）を実装。
    - デフォルトの先読みやバックフィル日数、最大探索範囲等の安全ガードを設置。

- リサーチ / ファクター (kabusys.research)
  - factor_research モジュール:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB の SQL ウィンドウ関数を活用し、営業日ベース（連続レコード）を前提に計算。データ不足時は None を返す設計。
  - feature_exploration モジュール:
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト: [1,5,21]）
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman の ρ、有効レコードが 3 未満なら None）
    - ランク変換ユーティリティ: rank(values)（同順位は平均ランク）
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median を計算）
  - research パッケージのエクスポート: 主要関数群と zscore_normalize の再エクスポート。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### 注意事項 / 設計方針
- ルックアヘッドバイアス防止のため、各種処理は内部で datetime.today()/date.today() を直接参照しない設計（target_date 引数を明示的に受け取る）。
- OpenAI API 呼び出しは JSON Mode を利用しレスポンスの安全なパースとバリデーションを厳密に行う。API 失敗時はフェイルセーフ（デフォルトスコアやスキップ）で継続する。
- DuckDB に対する書き込みは可能な限り冪等性を保つ（DELETE→INSERT、ON CONFLICT を想定）。
- .env 読み込みはプロジェクトルート検出に依存するため、配布後の環境では自動ロードが期待どおり動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使用して明示的に制御してください。

（以降のリリースでは、テストカバレッジ、監視/実行モジュールの実装、戦略実行フロー（strategy / execution / monitoring）やドキュメントの拡充が予定されています。）