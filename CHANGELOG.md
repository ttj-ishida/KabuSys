# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  

注: 本 CHANGELOG は提供されたコードベースの内容（docstring と実装）から推測して作成しています。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-03

初回リリース。日本株自動売買プラットフォームの基本コンポーネントを実装。

### 追加 (Added)

- パッケージ
  - kabusys パッケージ初期公開。__version__ = 0.1.0。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env/.env.local の読み込み順序と上書きルールを実装。OS 環境変数保護のための protected キーセットを考慮。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - export 形式やクォート、インラインコメント等を扱う堅牢な .env パーサを実装。
  - Settings クラスを公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須値取得（未設定時は ValueError）。
    - KABU_API_BASE_URL, LINE 関連トークン、データベースパス（DuckDB/SQLite）、監視用ファイルパス、CPU/メモリ/ディスク閾値などの設定プロパティ。
    - 環境 (development/paper_trading/live) とログレベルのバリデーション。
    - is_live/is_paper/is_dev ヘルパー。

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し OpenAI（gpt-4o-mini, JSON mode）で銘柄別センチメントを算出して ai_scores に書き込む処理を実装。
    - 時間ウィンドウ計算（JST 基準を UTC naive datetime に変換）を提供（calc_news_window）。
    - 1銘柄あたりの最大記事数・最大文字数でトリムする仕組みを実装（トークン肥大対策）。
    - バッチ処理（最大 20 銘柄/コール）、リトライ（429/ネットワーク/タイムアウト/5xx は指数バックオフ）、レスポンスの厳密なバリデーションを実装。
    - API 失敗時は例外投げずスキップしてフェイルセーフ（部分成功時は取得できた銘柄のみ置換保存）。
    - DuckDB executemany の空リスト問題を回避する処理を取り入れた idempotent な DELETE→INSERT 更新。
    - テスト容易性のため _call_openai_api を patch 可能に設計。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する処理を実装。
    - MA 計算は target_date 未満のデータのみを使用しルックアヘッドバイアスを排除。
    - マクロ記事が存在しない場合や API エラー時は macro_sentiment=0.0 にフォールバック（例外を上げない）。
    - OpenAI 呼び出しは独立実装。リトライ / バックオフ / 5xx 判定等を備える。
    - DB 書込は BEGIN/DELETE/INSERT/COMMIT による冪等操作。失敗時は ROLLBACK を試行して例外を伝播。

- データ / ETL / カレンダー (src/kabusys/data/)
  - ETL パイプラインのための ETLResult クラスを実装（pipeline.ETLResult を公開）。
    - 取得件数・保存件数・品質検査結果・エラー一覧などを含む構造化結果オブジェクト。
    - 品質検査の重大度判定ヘルパー（has_quality_errors）と辞書化（to_dict）を実装。
  - pipeline モジュール（ETL の骨格）を実装（差分更新、バックフィル、品質チェック方針を定義）。
    - J-Quants クライアント（jquants_client）を介して差分取得・保存する設計。
    - 品質チェックは呼び出し元で対処できるよう非致命的に収集する設計（Fail-Fast ではない）。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定 API を実装:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB 登録がない日や NULL 値に対しては曜日ベース（平日のみ営業日）でフォールバックする設計。
    - calendar_update_job を実装（J-Quants API から差分取得、バックフィル、保存、健全性チェック）。
    - 最大探索日数やバックフィル日数、見通し日数などの安全パラメータを定義。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research: モメンタム（1/3/6M）、ma200 乖離、ATR（20日）、流動性指標、財務ベースの value 指標（PER/ROE）などの計算関数を実装。
    - DuckDB を利用した SQL 中心の実装。prices_daily / raw_financials テーブルを参照。
    - データ不足時は None を返す設計。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）などを実装。
    - pandas 等に依存しない純 Python 実装。ルックアヘッドバイアス回避の設計を明記。
  - research パッケージの __all__ により主要関数を再公開。

- モニタリング / システム設定
  - PID ファイル・kill flag のパスとクリア挙動、CPU/メモリ/ディスク閾値など監視用設定を Settings に提供。

### 変更 (Changed)

- なし（初回リリース）

### 修正 (Fixed)

- なし（初回リリース）

### 削除 (Removed)

- なし

### セキュリティ (Security)

- なし特記

### 実装上の重要な設計上の注記（リリースに含むべきポイント）

- ルックアヘッドバイアスの防止
  - AI スコアやファクター計算はすべて target_date ベースで外挿せず、データ取得クエリは target_date 未満/等の適切な排他条件を使用。
  - datetime.today()/date.today() をスコア/計算の内部ロジックで直接参照しない方針。

- フェイルセーフ性
  - OpenAI API 呼び出し失敗時はデフォルト（中立）スコアにフォールバックするなど、致命的失敗を避ける設計。
  - ETL の品質チェックはエラーを収集するが処理を続行し、呼び出し側が判断できるようにしている。

- テスト容易性
  - OpenAI 呼び出し部分や内部呼び出し（例えば _call_openai_api）を patch/モック可能にしてユニットテストを容易にしている。
  - Settings 周りは環境変数の注入で制御可能。

- データベース操作
  - DuckDB を前提とした SQL 実装。idempotent 書き込み（DELETE→INSERT、ON CONFLICT 相当の扱い）や executemany に関する注意（空リストバインド回避）を考慮。

- 外部依存の最小化
  - 解析/統計処理は標準ライブラリのみで実装し外部ライブラリ依存を避ける方針。

---

今後のリリースでは、テストケース、ドキュメント（API 仕様）、CI/パイプライン、運用用スクリプト（デプロイ/監視/ロールバック）の追加が想定されます。必要であれば、この CHANGELOG を拡張して Unreleased セクションに今後の変更候補を記載できます。