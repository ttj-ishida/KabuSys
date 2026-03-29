Keep a Changelog
=================

全ての注目すべき変更はこのファイルに記録します。セマンティックバージョニングに従います。

[0.1.0] - 2026-03-29
-------------------

Added
- 初版リリース。日本株自動売買システム「KabuSys」のコア機能を実装。
- パッケージ構成を追加:
  - kabusys.config: 環境変数／.env 管理ユーティリティを実装
    - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env ロード
    - .env / .env.local の読み込み順序（OS 環境 > .env.local > .env）
    - export 付き行・クォートされた値・インラインコメントの扱いに対応する堅牢なパーサ
    - OS環境変数保護（protected set）と override 制御
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化
    - Settings クラスによる型付きアクセサ（必須変数チェック、デフォルト値、値検証）
- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事の銘柄別センチメントを OpenAI（gpt-4o-mini）へ問い合わせて ai_scores テーブルへ書き込む機能
    - JST 基準のニュース収集ウィンドウ計算（前日15:00〜当日08:30）
    - 銘柄ごとに記事を集約・トリム（記事数・文字数制限）
    - バッチ送信（最大20銘柄/回）、JSON mode を利用した厳密な出力期待
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ
    - レスポンスの堅牢なバリデーション（部分失敗はスキップ、スコアは ±1.0 でクリップ）
    - DuckDB 互換性を考慮した空リスト回避（executemany の空パラメータ未対応対策）
    - テスト用に _call_openai_api を差し替え可能
  - regime_detector: ETF（1321）200日移動平均乖離とマクロニュース LLM センチメントを合成して日次の市場レジーム（bull/neutral/bear）を判定・保存
    - ma200 比率計算（target_date 未満のデータのみ使用、ルックアヘッド回避）
    - マクロニュース抽出（キーワードフィルタ、最新最大20件）
    - OpenAI 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）
    - レジームスコアの合成ロジック（MA70% / macro30% の重み付け、スコアクリップ）
    - market_regime テーブルへの冪等的書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK）
- Research モジュール（kabusys.research）
  - factor_research: モメンタム（1/3/6M）、200日MA乖離、20日ATR、流動性指標、PER/ROE などの定量ファクターを DuckDB から計算する関数群（calc_momentum / calc_volatility / calc_value）
    - DuckDB のウィンドウ関数を用いた実装、欠損やデータ不足時の None 返却を明示
  - feature_exploration: 将来リターン計算（複数ホライズン）、スピアマンIC（rank に基づく）、基本統計量算出等を実装（calc_forward_returns / calc_ic / rank / factor_summary）
    - pandas 等に依存せず標準ライブラリで実装
    - 入力検証（horizons の制約、IC の最小サンプルチェック等）
  - zscore_normalize をデータユーティリティから再エクスポート
- Data モジュール（kabusys.data）
  - calendar_management: JPX カレンダーの夜間バッチ更新（J-Quants から差分取得）と営業日判定ロジックを実装
    - market_calendar がない場合の曜日ベースのフォールバック
    - next_trading_day / prev_trading_day / get_trading_days / is_trading_day / is_sq_day を提供
    - 最大探索日数制限、バックフィル、健全性チェック（将来日付異常検出）
  - pipeline / etl: ETL パイプラインの基本構造と ETLResult データクラスを実装
    - 差分更新・バックフィル方針（デフォルト backfill_days=3）、品質チェックの結果収集
    - DuckDB 上での最大日付取得、テーブル存在チェックなどのユーティリティ
  - jquants_client を用いたデータ取得・保存フローを想定（fetch/save の呼び出しポイント実装）
  - etl の公開インターフェース（ETLResult の再エクスポート）
- パッケージ初期化
  - kabusys.__init__ にバージョンと主要サブパッケージを公開（data, strategy, execution, monitoring）

Changed
- 内部設計指針の明文化: ルックアヘッドバイアス回避（datetime.today() 等を直接参照しない）、外部API失敗時のフェイルセーフ方針、モジュール分離（_call_openai_api をモジュール毎に独立実装）などを設計ドキュメントに反映。

Fixed
- .env パーサの改善:
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの誤認防止などを実装して .env の実務的な記法に対応。
- DuckDB 互換性対応:
  - executemany に空リストを渡すと失敗する問題を回避するため、空チェックを追加してから executemany を呼ぶようにした。

Security
- 環境変数の読み込みで OS 側の既存環境変数を保護するロジック（protected set）を導入。自動ロードを環境変数で無効化する仕組みを提供。

Performance
- AI バッチ処理および DuckDB 集約クエリはチャンク処理・ウィンドウ関数を多用して API／DB 負荷を抑制する実装に。

Testing / Developer experience
- OpenAI 呼び出し部分（_call_openai_api）を unittest.mock.patch 等で差し替え可能にして単体テストを容易化。
- ロギングを充実させ、処理状況・リトライ・例外発生時の診断をしやすくした。

Known issues / Notes
- ai モジュールは OpenAI API の JSON Mode を前提としているが、稀に余計な前後テキストが混入するケースを復元してパースする実装を入れている（完全保証は不可）。
- news_nlp/regime_detector は API 呼び出しでコストと遅延が発生するため、運用時は適切なキー管理と呼び出し頻度制御を推奨。
- monitoring サブパッケージは __all__ に含まれるが、このリリースでは具体的な実装 (ファイル) は含まれていない（今後追加予定）。

Acknowledgements
- この初版は DuckDB と OpenAI API を主要依存先として設計しています。設計方針として「外部と接続する処理はフェイルセーフで部分失敗を許容する」ことを優先しています。

<!-- 以降のリリースはここに追記 -->