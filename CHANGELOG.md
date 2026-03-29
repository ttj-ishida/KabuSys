# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0（初回リリース）

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買システム「KabuSys」のコアモジュール群を実装しました。主な追加点・設計方針・注意点を以下にまとめます。

### 追加(Added)
- パッケージ初期化
  - kabusys パッケージのバージョン管理を追加（__version__ = "0.1.0"）。
  - 公開 API として data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みするユーティリティを実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml から自動検出して決定。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のエスケープ処理に対応。
    - インラインコメントの扱い（クォートの有無に応じた適切な無視）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得用の _require()、Settings クラス（J-Quants / kabu ステーション / Slack / DB パス / 環境・ログレベル等）を実装。
  - env / log_level の検証（許可値チェック）を実装。
  - SQLite / DuckDB のデフォルトパス設定を追加。

- AI（自然言語処理）機能 (kabusys.ai)
  - news_nlp モジュール:
    - raw_news を集約して OpenAI（gpt-4o-mini）の JSON Mode を使い銘柄ごとのセンチメント ai_score を算出する score_news を実装。
    - タイムウィンドウ計算（JST基準で前日15:00～当日08:30）を calc_news_window で提供。
    - API 呼び出しはバッチ化（最大20銘柄／チャンク）、トークン肥大化対策（記事数／文字数制限）。
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフ／リトライ実装。
    - レスポンスの堅牢なバリデーションと部分成功時の DB 置換ロジック（DELETE → INSERT、部分失敗でも既存スコアを保護）。
    - テスト容易性のため _call_openai_api を patch できる設計。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（加重0.7）と、マクロニュースの LLM センチメント（加重0.3）を合成して日次の市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily / raw_news / market_regime を参照し、冪等的に market_regime テーブルへ書き込み。
    - マクロニュース抽出、OpenAI 呼び出し（JSON Mode）、リトライ、フェイルセーフ（API失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス回避のため datetime.today() を直接参照しない設計。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱うユーティリティ群を実装（営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
    - DB に登録されているカレンダー値を優先し、未登録日は曜日ベース（土日非営業）でフォールバックする一貫したロジック。
    - calendar_update_job：J-Quants から差分取得して market_calendar を冪等更新。バックフィル／健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - 差分取得、保存（idempotent 保存）、品質チェックを念頭に置いた ETL 設計方針を反映する基盤実装（pipeline モジュールにて一部ユーティリティを提供）。
    - DuckDB を前提にした最大日付取得、テーブル存在チェックを実装。

- リサーチ (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M、ma200 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER, ROE）の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL を用いた効率的なウィンドウ計算を採用。結果は (date, code) ベースの dict リストで返却。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンのランク相関 calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
    - pandas 等に依存せず、標準ライブラリ＋DuckDB のみで実装。

### 変更(Changed)
- （初回公開のため該当なし）

### 修正(Fixed)
- （初回公開のため該当なし）

### 削除(Removed)
- （初回公開のため該当なし）

### セキュリティ(Security)
- OpenAI API キーやその他機密値は Settings で必須チェックを行うが、.env 自動ロード時に OS 環境変数が優先され、既存 OS 環境変数は保護される（.env の強制上書きを防止）。
- 自動 .env ロードを環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 既知の注意点 / 設計上の重要事項
- ルックアヘッドバイアス回避:
  - 多くの処理（score_news, score_regime, ETL 等）は内部で date 引数を受け取り、datetime.today()/date.today() を直接参照しない設計です。運用時は明示的に target_date を渡して下さい。
- OpenAI 呼び出し:
  - JSON Mode を使用する設計だが、実際の SDK/モデルの挙動により前後テキストが混入する可能性を考慮してレスポンス復元ロジックを実装しています。
  - テスト時は _call_openai_api をモックすることを想定。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーになるバージョンを考慮したガードを実装（params が空でないことを確認してから executemany を呼ぶ）。
- フェイルセーフ:
  - LLM API の失敗等は基本的に例外を投げずフォールバック（0.0 やスキップ）して処理を継続する設計です。重要な DB 書き込み失敗時はロールバックして例外を上位に伝播します。
- テスト容易性:
  - OpenAI 呼び出しや time.sleep 等を差し替え可能にしてユニットテストでの制御を容易にしています。

### 互換性(Breaking Changes)
- 初回リリースのため互換性の変更点はありません。今後のバージョンで API を安定化させる予定です。

---

このリリースは主要機能の基盤実装が中心です。次のリリースでは以下を予定しています（非包括的）:
- strategy / execution / monitoring モジュールの詳細実装と統合テスト
- パフォーマンス改善、より厳密な型注釈の追加
- CLI やジョブスケジューラ統合のためのユーティリティ

ご要望や不具合報告があれば issue を作成してください。