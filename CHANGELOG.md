# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
日付はリリース日を表します。

## [Unreleased]
- 今後の予定（例）
  - ETL パイプラインおよび jquants_client の更なる堅牢化・単体テスト拡充
  - OpenAI 呼び出しのモニタリング／メトリクス連携
  - ドキュメント整備（API 使用例・migration ガイド）
  - パフォーマンス測定に基づく DuckDB クエリ最適化

## [0.1.0] - 2026-03-29
初期リリース。日本株自動売買システムのコア機能群を実装。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0、主要サブパッケージを公開: data, research, ai, ...）。
- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート自動検出ロジック（.git または pyproject.toml を基準）を導入し、カレントワーキングディレクトリに依存しない読み込みを実現。
  - .env パーサーを強化（export 構文対応、単／二重クォート内のエスケープ処理、インラインコメントの扱い等）。
  - .env の上書き制御（.env → .env.local の優先度）と OS 環境変数保護（protected keys）。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供（J-Quants、kabu API、Slack、DB パス、実行環境判定、ログレベルなどのプロパティ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機構を実装。
- AI ニュース処理（kabusys.ai.news_nlp）
  - score_news: raw_news および news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存。
  - ニュース収集ウィンドウ計算（JST ベースの前日 15:00 ～ 当日 08:30 を UTC に変換して扱う calc_news_window）。
  - バッチ処理（1 API コールあたり最大 20 銘柄）や、1銘柄あたりの最大記事数／最大文字数制限によるトークン肥大対策を実装。
  - OpenAI 呼び出しのリトライ（429、ネットワーク断、タイムアウト、5xx サーバーエラーに対する指数バックオフ）。
  - レスポンスバリデーションと堅牢な JSON パース（前後余計なテキストが混在する場合の復元処理、未知銘柄の無視、スコアの ±1.0 クリップ）。
  - フェイルセーフ設計：API 失敗時はスキップして他銘柄処理を継続、部分成功時は既存スコアを上書きしない（コード絞り込み DELETE → INSERT）。
- AI レジーム判定（kabusys.ai.regime_detector）
  - score_regime: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
  - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）による macro_sentiment 評価、API リトライ・フォールバック（失敗時は 0.0）。
  - ルックアヘッドバイアス防止設計（date 比較は target_date 未満 / 半開区間等の厳密化）。
- Data（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar）用ユーティリティを実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先・未登録日は曜日ベースのフォールバック、最大探索日数制限による無限ループ回避、データ健全性チェック（将来日付の検査）を導入。
    - calendar_update_job: J-Quants API から差分取得→冪等保存（バックフィルと健全性チェック含む）を実装。
  - pipeline:
    - ETLResult データクラスを提供（ETL 実行結果の集約、品質問題とエラー一覧の保持、辞書変換メソッド含む）。
    - ETL パイプラインのヘルパー（最終取得日の判定、差分取得のための max date 抽出等）を実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務を取得し PER/ROE を算出（EPS=0/欠損は None）。
    - DuckDB クエリ主体で実装し、ルックアヘッドバイアスを防止する設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得する汎用実装。
    - calc_ic: ファクターと将来リターンのスピアマン rank 相関（Information Coefficient）を実装。データ不足時は None を返す。
    - rank: 同順位の平均ランク化を行うユーティリティ（丸めによる ties 判定対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
- 実装上の設計方針（全体）
  - ルックアヘッドバイアスの排除（datetime.today()/date.today() に依存しない設計）。
  - DuckDB 互換性やバージョン差異への配慮（executemany の空リスト回避、list バインドの不安定性回避等）。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の使用）。
  - ロギングを多用して処理状況やフォールバック理由を明示。

### Changed
- （初期リリースのため該当なし）

### Fixed
- .env パーサーの強化により、以下のケースを正しく扱うように修正（初期実装に含む）
  - export 構文やクォート内のバックスラッシュエスケープ、インラインコメント処理。
  - 環境変数保護（OS 環境変数が .env によって不意に上書きされないよう保護）。

### Security
- 環境変数読み込みにおいて OS 環境変数を protected として扱い、.env による意図しない上書きを防止する仕組みを導入。
- OpenAI API キーや各種トークンは Settings により環境変数から取得し、明示的に未設定時は例外を投げる（誤った実行を防止）。

### Notes / Known limitations
- OpenAI 呼び出しは gpt-4o-mini と JSON mode を前提としているため、API の仕様変更やレスポンス形式の振る舞いによっては追加対応が必要となる可能性がある。
- DuckDB のバージョン差異（特に executemany とリスト型バインド周り）を考慮した実装になっているが、運用環境の DuckDB バージョンでの動作確認を推奨。
- 一部の外部依存（jquants_client、kabu API クライアント等）は実装を前提としているが、本リリースのコードはそれらクライアントの存在を仮定しているため、実運用前に接続確認が必要。

---

この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時は変更履歴やコミットログを参照して調整してください。