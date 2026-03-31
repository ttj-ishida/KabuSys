# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [0.1.0] - 2026-03-31

### 追加
- パッケージ初期リリースを追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 基本モジュールと公開インターフェース
  - src/kabusys/__init__.py
    - バージョン定義 (__version__ = "0.1.0") と主要サブパッケージの公開定義（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数を読み込む自動ローダーを実装。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env
      - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD 非依存）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサーの実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ、コメント処理等）。
    - 上書き制御（override / protected）を実装し、OS 環境変数の保護に対応。
    - Settings クラスを提供（プロパティ経由で設定値を取得）。
      - J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル など。
      - バリデーション（有効な env 値・ログレベルの検査）と必須変数のチェック（_require）。

- AI 関連
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を銘柄ごとに集約し OpenAI（gpt-4o-mini, JSON mode）でセンチメントを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ（calc_news_window）。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数・文字数上限（記事数最大10、文字数最大3000）によりプロンプト肥大化を防止。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフで再試行。
    - レスポンスのバリデーションおよびスコアクリッピング（±1.0）。
    - DuckDB に対する冪等書き込み（DELETE → INSERT）、部分失敗時に既存スコアを保護する挙動。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・保存。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロニュースの抽出はキーワードベースでフィルタ（_MACRO_KEYWORDS）。
    - OpenAI 呼び出しは独立実装。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - リトライ・バックオフおよび 5xx 判定／ログ出力の実装。

- データ処理（Data Platform）
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの骨格とユーティリティを追加。
    - 差分更新・バックフィル（デフォルト backfill 日数）・品質チェックの設計を反映。
    - ETLResult データクラスを定義（取得件数・保存件数・品質問題・エラー等を集約）。
    - DuckDB を使った最大日付取得等のユーティリティを実装。

  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。

  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理機能を実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API。
      - market_calendar が未取得の場合の曜日ベースフォールバック。
      - database 優先ルール（DB 登録があれば DB 値を優先、未登録は曜日判定で補完）。
      - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新（バックフィル・健全性チェック含む）。
    - 最大探索日数の制限やデータ不整合時のログ出力など堅牢性対策を導入。

  - jquants_client 連携を想定する実装箇所（fetch/save を呼び出す設計を反映）。

- リサーチ（研究用）モジュール
  - src/kabusys/research/factor_research.py
    - ファクター計算を実装。
      - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
      - Volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金, 出来高比率。
      - Value: PER、ROE（raw_financials から最新財務データを取得）。
    - DuckDB ベースの SQL+Python 実装で、外部 API や発注処理とは独立。
    - データ不足時には None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: マルチホライズン（デフォルト [1,5,21]）に対応。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関を実装（同順位の平均ランク処理を含む）。
    - ランク変換ユーティリティ（rank）。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
  - src/kabusys/research/__init__.py
    - 主要研究用関数を再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### 設計上の注意点（ドキュメント的追加）
- ルックアヘッドバイアス防止:
  - 多くの処理で datetime.today() / date.today() を直接参照せず、外部から与えられる target_date を基準に処理を行う設計。
  - prices_daily クエリやニュースウィンドウで「< target_date」等の条件を用いて未来データの持ち込みを防止。
- フェイルセーフ:
  - OpenAI API 呼び出し失敗時やパース失敗時は例外を上位へ投げず、ロギングのうえデフォルト値（例: 0.0）で継続する箇所を多数用意。
- テスト容易性:
  - OpenAI 呼び出しなどを内部関数でラップし unittest.mock.patch で差し替え可能にすることで単体テストを容易化。
- DuckDB に依存した設計:
  - ETL / research / ai / calendar モジュールは DuckDB 接続（DuckDBPyConnection）を受け取り、SQL と組み合わせて処理を行う。

### 既知の制限 / 注意事項
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。
- .env パーサーは多くのケースを想定しているが、非常に特殊な書式（複雑なネストや不正なエスケープ等）は未検証。
- ai モジュールは JSON mode を期待するが、LLM の挙動により前後の余計な文字列が混入する場合があり、これを復元するロジックを入れているが完全でない可能性がある。
- DuckDB の executemany に空リストを渡せないバージョン（例: 0.10）への互換性考慮として、空チェックを実施している。

### 依存（コード上の想定）
- duckdb
- openai（OpenAI SDK、chat completions の JSON mode を利用）
- Python 標準ライブラリのみで追加の解析は実装（pandas 等には依存しない設計）

---

今後の予定（参考）
- strategy / execution / monitoring パッケージの実装拡充（現在は公開名のみ定義）。
- テストカバレッジ拡大（特に OpenAI 呼び出しのモック周り）。
- jquants_client 実装の具体化と ETL の実行スクリプト化。