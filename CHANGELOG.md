CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-04
--------------------

Added
- 初回リリースとしてライブラリ全体を追加。
  - パッケージ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - 公開モジュール群: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルートは .git または pyproject.toml から探索（CWD 非依存）。
  - .env パーサーの実装:
    - export KEY=val 形式対応、単一/二重クォートとエスケープ対応、コメント処理。
  - Settings クラスでアプリ設定をプロパティ経由で提供。
    - J-Quants / kabuステーション / LINE / DB（DuckDB / SQLite）/ 監視 / システム設定等の環境変数を取得。
    - 必須項目未設定時は明示的に ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値チェックを実装（許容値の検証）。
    - パス設定は Path.expanduser() を利用。

- AI（自然言語処理）モジュール (src/kabusys/ai)
  - ニュースセンチメント解析: news_nlp.score_news
    - J-Quants 由来の raw_news / news_symbols を銘柄単位に集約し、OpenAI(gpt-4o-mini) の JSON mode を用いてスコア化。
    - バッチサイズ、トークン肥大化対策、スコア検証/クリップ、部分書き換え戦略（DELETE → INSERT）を実装。
    - リトライ（429・接続断・タイムアウト・5xx）に対する指数バックオフを実装。
    - API キーは引数で注入可能（テスト容易性）。未設定時は ValueError。
    - テスト用に _call_openai_api をパッチ差し替え可能に設計。
  - マーケットレジーム判定: regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime を参照し、冪等的に market_regime を更新（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 でフェイルセーフ継続。
    - API 呼び出しは専用内部実装でモジュール結合を避ける。
    - OpenAI client は引数（環境変数 OPENAI_API_KEY）で解決。未設定時は ValueError。
    - リトライ・エラーハンドリング（RateLimit/接続/TIMEOUT/APIError の 5xx 判定等）を実装。

- データプラットフォーム (src/kabusys/data)
  - ETL / Pipeline:
    - ETLResult dataclass と pipeline のインターフェースを提供（差分取得・保存・品質チェックの設計方針を反映）。
    - jquants_client を通じた差分取得・冪等保存を想定。
    - 品質チェック（quality）を結果に含める設計。エラーは収集して上位で判断する方針（Fail-Fast ではない）。
    - DuckDB 向けの互換性注意（executemany に空リスト禁止など）を考慮した実装。
  - カレンダー管理:
    - JPX カレンダーの取得・保存と営業日判定ユーティリティを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - market_calendar がない場合は曜日ベースでフォールバック（週末は休場）。
    - calendar_update_job: J-Quants から差分取得して冪等的に保存。バックフィルと健全性チェックを実装。
    - 最大探索範囲・ループ回避の安全措置を追加。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research:
    - モメンタム（1M/3M/6M, MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金等）、バリュー（PER, ROE）を DuckDB クエリで計算する関数群を実装。
    - データ不足時の None 処理、戻り値は (date, code) を含む dict リスト。
    - DuckDB ウィンドウ関数を多用し、営業日スキャン範囲のバッファを導入。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - スピアマン（ランク）相関を ties を考慮して計算。
    - horizons のバリデーション、NaN/有限性チェック。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Implementation details and design decisions
- ルックアヘッドバイアス対策: 全てのモジュールで datetime.today() / date.today() を直接参照しない設計（target_date を明示的に渡す）。
- DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 戦略等）。
- OpenAI 呼び出しは JSON Mode を利用し、レスポンスのパースとバリデーションを厳密に行う。パース失敗時はスキップまたは中立スコアでフェイルセーフ。
- テスト容易性: OpenAI 呼び出しを内部関数でラップし、unit test でモック差し替え可能な設計。
- DuckDB 互換性注意: executemany に空リストを渡さない等の実装上の配慮がある。
- タイムゾーン: raw_news.datetime は UTC 前提。calendar / window 計算は UTC-naive な datetime を返すが、処理は JST ↔ UTC の変換を考慮している。
- 環境変数の必須キー一覧（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（AI 機能利用時）
  - その他 DB パスや監視設定は Settings プロパティでデフォルト値が設定される。

Security
- OpenAI API キー等の秘密情報は環境変数で管理する前提。.env 自動ロード機構はあるが、プロダクションでは OS 環境やシークレットマネージャの利用を推奨。

Acknowledgements
- 本ドキュメントはソースコードの構成、コメント、docstring から機能と設計方針を推測して作成しました。実際の仕様や実装の細部はソースコードを参照してください。