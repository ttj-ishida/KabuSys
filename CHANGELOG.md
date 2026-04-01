# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。  
バージョン番号は semver に従います。

## [Unreleased]

## [0.1.0] - 2026-04-01
初期リリース。

### 追加
- パッケージ基礎
  - パッケージ初期化 (kabusys.__init__) を追加。公開サブパッケージは data, strategy, execution, monitoring を想定。
  - バージョン: 0.1.0。

- 環境設定 / ロード (.env 対応)
  - kabusys.config:
    - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を基準）。
    - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数優先）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサー実装: コメント、export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
    - .env 読み込み時の上書き制御（override）と OS 環境変数保護（protected set）。
    - Settings クラスを提供。主要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等）をプロパティとして取得。安全性のため必須変数未設定時に ValueError を投げるものを用意。
    - デフォルト値: KABUSYS_ENV=development, LOG_LEVEL=INFO、各種パス（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH）や監視閾値のデフォルトを設定。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値の制約）。

- AI モジュール
  - kabusys.ai.news_nlp:
    - raw_news / news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - ニュース収集ウィンドウの計算（JST 基準: 前日 15:00 ～ 当日 08:30）を calc_news_window で提供。
    - バッチ処理（最大 20 銘柄／回）、1 銘柄あたり記事数上限、文字数トリム上限を実装（トークン肥大対策）。
    - API 再試行戦略（429, ネットワーク断, タイムアウト, 5xx を対象に指数バックオフ）を実装し、失敗はスキップしてフェイルセーフ化。
    - レスポンスの厳格なバリデーションとスコアクリッピング（±1.0）、部分成功時に他銘柄の既存データを消さない idempotent な DB 書き込み（DELETE → INSERT）を実装。
    - テスト用に _call_openai_api を patch できる設計。

  - kabusys.ai.regime_detector:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（比率）と、マクロニュースの LLM センチメントを重み付け合成して日次の市場レジーム（bull/neutral/bear）を算出。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを回避。
    - マクロニュースは predefined キーワードでフィルタし、OpenAI で JSON 出力の macro_sentiment を取得（API 失敗時は 0.0 にフォールバック）。
    - レジーム合成、閾値によるラベリング、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - OpenAI クライアント呼び出しは独自実装にしてモジュール結合を避ける。テスト時の差し替えを想定。

- Data モジュール
  - kabusys.data.calendar_management:
    - JPX 市場カレンダー管理（market_calendar）の夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・保存 (ON CONFLICT / upsert 想定)。
    - 営業日判定ユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB データ優先、未登録日は曜日日ベースでフォールバック。
    - 安全策: 最大探索日数制限、バックフィル、last_date の将来日付異常チェック等を実装。

  - kabusys.data.pipeline / etl:
    - ETL パイプライン基盤（ETLResult dataclass を含む）を追加。差分取得、保存、品質チェック連携を想定。
    - ETLResult: ETL のフェッチ数・保存数、品質問題リスト、エラーリストを格納。has_errors / has_quality_errors / to_dict を提供。
    - pipeline モジュールを通じて jquants_client / quality との協調を想定（差分更新・バックフィル・品質チェックの設計方針実装）。

- Research モジュール
  - kabusys.research:
    - factor_research: calc_momentum, calc_value, calc_volatility（ATR, turnover, volume_ratio など）を実装。prices_daily / raw_financials のみ参照して安全にファクターを算出。200 日 MA や ATR のデータ不足時の挙動を明示（None を返す）。
    - feature_exploration: calc_forward_returns（任意ホライズンの将来リターン算出）、calc_ic（Spearman ランク相関による IC 算出）、factor_summary（count/mean/std/min/max/median）、rank（同順位は平均ランク）を実装。
    - 実装は DuckDB SQL + Python 標準ライブラリで行い、外部ライブラリへの依存を最小化。

- 監視・システム設定
  - Settings に CPU/MEM/DISK 閾値、PID ファイルパス、env 判定プロパティ（is_live/is_paper/is_dev）を追加し、監視・実行コンポーネントから利用可能に。

### 変更（設計・安全性）
- ルックアヘッドバイアス対策:
  - AI 判定・ファクター計算・ニュースウィンドウ等で datetime.today()/date.today() を直接参照しない設計。全関数は target_date 引数に依存するように実装。
- フェイルセーフ化:
  - OpenAI API 呼び出し失敗時は例外を上位に投げず、許容範囲で 0.0 またはスキップすることで処理継続を優先（ログで警告を出力）。
- DB 書き込みの idempotency:
  - ai_scores / market_regime 等への書き込みは既存レコードを削除してから挿入する形で冪等性を確保。
- テスト容易性:
  - OpenAI 呼び出し部はモック差し替えしやすい関数として分離（_unfinished _call_openai_api）している。

### 既知の制約 / 注意事項
- OpenAI 関連:
  - gpt-4o-mini を利用、JSON Mode に基づく厳格な JSON 出力を期待するが、実運用での LLM 出力のばらつきに対するパーサーの耐性措置（{} 抽出等）を実装している。
  - API キー (OPENAI_API_KEY) が未設定の場合、score_news / score_regime は ValueError を送出する。
- .env 自動ロード:
  - プロジェクトルート検出に失敗すると自動ロードはスキップされる（パッケージ配布後でも安全）。
  - OS 環境変数はデフォルトで保護され、.env は上書きされない（ただし .env.local は override=True で上書き可能）。
- DuckDB バインド注意:
  - DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、空チェックを事前に行っている。
- 一部モジュールは外部クライアント（jquants_client）に依存。実環境では該当クライアント実装と API トークン等の設定が必要。

### セキュリティ
- 機密情報（トークン・パスワード）は Settings 経由で環境変数から取得する設計。未設定時は明示的にエラーを出して早期検出を促す。

### 破壊的変更
- 初期リリースのため破壊的変更はなし。

---

今後のリリースでの予定（例）
- strategy / execution / monitoring サブパッケージの具体的な取引ロジック・発注インターフェースの追加
- 単体テストと CI の整備、type checking（mypy）とドキュメントの拡充
- OpenAI 呼び出しのコスト管理・レート制御の改善
- jquants_client の抽象化とモック実装の追加

（以上）