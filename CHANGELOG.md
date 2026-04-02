# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
安定したリリースごとにバージョンを付与しています。

フォーマット: 
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

## [Unreleased]
（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-04-02
初回公開リリース。本リポジトリに含まれる主要機能・設計方針をまとめます。

### Added
- パッケージ基盤
  - パッケージ情報を公開（kabusys.__version__ = "0.1.0"）し、主要サブパッケージを __all__ でエクスポート。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
  - .env のパースはシェルスタイル（`export KEY=val` 対応）、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - OS 環境変数を保護するための protected キー対応と .env.local による上書き処理。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視設定 / システム設定（環境・ログレベル）などを型付きプロパティで取得。値検証（有効な env や log level の検査）を実施。

- AI モジュール（kabusys.ai）
  - news_nlp モジュール
    - raw_news と news_symbols を元に、指定タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）内のニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）を用いたセンチメント評価を実行。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数リミット（最大10記事・最大3000文字）を実装。
    - JSON mode のレスポンスを厳密にバリデートし、スコアを ±1.0 にクリップして ai_scores テーブルへ冪等的に（DELETE→INSERT）保存。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフのリトライ、フェイルセーフ（失敗時はスキップして継続）。
    - テスト容易性のため _call_openai_api 関数を patch で差し替え可能に設計。

  - regime_detector モジュール
    - ETF (1321) の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）判定を実装。
    - ニュースの抽出は news_nlp の calc_news_window を利用してウィンドウ内のマクロ関連タイトルを取得。
    - OpenAI 呼び出しは独立実装で、レスポンスパース失敗や API エラー時は macro_sentiment = 0.0 でフォールバック。
    - レジームスコア合成後は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。
    - API キー注入（引数 or 環境変数 OPENAI_API_KEY）に対応。

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール
    - JPX カレンダー（market_calendar テーブル）を扱うユーティリティ群を提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 登録値優先の設計。未登録日は曜日ベース（週末除外）でフォールバック。
    - next/prev の最大探索日数制限（_MAX_SEARCH_DAYS = 60）による無限ループ防止。
    - calendar_update_job を実装し、J-Quants API（jquants_client 経由）から差分取得→冪等保存。バックフィル（日数）と健全性チェックを備える。

  - pipeline / ETL（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（ETL 実行結果の集計と to_dict 実装）。
    - 差分更新・バックフィル・品質チェックの設計方針を実装対象として準備（jquants_client / quality モジュールとの連携を想定）。

- 研究（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M）、200日 MA 乖離、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）等の計算関数を実装。すべて DuckDB を用いた SQL ベース計算。
    - データ不足時の None 処理やログ出力、計算窓のバッファ設計（カレンダー日数の余裕）を実装。
  - feature_exploration
    - 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ランク変換、ファクター統計サマリー（count/mean/std/min/max/median）を提供。
    - 外部依存を減らす（標準ライブラリのみ）方針で実装。

- 共通
  - DuckDB を主要なローカル・分析 DB として利用する設計で、各モジュールが DuckDB 接続を受け取り SQL と Python を組み合わせて処理する構成を採用。
  - トランザクション管理（BEGIN/COMMIT/ROLLBACK）を各所で実施し、例外時には ROLLBACK を試行してログを残す実装。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Security
- 環境変数の自動読み込みは保護機能（既存 OS 環境変数の保護）を内蔵しており、.env.local による上書きを OS 環境変数が阻止される設計を採用。

---

注記／設計方針の強調
- ルックアヘッドバイアス回避: AI スコアリング・レジーム判定・ETL・研究モジュールは内部で datetime.today() / date.today() を乱用せず、呼び出し元から target_date を受け取る形で実装されています。
- フォールバック & フェイルセーフ: 外部 API（OpenAI / J-Quants）失敗時のフォールバック（0 やスキップ）や、ログ出力・リトライ戦略を一貫して導入しています。
- テスト容易性: OpenAI 呼び出しや一部内部関数は patch で差し替え可能に設計し、ユニットテストが書きやすくなっています。
- DB 書き込みは可能な限り冪等（DELETE→INSERT、ON CONFLICT の想定）で実施し、部分失敗時でも既存データを不必要に上書きしない工夫を行っています。

今後の予定（例）
- ai モジュールのレスポンス検証の強化、より細かなログ/メトリクス出力
- ETL パイプラインの実運用フロー実装（スケジューリング、監査ログ）
- research モジュールのパフォーマンス最適化および追加ファクター実装

-->
(この CHANGELOG はコードベースの現状から推測して作成しています。実際のリリースノートとして公開する場合は、実作業ログ・コミットログを基に調整してください。)