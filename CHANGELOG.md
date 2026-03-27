# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、変更の重大度はカテゴリ別に整理しています。

- 既知の慣例: "Added", "Changed", "Deprecated", "Removed", "Fixed", "Security"

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-27
初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは 0.1.0（src/kabusys/__init__.py）。
  - パッケージ公開 API として data, research, ai, config 等の主要モジュールを整備。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルと環境変数を統合して読み込む自動ローダを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - パッケージ配布後も安定動作するよう、__file__ を起点にプロジェクトルート（.git または pyproject.toml）を探索。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース処理を実装（export 形式、クォート、エスケープ、行末コメント対応など）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パスなど主要な設定プロパティを公開。
  - 入力検証: KABUSYS_ENV（development, paper_trading, live）や LOG_LEVEL（DEBUG など）の妥当性チェックを実装。
  - 必須変数未設定時にわかりやすい ValueError を発生させる _require ヘルパ。

- データ関連（kabusys.data）
  - ETL パイプライン基盤（data.pipeline）を実装。
    - 差分取得・保存・品質チェックのワークフローに対応。
    - ETLResult データクラスを公開して実行結果・品質問題・エラー情報を集約（kabusys.data.etl で再エクスポート）。
  - マーケットカレンダー管理（data.calendar_management）を実装。
    - DB（market_calendar）ベースの営業日判定、next/prev_trading_day、get_trading_days、is_sq_day を提供。
    - DB 未取得時は曜日ベースのフォールバックを行う堅牢設計。
    - calendar_update_job: J-Quants からカレンダーを差分取得して冪等保存する夜間バッチ処理を実装（バックフィルと健全性チェック付き）。

- 研究（research）
  - ファクター計算群を実装（kabusys.research）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を算出。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率などを算出。
    - calc_value: raw_financials を用いた PER / ROE の算出（直近財務レコードを結合）。
  - 特徴量探索・評価ユーティリティ
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得可能（horizons のバリデーション、パフォーマンス考慮の探索範囲）。
    - calc_ic: Spearman（ランク）相関による IC 計算（欠損・同順位処理対応）。
    - rank / factor_summary: ランク化・統計サマリー機能を実装。
  - 標準ライブラリのみで動作するように設計（pandas 等に依存しない）。

- AI / NLP（kabusys.ai）
  - ニュースセンチメント（news_nlp）モジュールを実装。
    - raw_news と news_symbols を結合して銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）によるバッチ評価を行う。
    - バッチサイズや文字数制限、429/ネットワーク/5xx のエクスポネンシャルバックオフ、JSON レスポンス検証・クリップ（±1.0）などの堅牢性を備える。
    - calc_news_window による JST 基準のニュース収集ウィンドウ計算を提供（ルックアヘッドバイアス回避のため date を引数で受ける設計）。
    - API 呼び出しはテスト容易性のため差し替え可能（_call_openai_api のモック対応）。
  - 市場レジーム判定（regime_detector）モジュールを実装。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次のレジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込み。
    - マクロキーワードによる raw_news フィルタリング、OpenAI への JSON 出力期待、リトライとフェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - DB クエリはルックアヘッドを防止する条件（date < target_date 等）を明確に指定。

### Changed
- 設計方針の明確化（初期実装としての宣言）
  - 多くのモジュールで「datetime.today() / date.today() を参照しない」設計が明示され、ルックアヘッドバイアス防止を重視。
  - DuckDB を用いた SQL+Python ハイブリッド設計で、DB 内で集計・ウィンドウ関数を活用する方針を採用。

### Fixed
- エラーハンドリングとフェイルセーフ
  - OpenAI API 呼び出し周りで、RateLimit / 接続エラー / タイムアウト / 5xx を個別に扱い、適切にログ出力してフォールバック（多くは 0.0 or スキップ）する実装を追加。
  - DB 書き込み時に BEGIN/COMMIT/ROLLBACK を用いた冪等性とトランザクション保護を徹底。ROLLBACK 失敗時は警告ログを出す。

### Deprecated
- なし

### Removed
- なし

### Security
- なし

備考:
- OpenAI API キーは各関数の引数で注入可能。省略時は環境変数 OPENAI_API_KEY を参照する設計で、テスト時に鍵を直接注入することで外部依存を切り離せます。
- DuckDB バインド時の互換性（executemany が空リストを受け付けない等）に配慮した実装上の注意が各所に記載されています。
- 本 CHANGELOG はコードベースから推測して作成した初期リリースの要約です。実際のリリースノート作成時はコミットログ・Issue 等を参照して追記してください。