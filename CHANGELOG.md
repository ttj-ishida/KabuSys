# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはプロジェクトの重要な変更点・機能追加・修正を記録します。

最新: 0.1.0（初回リリース）

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01
初回リリース。日本株自動売買／データ基盤／リサーチ用ユーティリティ群を実装。

### Added
- パッケージ構成
  - kabusys コアパッケージを追加。サブパッケージとして data, research, ai, execution, monitoring 等を公開。
  - パッケージバージョンを __version__ = "0.1.0" として定義。

- 環境設定 / config
  - .env ファイルまたは環境変数から設定を読み込む自動ローダ実装（プロジェクトルートは .git / pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサ実装: `export KEY=val` 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理。無効行（空行・コメント・不正フォーマット）を無視。
  - Settings クラスを実装（プロパティ経由で各種設定取得）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / 環境種別（development/paper_trading/live）/ログレベル等を取得・バリデーション。
    - パスは pathlib.Path で返却し expanduser を適用。
    - env / log_level に対する妥当性検査を実装。

- AI モジュール（LLM を利用したニュース解析）
  - kabusys.ai.news_nlp
    - ニュースの時間窓計算（calc_news_window）。
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出する score_news を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄当たりの記事数・文字数トリム、JSON Mode のレスポンス検証・復元ロジックを実装。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで行う。
    - スコアは ±1.0 にクリップ、取得済み銘柄だけを DELETE → INSERT して書き換えることで idempotent に保存。
    - テスト容易性のため _call_openai_api をパッチ差し替え可能に設計。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200日移動平均乖離と LLM によるマクロセンチメントを合成して日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - MA 計算（ルックアヘッド回避のため target_date 未満のデータのみ利用）、マクロ記事抽出、LLM 呼び出し、マクロスコアのリトライ/フォールバックを実装。
    - 最終的なスコアを market_regime テーブルへ冪等（BEGIN/DELETE/INSERT/COMMIT）で保存。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。

- Data / ETL / カレンダー
  - kabusys.data.pipeline
    - ETL 実行結果を表す ETLResult dataclass を追加（品質問題・エラーメッセージの集約、has_errors / has_quality_errors 判定、辞書化メソッド to_dict）。
  - kabusys.data.calendar_management
    - JPX 市場カレンダー管理と営業日判定ロジックを実装。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
      - market_calendar テーブルが未取得の場合は曜日（平日）ベースのフォールバックを行う。
      - next/prev/get_trading_days は DB 登録値優先かつ未登録日は曜日フォールバックで処理し、一貫性を保つ実装。
    - calendar_update_job を実装（J-Quants から差分取得 → 保存、バックフィル _BACKFILL_DAYS、健全性チェック _SANITY_MAX_FUTURE_DAYS）。
    - market_calendar が sparse な場合でも一貫した判定を返す設計。

- Research（ファクター計算・特徴量解析）
  - kabusys.research.factor_research
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - Momentum: 1M/3M/6M リターン、200日MA乖離（データ不足時は None）。
    - Volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率（データ不足は None）。
    - Value: PER（EPS が 0/欠損時は None）、ROE を計算。
    - DuckDB のウィンドウ関数を活用した高効率実装。
  - kabusys.research.feature_exploration
    - calc_forward_returns（任意ホライズンの将来リターンを一度のクエリで取得）、calc_ic（スピアマンランク相関による IC 計算）、rank、factor_summary（基本統計量）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- 共通実装上の注意点／設計判断（ドキュメント化）
  - ルックアヘッドバイアス防止のため、各処理は datetime.today()/date.today() を直接参照しない設計（target_date を引数で与える）。
  - DuckDB を主要なデータストアとして利用。
  - DB 書き込み時は冪等性を重視（DELETE → INSERT、トランザクション利用、ROLLBACK フォールバック）。
  - テストしやすい（内部 API 呼び出しの差し替えポイントを用意）・障害に耐える（API 失敗時のフォールバックやリトライ実装）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （該当なし）

---

注記:
- 実装はソース内のログメッセージ・docstring・例外処理から推測して要点をまとめています。動作環境や外部 API（OpenAI, J-Quants, kabuステーション 等）の設定（APIキー・エンドポイント・.env）を正しく与える必要があります。
- ユーザー向けドキュメント・運用ガイド（API キー管理、cron ジョブ設定、監視設定など）は別途整備することを推奨します。