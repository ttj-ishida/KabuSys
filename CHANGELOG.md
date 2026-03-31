# Changelog

すべての重要な変更を「Keep a Changelog」準拠の形式で記載します。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成しています。

フォーマット:
- 署名付きの日付（ISO 形式）を使用しています。
- セクションは主に Added / Changed / Fixed / Security を使用しています。

## [Unreleased]
- 今後のリリース予定の注記や進行中の作業をここに記載します。

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能とモジュールを実装しています。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys
  - パッケージの公開 API: data, strategy, execution, monitoring を __all__ に設定（モジュール構成を公開）。

- 環境変数 / 設定管理 (`kabusys.config`)
  - .env / .env.local ファイルの自動読み込み機能を実装（OS 環境変数 > .env.local > .env の優先順位）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーを実装し、export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
  - 既存の OS 環境変数を保護する protected set を用いた上書き制御を実装。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB / 監視 / システム設定をプロパティで取得可能（必須項目は _require() で未設定時に ValueError を送出）。
  - 環境変数値検証: KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL（DEBUG/INFO/...）の妥当性チェック。

- AI 関連モジュール (`kabusys.ai`)
  - news_nlp モジュール
    - raw_news と news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出、ai_scores テーブルへ書き込み。
    - タイムウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window() で提供。
    - バッチサイズ、トークン肥大対策（記事数・文字数上限）を導入。
    - JSON Mode を利用し厳密な JSON レスポンスを期待、レスポンスのバリデーションと安全なパースを実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。失敗時はそのチャンクをスキップ（フェイルセーフ）。
    - テスト用に OpenAI 呼び出し関数をモック差し替え可能に設計（_call_openai_api）。
    - DuckDB への書き込みは冪等操作（DELETE → INSERT）を採用し、部分失敗時に既存スコアを保護。
  - regime_detector モジュール
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算は target_date 未満のデータのみを参照しルックアヘッドバイアスを防止。
    - マクロニュースは raw_news からマクロキーワードでフィルタしてタイトルを抽出し、OpenAI へ投げてスコアを算出（記事なし時は LLM 呼び出しを行わず macro_sentiment=0.0）。
    - OpenAI 呼び出しの再試行（リトライ）、エラー時のフェイルセーフ（macro_sentiment=0.0）を実装。
    - 結果は market_regime テーブルへトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等書き込み。失敗時は ROLLBACK を試行し、失敗ログを記録。

- データ基盤モジュール (`kabusys.data`)
  - calendar_management モジュール
    - JPX カレンダー管理（market_calendar テーブル）および営業日判定ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day のユーティリティを提供。
    - DB 登録データを優先し、未登録日は曜日ベースでフォールバックする一貫した設計。
    - 夜間バッチ calendar_update_job により J-Quants API から差分取得して冪等保存（fetch + save）を実装。バックフィル・健全性チェックを実装。
  - pipeline / etl モジュール
    - ETLResult データクラスを公開し ETL 実行結果を収集・出力可能に（品質チェック結果や発生エラーを含む）。
    - pipeline での差分更新・保存（jquants_client への委譲）・品質チェック（quality モジュール利用）を想定した構成。
    - _get_max_date や _table_exists 等のユーティリティ、初期データ取得開始日等の定数を定義。

- リサーチ・分析モジュール (`kabusys.research`)
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）などのファクター計算関数を実装。
    - DuckDB 内の SQL ウィンドウ関数等を駆使して効率的に計算。データ不足時は None を返す等の堅実な挙動。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（Spearman ランク相関）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない、標準ライブラリ + DuckDB ベースの実装。

- 共通・実務的な設計上の配慮
  - ルックアヘッドバイアス対策: 各種モジュールで datetime.today() / date.today() 参照を避け、呼び出し側が target_date を与える方式を採用。
  - API 呼び出しのモック可能設計: テスト容易性のため OpenAI 呼び出し部分等を差し替え可能に実装。
  - DuckDB を主要な分析 DB として使用。SQL の互換性やバージョン差異（executemany の空リスト等）へ注意した実装。
  - トランザクション管理と例外処理: 重要な DB 書き込みは BEGIN/COMMIT/ROLLBACK を使用し、ROLLBACK 失敗時のログ出力を実装。
  - ロギングを広範囲に導入し、処理状況・警告・エラーを詳細に出力するよう設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーが未設定の場合は明示的に ValueError を送出する（news_nlp.score_news / regime_detector.score_regime など）。API キーは引数で注入可能でテスト時に環境変数依存を回避可能。
- .env 読み込みは標準 UTF-8、読み込み失敗時は警告を出力して処理を継続。

### Known limitations / Notes
- OpenAI への依存: LLM レスポンスの品質により結果が変動するため、レスポンス検証・フォールバック処理を実装しているが、運用では API 制限やコスト管理が必要。
- データ不足時のフォールバック:
  - ma200_ratio の計算に必要なデータが不足する場合は中立（1.0）を採用。
  - マクロセンチメントや AI スコア取得失敗時は 0.0 を採用して処理を継続（フェイルセーフ）。
- DuckDB バージョン差異に注意（executemany の挙動等）。コード中に互換性考慮のコメントを含む。
- jquants_client / quality モジュールの具体実装は外部依存（本 changelog は現行コードから推測して記載）。

---

（必要があれば、各モジュールごとの詳細な変更点や例、利用方法を追加できます。どのレベルの詳細を出力するか指示してください。）