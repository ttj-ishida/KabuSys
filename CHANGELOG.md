# CHANGELOG

すべての重要な変更履歴をこのファイルに記録します。  
このドキュメントは "Keep a Changelog" の形式に準拠します。

フォーマット:
- Unreleased: 今後の変更
- 各バージョン: 変更のカテゴリ別（Added, Changed, Fixed, Removed, Security）

<!-- NOTE: 実装コードからの推測に基づき CHANGELOG を作成しています。 -->

## [Unreleased]
- 今後の変更予定はここに記載します。

## [0.1.0] - 2026-04-03
初回公開リリース。日本株自動売買システム "KabuSys" の基盤モジュール群を実装・公開。

### Added
- パッケージの基本情報
  - パッケージ名: kabusys、バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を登録（パッケージ公開インターフェースの準備）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
  - 自動ロードの優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用）。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - 環境変数の上書き時に OS 環境変数を保護する protected 機能を実装。
  - Settings クラスを提供し、各種設定を property で取得:
    - J-Quants / kabu API / LINE / DB（DuckDB/SQLite）/監視設定等の既定値と必須チェック。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証。
    - kill_flag_clear_on_start, CPU/Memory/Disk の閾値など監視用設定を提供。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へ送信してセンチメントを算出。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1銘柄あたりの記事数と文字数制限（最大記事数/最大文字数）。
    - OpenAI の JSON mode を使用し、レスポンスのバリデーションとスコアの ±1.0 クリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx サーバーエラーに対する指数バックオフのリトライ処理を実装。
    - レスポンスパース失敗や API エラーは安全にスキップし、処理を継続（フェイルセーフ）。
    - 成果物を ai_scores テーブルに冪等的に書き込み（部分失敗時に他銘柄データを保護する実装）。
    - テスト容易性のため OpenAI 呼び出し箇所（_call_openai_api）を差し替え可能に実装。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定。
    - マクロキーワードで raw_news を抽出し、OpenAI で macro_sentiment を評価（記事なしは LLM 呼び出しを行わず 0.0 を採用）。
    - レジームスコア合成と閾値判定（BULL/BEAR の閾値設定）。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - API の再試行処理とフェイルセーフ（API 失敗時は macro_sentiment = 0.0 で継続）。

- データ基盤モジュール (kabusys.data)
  - 市場カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを利用した営業日判定・前後営業日探索・期間内営業日列挙・SQ判定を提供。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - next_trading_day / prev_trading_day は最大探索範囲を設け、無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィルと健全性チェックを実装。
    - jquants_client を介したデータ取得/保存のためのフックを用意。

  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの集約）。
    - 差分更新・バックフィル・品質チェック（quality モジュール）を意識した設計。
    - jquants_client を用いた idempotent な保存処理、品質チェックの結果収集をサポート。
    - DuckDB テーブル存在チェック、最大日付取得などユーティリティを実装（ETL 内部で利用）。

- 研究用モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算（データ不足ハンドリング）。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算（EPS が 0 または欠損のハンドリング）。
    - SQL ベースの実装により DuckDB 上で高速に実行可能。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（ホライズンの検証あり）。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算（有効レコード 3 未満は None）。
    - rank: 同順位は平均ランクを採るランク化関数（丸めによる ties 対応）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算。
  - research パッケージは便利関数を再エクスポート（zscore_normalize 等）。

### Changed
- なし（初回リリースのため）。

### Fixed
- DuckDB 特有の注意点に対応:
  - executemany に空リストを渡すと失敗する点に配慮し、空チェックを追加して安全に処理。
- OpenAI API 呼び出しに関する堅牢性強化:
  - 429/ネットワーク/タイムアウト/5xx に対するリトライとバックオフを実装。
  - API レスポンスの JSON パース失敗時の復元処理（文字列内の最外側の {} を抽出してパース試行）を実装。
- 環境変数パーサの強化:
  - export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント判定などを正しく処理。

### Removed
- なし。

### Security
- OpenAI API キーは明示的に引数で注入可能（api_key）か、環境変数 OPENAI_API_KEY を参照する実装。
- 環境ファイル自動読み込み時に OS 環境変数を保護する機構を導入（.env による上書きを防止可能）。

### Notes / Breaking changes
- 初回リリースのため後方互換性の破壊は存在しません。ただし将来のリリースで設定名や DB スキーマを変更する可能性があります。
- OpenAI の使用は gpt-4o-mini（JSON mode）を想定しているため、API 仕様が変わると調整が必要です。
- DuckDB 上のテーブル構成（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を前提とした実装です。実行前にスキーマ整備が必要です。

---

作成にあたっては、ソースコード内の docstring / コメント / 実装内容から機能・挙動を推測して CHANGELOG を生成しました。実際のリリースノート作成時は、実際のコミット履歴やリリース日・影響範囲に応じて調整してください。