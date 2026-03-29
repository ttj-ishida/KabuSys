# Changelog

すべての重要な変更は Keep a Changelog の慣例に従って記録しています。  
このファイルはパッケージのコードベースから推測して作成した初期リリース向けの変更履歴です。

フォーマット:
- Unreleased — 未リリースの変更 (現時点では空)
- 各バージョンごとにカテゴリ別に要約（Added, Changed, Fixed, Removed, Deprecated, Security）

詳細な設計方針や挙動は各モジュールの docstring に従っています（duckdb 用の互換性処理、LLM 呼び出しのリトライ戦略、ルックアヘッドバイアス回避など）。

## [Unreleased]

---

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース。
- 基本パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - 公開モジュール: data, strategy, execution, monitoring

- 設定・環境変数管理（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - _load_env_file による protected（OS 環境）キー保護と override フラグの扱い。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得（J-Quants, kabu API, Slack, DB パス, 環境種別・ログレベルのバリデーションなど）。
  - 環境変数の必須チェックで未設定時に詳細な ValueError を送出。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ保存する処理を実装。
    - 収集ウィンドウ計算（JST ベースから UTC への変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/チャンク）、記事数・文字数のトリム（最大記事数／最大文字数）によりトークン膨張を抑制。
    - OpenAI 呼び出しは JSON mode を利用し、レスポンス検証ロジックを実装（_validate_and_extract）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。非リトライ系エラーはスキップしてフェイルセーフに継続。
    - DuckDB の executemany の制約に配慮し、空リストバインドを回避する実装。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）に対応。テスト用に _call_openai_api を patch できる設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成で市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio の計算は target_date 未満のデータのみを使用し、データ不足時は中立（1.0）を返す。
    - マクロキーワードで raw_news をフィルタし、LLM に渡して JSON で macro_sentiment を取得。API 失敗時は 0.0 をフォールバック。
    - レジームスコア合成とクリッピング、閾値に基づくラベリングを実装。
    - market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で書き込み。
    - API 呼び出しはテストで差し替え可能（_call_openai_api の独立実装）。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルに基づく営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日は曜日（平日）ベースでフォールバックする一貫したロジック。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
    - 最大探索日数やバックフィル期間などの安全策を導入。

  - ETL パイプライン（pipeline）
    - 差分更新・保存・品質チェックを念頭に置いた ETLResult データクラスを実装。処理結果の集約・エラー/品質問題の報告が可能。
    - _table_exists / _get_max_date 等のユーティリティを実装し、DuckDB との互換性を考慮。

- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高周り）、Value（PER / ROE）を DuckDB SQL ベースで実装。不足データ時は None。
    - duckdb を用いたウィンドウ関数・集約により高効率に計算。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns、可変ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）、ランク付けユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
  - データ系ユーティリティ（kabusys.data.stats からの zscore_normalize の再エクスポートを含む）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を参照する仕組み。API キーそのものの保存・露出は行わない設計（アプリ側で適切に管理することを想定）。

### Notes / 実装上の重要な設計判断（要約）
- ルックアヘッドバイアス防止: 日時参照に datetime.today() / date.today() を直接使用しない設計。target_date を明示的に受け取る。
- フェイルセーフ: LLM 呼び出し失敗や API レスポンス不正時はスコアに中立値を用いるか個別処理をスキップし、全体処理を止めない。
- DuckDB 互換性: executemany の空リスト回避や日付型の安定的扱いなど、DuckDB のバージョン差分に配慮した実装。
- テスト容易性: OpenAI 呼び出し用関数をモジュール内で差し替え可能にしてユニットテストでのモックを容易にしている。

---

（補足）
- 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のリリースノートに追加したいスクリーンショット、互換性情報、既知の問題、マイグレーション手順などがある場合は明示してください。必要であれば各モジュールごとの詳細な変更履歴や開発・運用上の注意点も追記します。