# Changelog

すべての重要な変更点はこのファイルに記録します。フォーマットは「Keep a Changelog」準拠です。  
現在のパッケージバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-03

初回リリース。以下の主要機能と設計上の方針を実装・公開しました。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__init__、__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ に定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - .env パーサ実装（export 形式、クォート、インラインコメント、エスケープ対応）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 必須キー取得時に未設定であれば ValueError を投げる _require を追加。
  - 各種設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / env 判定 / log level 等）と入力バリデーション。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定・SQ判定・前後営業日探索・営業日リスト取得機能を追加。
    - DB データ優先・未登録日は曜日ベースのフォールバック、探索上限を設定して無限ループを防止。
    - 夜間バッチ calendar_update_job を追加（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン（pipeline, etl）
    - ETLResult dataclass を導入し、ETL 実行の取得数／保存数／品質問題／エラーを体系的に保持。
    - データソース差分取得・保存・品質チェックの設計方針を実装（_backfill、calendar lookahead 等）。
    - etl モジュールで pipeline.ETLResult を再エクスポート。

- 研究・因子モジュール（kabusys.research）
  - factor_research:
    - モメンタム（calc_momentum）：1M/3M/6M リターン、200日 MA 乖離算出。
    - ボラティリティ / 流動性（calc_volatility）：20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - バリュー（calc_value）：EPS/ROE を用いた PER/ROE 計算（raw_financials から最新レコードを取得）。
    - 各関数は DuckDB 上の prices_daily / raw_financials を参照し、(date, code) ベースの辞書リストを返す。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）のリターンを一括取得。
    - IC 計算（calc_ic）：ファクターと将来リターンのスピアマン（ランク相関）計算。
    - ランク関数（rank）：同順位は平均ランクに処理、丸め誤差対策あり。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。

- AI ベースのスコアリング（kabusys.ai）
  - ニュース NLP（news_nlp.score_news）
    - raw_news と news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI gpt-4o-mini に送信。
    - バッチ処理（1コール最大 20 銘柄）、記事・文字数のトリム、リトライ（429/ネットワーク/5xx に対する指数バックオフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code/score の型検証、スコアクリップ ±1.0）。
    - 成功した銘柄のみを ai_scores テーブルに置換的に書き込み（DELETE→INSERT、部分失敗で他銘柄を保護）。
    - ルックアヘッドバイアス回避のため target_date ベースのウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）。
    - OpenAI API キーの注入、テスト用に _call_openai_api を差し替え可能。
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロ記事抽出、OpenAI による JSON レスポンス処理、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）。
    - score を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス防止設計（prices_daily の date < target_date 等）。

- 安全・互換性・運用関連
  - DuckDB の executemany 空リスト制約（0.10 等）に対するガード実装（空リスト時の呼び出し回避）。
  - 各モジュールでのトランザクション制御と ROLLBACK のフォールバックロギング。
  - OpenAI SDK の各種例外型（RateLimitError, APIConnectionError, APITimeoutError, APIError）への対応とログ出力。

### Changed
- （初版のため履歴上の変更履歴はありません）

### Fixed
- （初版のため特定のバグ修正履歴はありません）

### Deprecated
- （なし）

### Removed
- （なし）

### Security
- OpenAI API キー未設定時に明示的なエラー（ValueError）を投げるようにして、不正な呼び出しを防止。

---

注記:
- 多くの設計箇所で「ルックアヘッドバイアス防止」「フェイルセーフ（API 失敗時は中立またはスキップして継続）」「DB 書き込みの冪等性」が明示的に採用されています。  
- 実際の運用では OpenAI API キー、J-Quants トークン、Kabu API パスワード等の環境変数設定が必要です（kabusys.config.Settings を参照してください）。