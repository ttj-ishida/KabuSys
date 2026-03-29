# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載します。  
フォーマット: https://keepachangelog.com/（日本語訳に準拠）

履歴は semver に従います。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-29
初期リリース — 基本的なデータプラットフォーム、リサーチ、AI、環境設定の実装を含む

### 追加
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - モジュール公開案内（__all__ に data, strategy, execution, monitoring を列挙）。

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供（テスト向け）。
  - エントリ行のパースは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 環境変数保護（読み込み時に既存 OS 環境変数を protected として扱う）を実装。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得する:
    - J-Quants / kabuステーション / Slack / DB パス等の必須/デフォルト値
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ユーティリティ

- AI モジュール（kabusys.ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を集約して銘柄ごとのニューステキストを構築し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/チャンク）、1 銘柄あたり記事数上限・文字数上限の実装。
    - JSON mode を使ったレスポンス検証と堅牢なパースロジック（余分なテキストを含む場合の復元処理を含む）。
    - 429・ネットワーク切断・タイムアウト・5xx に対する指数バックオフの再試行ロジック。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等に書き込み（DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能にしている（モック挿入ポイント）。
  - regime_detector モジュール:
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、calc_news_window を用いてウィンドウ指定。
    - OpenAI 呼び出しに対する再試行・例外ハンドリング。API 失敗時は macro_sentiment=0.0 のフォールバック。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- データモジュール（kabusys.data）
  - calendar_management:
    - market_calendar を扱う営業日判定ユーティリティを実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録がない日や NULL 値に対する曜日ベースのフォールバックを提供。
    - 最大探索日数制限および健全性チェックを実装。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等に更新。バックフィルと健全性チェックを含む。
  - pipeline / etl:
    - ETLResult データクラスを公開（ターゲット日、取得/保存件数、品質問題、エラー等を含む）。
    - ETL 実行方針（差分更新、バックフィル、品質チェックの扱い）を反映したユーティリティ実装の土台を提供。
  - その他:
    - data パッケージの ETLResult 再エクスポート。

- リサーチモジュール（kabusys.research）
  - factor_research:
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR、相対 ATR、出来高比率、平均売買代金）、Value（PER, ROE）ファクター計算関数を実装。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのラグ計算・集計を行う。
    - 不足データ時は None を返す設計。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、rank（同順位は平均ランク）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）を実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。
  - data.stats からの zscore_normalize の再エクスポートを含む。

### 変更（設計上の決定）
- ルックアヘッドバイアス対策:
  - news_nlp と regime_detector を含むすべてのモジュールで datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を渡す設計を採用。
  - DB クエリは target_date を上限排他条件にするなど、未来データの混入を防ぐクエリ設計を採用。

- 耐障害性・冪等性:
  - OpenAI 呼び出しは再試行・タイムアウト・エラー種別で挙動を分け、API エラー時も例外投げずに安全にフォールバックする箇所がある（フェイルセーフ）。
  - DB 書き込みは冪等操作（DELETE → INSERT など）を用いて部分失敗が他データを破壊しないように設計。

- テストフレンドリーな実装:
  - OpenAI 呼び出しの内部関数はモックで差し替え可能（unittest.mock.patch を想定）にしてテストしやすくしている。
  - 設定読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードをオフにできる。

### 修正
- （初期リリースのため該当なし）

### 非推奨
- （初期リリースのため該当なし）

### 削除
- （初期リリースのため該当なし）

### セキュリティ
- OpenAI API キー・Slack トークンなどの機密情報は Settings による環境変数で取得する設計。自動ロードは .env ファイルを扱うが OS 環境変数を保護する仕組みを実装。

---

注記:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートでは更に利用方法、既知の制約、後方互換性の注意点、マイグレーション手順などを追記することを推奨します。