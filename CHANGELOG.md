Changelog
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

（現時点のコードベースは初回リリース相当の内容のため、未公開変更はありません）

[0.1.0] - 2026-04-04
-------------------

初回リリース。日本株自動売買・データ基盤のコア機能群を提供します。主な追加点は以下の通りです。

Added
- パッケージのエントリポイント
  - kabusys パッケージ初期化（__version__ = "0.1.0", __all__ 定義）。
- 環境設定 / .env ローダー（kabusys.config）
  - プロジェクトルートの自動検出（.git または pyproject.toml を起点）により、CWD に依存しない .env 自動読み込みを実装。
  - .env / .env.local の読み込み順序と上書きルールを実装（OS 環境変数を保護する protected 機構）。
  - 行パーサーは export KEY=val、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理（クォート外での # の扱い）などに対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能を追加（テスト向け）。
  - Settings クラスでアプリケーション設定をプロパティとして提供（OpenAI / J-Quants / kabu-station / LINE / DBパス / 監視設定 / 環境・ログレベル検証など）。
  - 必須環境変数未設定時は明示的に ValueError を送出する _require 実装。
- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini の JSON Mode）でセンチメントを評価。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄 / API 呼び出し）、1 銘柄あたり最大記事数・最大文字数でトリム、スコア ±1.0 でクリップ。
    - API エラー（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフリトライを実装。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results フォーマット検証、未知コードの無視、数値検査）を実装。部分成功時は該当銘柄のみ置換することで既存データ保護。
    - テストしやすさのため _call_openai_api を分離してモック可能に実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を実行。
    - マクロニュース抽出（キーワードフィルタ）と OpenAI 呼び出し、リトライ/フォールバック（API 失敗時 macro_sentiment=0.0）。
    - レジームスコアのクリップと閾値判定、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - lookahead バイアスを避ける設計（datetime.today()/date.today() を参照しない、クエリは date < target_date で過去データのみ使用）。
- Research（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR, 相対 ATR）、流動性指標（20 日平均売買代金・出来高比率）、バリューファクター（PER・ROE）を DuckDB 上で計算する関数を追加（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の取り扱い（例: MA200 行数不足時は None）を明示。
    - 設計方針として外部 API 呼び出しは行わず、prices_daily / raw_financials のみを参照。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns：デフォルト horizons=[1,5,21]）、IC（Spearman ランク相関）計算（calc_ic）、基本統計サマリ（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - pandas 等に依存せず純粋 Python + SQL（DuckDB）で実装。
  - research パッケージの __all__ で主要関数を再エクスポート。
- Data（kabusys.data）
  - calendar_management
    - JPX カレンダーの管理と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を追加。
    - market_calendar がない場合の曜日ベースフォールバック（週末を非営業日扱い）を実装し、DB 登録値があればそれを優先する一貫した挙動を実現。
    - 夜間バッチ job（calendar_update_job）で J-Quants API から差分取得し冪等保存、バックフィル、健全性チェックを行う（jquants_client 経由）。
  - ETL / pipeline
    - ETLResult データクラスを公開（kabusys.data.pipeline -> ETLResult を etl 経由でエクスポート）。
    - 差分取得・保存（idempotent 保存）・品質チェックフローを想定したパイプライン基盤を実装（差分単位、backfill、品質イシュー収集など）。
    - DuckDB の互換性考慮（executemany に空リストを渡さない等の保護）を実装。
- 汎用的な堅牢化
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、ROLLBACK に失敗した場合は警告ログ。
  - OpenAI API 呼び出し周りはリトライ・ステータスコード判定・ログ出力を充実。
  - 設計方針として「ルックアヘッドバイアス防止」の徹底（時間参照を明示的に引数化し、内部で現在時刻を直接参照しない）。
  - テストしやすい構造（API キー注入、_call_openai_api のモック差し替えポイント等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 必須秘密情報（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings 経由で明示取得。未設定時は例外により早期検出。

Notes / Usage hints
- OpenAI キー注入:
  - news_nlp.score_news / regime_detector.score_regime は api_key 引数を受け取り、None の場合は環境変数 OPENAI_API_KEY を参照します。テスト時は api_key を直接渡すか _call_openai_api をモックしてください。
- .env の自動読み込みを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストや CI で便利です）。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーになるバージョンを考慮して、コード側で空リストガードを入れています。
- ログレベル / 環境検証:
  - Settings.log_level / Settings.env は有効値を検証します（不正値は ValueError を送出）。

開発者向け設計方針（要約）
- lookahead バイアスを避けるため、日付・時刻は呼び出し側が渡す（内部で date.today() を使わない）。
- 外部 API 呼び出しの失敗はフェイルセーフで継続できる設計（部分失敗時に他データを保護）。
- DuckDB を第一級でサポートし、互換性のための実装上の工夫（空パラメータ防止、date 型の安全変換等）を行う。
- テストしやすさを考慮して外部依存の注入点・モックポイントを明確化。

今後の予定（例）
- ストラテジー本体（strategy）や実行/監視（execution/monitoring）モジュールの実装拡張。
- ai モデル評価の自動テスト・キャッシュ戦略の追加。
- ETL のより詳細な品質チェックルール追加とアラート機能の実装。

---