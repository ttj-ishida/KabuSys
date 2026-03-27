# Changelog

すべての注目すべき変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に従います。
<https://keepachangelog.com/ja/1.0.0/>

注: 日付はリリース日を示します。

## [Unreleased]
（現在の開発中の変更はここに記載します）

## [0.1.0] - 2026-03-27
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。公開エントリポイントと主要サブパッケージを __all__ で定義。
- 環境設定 / 起動時自動ロード
  - env/.env ファイルおよび環境変数を扱う設定モジュールを追加（kabusys.config）。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準に探索）。
  - .env/.env.local の自動読み込み機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env のパースを堅牢化（export 形式対応、クォート内のエスケープ、インラインコメント処理など）。
  - 環境変数保護機能（既存OS環境変数を保護して .env で上書きしない）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /実行環境・ログレベル等のプロパティを公開。
  - 環境変数検証（有効な env 値、ログレベルチェック、必須変数未設定時は明示的なエラー）。

- データプラットフォーム（DuckDB ベース）
  - ETL 結果を表す ETLResult データクラス追加（kabusys.data.pipeline）。
  - ETL パイプライン基盤（差分取得・保存・品質チェック等の方針、ユーティリティ関数）を実装。
  - market_calendar を扱うマーケットカレンダー管理モジュールを追加（kabusys.data.calendar_management）。
    - 営業日判定（is_trading_day）、次/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）、SQ判定（is_sq_day）を実装。
    - JPX カレンダーを J-Quants から差分取得して更新する夜間バッチジョブ（calendar_update_job）を追加。
    - DB 登録値優先、未登録日は曜日フォールバックする安定した設計。
  - データ ETL ユーティリティの公開インターフェース（kabusys.data.etl）。

- ニュース・AI（OpenAI 統合）
  - ニュースセンチメント解析（kabusys.ai.news_nlp）を追加。
    - 指定の時間ウィンドウ（前日15:00 JST〜当日08:30 JST）に基づき raw_news と news_symbols を集約し、銘柄ごとに LLM（gpt-4o-mini）でセンチメントを評価。
    - バッチ処理（最大 20 銘柄/回）、記事数/文字数トリム、結果のバリデーション、スコアクリップ、DuckDB への冪等書き込みを実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライとフェイルセーフ（失敗時は対象銘柄をスキップ）を実装。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能に実装（ユニットテストでモック可能）。
  - 市場レジーム判定（kabusys.ai.regime_detector）を追加。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組合せて日次レジーム（bull/neutral/bear）を判定し DB に冪等保存。
    - prices_daily / raw_news / market_regime テーブルを用いる処理フローを実装。
    - API 呼び出しのリトライ・フェイルセーフ（失敗時は macro_sentiment=0.0）を実装。
    - LLM プロンプトは JSON 出力を想定し、レスポンスパース失敗時の復元ロジックやログ出力を実装。
- リサーチ／ファクター
  - research パッケージを追加（kabusys.research）。
  - factor_research モジュールでモメンタム・ボラティリティ・バリュー等のファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離など。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率など。
    - calc_value: PER、ROE（raw_financials と prices_daily を結合）。
    - 全関数は DuckDB への SQL クエリで実装し、外部 API にアクセスしない設計。
  - feature_exploration モジュールで将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク化ユーティリティ（rank）を実装。
    - calc_forward_returns は可変ホライズン対応、入力検証、単一クエリでの取得に最適化。
    - calc_ic はスピアマンのランク相関を厳密に計算（同順位は平均ランクに対応）。
    - factor_summary は count/mean/std/min/max/median を算出。

### Changed
- 設計上の選択と安全策（プロジェクト初期からの方針）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() をコア処理内で直接参照しない設計を徹底（すべての集計/スコアリングで target_date を明示的に渡す）。
  - DuckDB への書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT など）して部分失敗時に既存データを保護。
  - OpenAI 呼び出しは失敗時に処理全体を停止しないフェイルセーフな振る舞い（ログ出力＋スコア無視または 0.0 フォールバック）を採用。
  - .env パーサーや API ハンドリングで詳細なログ出力とワーニングを追加。

### Fixed
- （初回リリースのため過去のバグ修正は無し。実装時に発見された堅牢化・エラーハンドリングは上記 Added に含む）

### Security
- 環境変数取り扱いの配慮
  - OS 環境変数を保護する protected 機構により、意図せぬ .env による上書きを防止。
  - OpenAI API キーや Slack トークン等の必須変数が未設定の場合は明示的にエラーを発生させることで、誤った挙動や秘密情報の漏洩を抑止。

### Notes / Implementation details
- OpenAI SDK 呼び出しは内部で切り替え可能（テスト用にモックしやすい実装）。
- ニュース集約やファクター計算は DuckDB のウィンドウ関数や SQL で実施し、外部ライブラリに依存しない軽量実装。
- 一部モジュールは jquants_client や quality モジュールを参照（外部 API クライアント／品質チェックロジックは別モジュールとして分離）。
- DuckDB バインドに関する互換性配慮（executemany の空リスト回避など）を実装。

---

今後の予定（例）
- 詳細な CLI / ジョブスケジューラ統合
- モニタリング・アラート（Slack 通知の実装）
- 単体テスト・統合テストの拡充と CI 設定
- パフォーマンス最適化（大規模データ時のクエリチューニング）