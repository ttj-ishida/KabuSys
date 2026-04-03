# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠します。  
フォーマット: [Unreleased] とバージョンごとのセクション（Added / Changed / Fixed / Removed / Security）。

最新更新日: 2026-04-03

## [Unreleased]

- なし（初回リリースが v0.1.0 のため現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-03

### Added
- 基本パッケージ骨格を追加（kabusys v0.1.0）
  - パッケージメタ情報: src/kabusys/__init__.py (`__version__ = "0.1.0"`)。

- 環境変数 / 設定管理モジュールを追加（src/kabusys/config.py）
  - .env および .env.local の自動読み込みをプロジェクトルート（.git または pyproject.toml）から行う機能を実装。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env の文法パーサを実装（export 形式、シングル/ダブルクォート、インラインコメント、バックスラッシュエスケープ対応）。
  - Settings クラスを追加し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 実行環境設定等のプロパティを提供。
  - 環境変数の必須チェック (_require) と妥当性検査（KABUSYS_ENV, LOG_LEVEL の値検証）を追加。

- AI（NLP）モジュールを追加（src/kabusys/ai）
  - ニュースセンチメント集約（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成し、OpenAI（gpt-4o-mini）の JSON Mode でバッチスコアリング（最大 20 銘柄/リクエスト）を行う score_news を実装。
    - タイムウィンドウ計算（JST基準で前日15:00〜当日08:30相当）と calc_news_window を提供。
    - 1銘柄あたりの記事上限 / 文字数トリム、レスポンスの厳密なバリデーション、スコア ±1.0 のクリップ処理を実装。
    - レート制限・接続断・タイムアウト・5xx に対する指数バックオフのリトライを実装。API失敗時はそのチャンクをスキップして継続するフェイルセーフ設計。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）し、部分失敗時に既存データを保護。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（ウエイト 70%）とマクロ経済ニュースの LLM センチメント（ウエイト 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出する score_regime を実装。
    - ma200_ratio 算出、マクロキーワードによる raw_news フィルタ、OpenAI 呼び出し（gpt-4o-mini）での JSON パース、スコア合成、DuckDB の market_regime への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出し失敗時には macro_sentiment=0.0 として継続するフォールバック、OpenAI の種々の例外を考慮したリトライ処理を実装。
    - ルックアヘッドバイアス対策として target_date 未満のみのデータ参照を徹底（datetime.today() を直接参照しない設計）。

- データプラットフォーム関連モジュールを追加（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーが存在しない場合は曜日ベースのフォールバック（平日を営業日と判断）。
    - calendar_update_job により J-Quants から差分取得して market_calendar を冪等的に更新する処理を実装（バックフィル・健全性チェック付き）。
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - DataPlatform に基づく差分取得・保存・品質チェック方針を文書化し、ETLResult データクラスを実装（src/kabusys/data/pipeline.py）。
    - ETLResult を etl パッケージで再エクスポート（src/kabusys/data/etl.py）。

- 研究 / ファクター計算モジュールを追加（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum：1M/3M/6M リターンおよび 200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility：20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率などの計算。
    - calc_value：raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新財務レコードを target_date 以前から取得）。
    - DuckDB SQL＋ウィンドウ関数を用いた実装。データ不足時の None 返却やスキャン範囲のバッファを実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns：指定ホライズンの将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic：スピアマンランク相関に基づく IC（Information Coefficient）計算を実装。データ不足時は None を返す。
    - factor_summary：カラムごとの count/mean/std/min/max/median を集計。
    - rank：同順位は平均ランクとするランク化ユーティリティ（丸め誤差対策として round を使用）。
  - 研究向けの公開 API（src/kabusys/research/__init__.py）で主要関数を再エクスポート。

- 共通設計上の注意点を実装
  - ルックアヘッドバイアス防止のため、date 引数ベースの設計（関数内部で date.today()/datetime.today() を直接参照しない）。
  - DuckDB を主要なローカルデータストアとして利用（全モジュールが DuckDB 接続を受け取る設計）。
  - OpenAI 呼び出しはモジュール内で独立して実装し、単体テストで差し替えやすくしている（unittest.mock.patch を想定）。
  - API 呼び出し時のリトライ / フェイルセーフ設計（部分失敗を許容し、処理を続行）を採用。
  - DB 書き込みは冪等性を考慮（対象日・対象コードで DELETE → INSERT、トランザクション制御を使用）。

### Changed
- 該当なし（初回リリースのため変更履歴はありません）

### Fixed
- 該当なし（初回リリースのため修正履歴はありません）

### Removed
- 該当なし

### Security
- 環境変数に関する注意:
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で渡す必要あり（未設定時は ValueError を送出）。
  - 自動 .env ロードはプロジェクトルート検出に基づく（配布・テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化推奨）。

---

## 既知の注意点 / 備考
- score_news / score_regime は OpenAI の JSON Mode（response_format={"type":"json_object"}）を前提としているが、実運用では LLM の出力変動に備えた堅牢なパース・バリデーションが行われる設計です。API レスポンスが期待外の場合は該当チャンクをスキップして処理を継続します。
- DuckDB の executemany に対する互換性制約（空リスト不可）を考慮した実装が含まれます（ai_scores 書き込み等）。
- monitoring モジュールはパッケージの公開対象（__all__）に含まれていますが、本リリース時に実装が含まれていない可能性があります。利用時は該当モジュールの有無を確認してください。
- J-Quants / kabu API クライアント（jquants_client、kabu ステーション呼び出し等）は data モジュール内で外部クライアント経由に設計されており、呼び出し側での API トークン注入・モック差し替えが可能です。

---

（注）この CHANGELOG はリポジトリ内のソースコードの実装から推測して作成しています。実際のリリースノートや公開ドキュメントと差分がある場合は適宜調整してください。