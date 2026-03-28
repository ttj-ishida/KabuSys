# Changelog

すべての注目すべき変更点はここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。以下の主要機能・モジュールを実装しました。

### Added
- パッケージ概要
  - 基本パッケージ定義を追加（kabusys.__init__, バージョン = 0.1.0）。

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト時に利用可能）。
  - .env パース機能実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応）。
  - Settings クラスを追加し、環境変数経由の各種設定をプロパティ提供（J-Quants / kabuステーション / Slack / DB パス / env / log_level 等）。
  - env, log_level の検証（有限の値集合をチェック）と is_live / is_paper / is_dev のユーティリティプロパティを実装。

- データ処理基盤（src/kabusys/data/*）
  - カレンダー管理（calendar_management.py）
    - JPX マーケットカレンダーの夜間更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 冪等保存。
    - 営業日判定ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない/未登録日の場合は曜日ベースのフォールバックを行う設計。
    - 最大探索日数制限や健全性チェック、バックフィルロジックを実装。
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを追加して ETL 実行結果を集約。
    - 差分取得、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - DuckDB との互換性を考慮した実装（テーブル存在判定、MAX 日付取得などのユーティリティ）。
  - jquants_client の再利用想定インターフェースを呼び出す設計に。

- 研究（research）モジュール（src/kabusys/research/*）
  - factor_research.py
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR、ATR 比率）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）を DuckDB データから計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理とログ出力を実装。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）。
    - IC（Information Coefficient：Spearman の ρ）計算（calc_ic）。
    - 値をランクに変換するユーティリティ（rank）とファクターの統計サマリー（factor_summary）。
  - research パッケージの __init__ で主要関数を再エクスポート。

- AI / NLP 機能（src/kabusys/ai/*）
  - ニュースセンチメント（news_nlp.py）
    - raw_news と news_symbols から対象記事を銘柄ごとに集約し、OpenAI（gpt-4o-mini、JSON mode）へバッチ送信してスコアを取得、ai_scores テーブルへ書き込む機能（score_news）。
    - タイムウィンドウ設計（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して比較）とトークン肥大化対策（記事数・文字数制限）。
    - バッチ処理（最大 20 銘柄）、429/ネットワーク/タイムアウト/5xx に対する指数バックオフ・リトライ、レスポンスの厳格なバリデーションを実装。
    - JSON parse 回復処理（前後余計テキストから最外の {} を抽出）や数値チェック、スコアクリップ（±1.0）。
    - DuckDB の executemany 空リスト制約を考慮した安全な DELETE/INSERT ロジック（部分失敗時に既存スコアを保護）。
    - テスト用に _call_openai_api を patch 可能にしている（ユニットテストで差し替え可）。
  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM（gpt-4o-mini）センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定（score_regime）。
    - prices_daily / raw_news を参照して ma200_ratio を計算、マクロ記事抽出、LLM 呼び出し、スコア合成。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ、同様にリトライ・バックオフ実装。
    - レジーム結果は market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - news_nlp とモジュール結合しない設計（_call_openai_api は別実装で独立）。

- 互換性・実装上の配慮
  - DuckDB からの日付取り扱いや executemany の制約、NULL 値の扱いなどを考慮した実装（_to_date, 空 execuemany チェック等）。
  - ルックアヘッドバイアス回避のため、いずれの処理も datetime.today()/date.today() を直接参照しない設計（外部から target_date を受け取る方式）。
  - ロギングを各モジュールに導入し、警告・情報ログで異常や意思決定の根拠を出力。

### Changed
- 初版のためなし（今後のリリースで追記予定）。

### Fixed
- 初版のためなし（今後のリリースで追記予定）。

### Notes / Implementation details
- OpenAI の利用は gpt-4o-mini を想定し、JSON mode（response_format={"type": "json_object"}）を利用する設計になっています。
- LLM 呼び出しはリトライや 5xx 判定を考慮しており、API の一時障害が発生しても処理全体が破綻しないようフェイルセーフにしています（多くの場合はスコアを 0.0 として扱い継続）。
- DB 書き込みは可能な限り冪等に設計（DELETE → INSERT、トランザクション管理、エラー時の ROLLBACK の試行とログ出力）。
- news_nlp と regime_detector は共に _call_openai_api を内部実装として持ち、モジュール間でプライベート関数を共有しない方針を採っています（結合度低減のため）。

---

今後の予定（例）
- テストカバレッジ拡充、外部 API クライアントの抽象化、より詳細な品質チェックルールの追加、パフォーマンス計測・最適化。