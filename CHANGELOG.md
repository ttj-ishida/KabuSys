Changelog
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
- 基本パッケージ構成を追加:
  - パブリック API: kabusys.__version__ = 0.1.0、kabusys パッケージのエクスポート（data, strategy, execution, monitoring）。
- 設定/環境変数管理 (kabusys.config):
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジック: __file__ を起点に .git または pyproject.toml を探索してルートを特定（CWD に依存しない）。
  - .env のパースは export KEY=val、クォートやバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 必須環境変数取得関数 (_require) と Settings クラスを提供。J-Quants / kabu API / LINE / DB / 監視設定 等のプロパティを定義。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を実装。
- AI 関連 (kabusys.ai):
  - ニュース NLP スコアリング (kabusys.ai.news_nlp):
    - raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換して DB 比較）。
    - バッチ処理: 最大 20 銘柄／リクエスト、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - エラーハンドリング: 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ、その他はスキップして継続（フェイルセーフ）。
    - レスポンス検証: JSON 抜き出し、"results" リスト形式の検証、未知コード除外、スコア数値変換、±1.0 にクリップ。
    - DuckDB との冪等書き込み（DELETE → INSERT）と DuckDB 0.10 に対する compat 対策（executemany の空リスト回避）。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - テスト容易性: OpenAI 呼び出しを差し替え可能な内部関数（_call_openai_api）。
  - 市場レジーム判定 (kabusys.ai.regime_detector):
    - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは gpt-4o-mini、最大記事数 20 件、リトライや 5xx の扱いを実装。API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - duckdb を使った計算と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK）。
    - lookahead バイアス防止のため、target_date 未満のみを参照する設計。
- Research（リサーチ）モジュール (kabusys.research):
  - factor_research:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR/相対 ATR、出来高関連指標）、Value（PER/ROE）計算関数を実装。
    - DuckDB のウィンドウ関数や LAG/AVG を活用した実装。データ不足時の None 扱い、ログ出力を実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンのρ、欠損/非有限値除外、サンプル数チェック）。
    - ランク変換（rank）: 同順位は平均ランク、丸め処理で ties の誤検出を防止。
    - ファクター統計サマリー（count/mean/std/min/max/median）。
  - research パッケージの __all__ に代表的関数をエクスポート。
- Data（データ基盤）モジュール (kabusys.data):
  - calendar_management:
    - JPX マーケットカレンダー管理、営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar の有無に応じた DB 優先ルールと曜日ベースのフォールバック、最大探索日数制限、健全性チェック、バックフィルの実装。
    - J-Quants クライアント経由での夜間バッチ更新ジョブ（calendar_update_job）を提供（fetch_market_calendar / save_market_calendar を使用）。
  - pipeline / etl:
    - ETL パイプラインのインターフェースと ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - 差分更新・バックフィル・品質チェック（品質問題は収集して呼び出し元に委ねる設計）。
    - jquants_client（jq） との連携を前提にした設計。
  - data パッケージの再エクスポート（ETLResult）。
- テスト・運用に配慮した設計:
  - datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。
  - OpenAI API 呼び出しを差し替え可能にしてユニットテストしやすくしている。
  - DuckDB を前提としたトランザクション制御、executemany の互換性考慮、NULL/欠損値の明示的処理。
- ロギング: 各モジュールで詳細なログ（info/warning/debug）を追加。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 環境変数管理で OS 環境変数を保護するための protected キーセットを導入（.env による上書きを制限）。
- API キーは引数で注入可能で、未設定時は明示的な ValueError を発生させることで秘密情報の誤使用を防止。

Notes / 実装上の注意
- DuckDB を使用することを前提としているため、実行時に DuckDB 接続（DuckDBPyConnection）を渡す必要がある。
- OpenAI（gpt-4o-mini）を利用する箇所は実行環境で OPENAI_API_KEY を設定するか、api_key を明示的に渡す必要がある。
- jquants_client（kabusys.data.jquants_client）や quality モジュールは外部依存（実装は別モジュール）を仮定した設計になっている。
- strategy / execution / monitoring などのパッケージ名は __all__ に含まれるが、本差分ではそれらの実装ファイルはリストされていないため、今後のリリースで追加・更新される想定。

---

作成した CHANGELOG はコードの実装内容から推測して記載しています。実際のコミット歴・リリースノートと差異がある場合は適宜修正してください。