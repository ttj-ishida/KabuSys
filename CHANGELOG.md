# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買 / データ基盤 / 研究用ユーティリティの基本機能を実装しました。

### 追加（Added）
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開 API に data, strategy, execution, monitoring を想定したエクスポートを追加。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード実装。
    - プロジェクトルートの検出ロジック（.git または pyproject.toml を探索）により CWD 非依存で自動ロード。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - 自動ロード無効化: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサの実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理等に対応）。
  - protected set を用いた既存 OS 環境変数の保護（.env.local の上書き制御）。
  - Settings クラスを公開（settings）
    - J-Quants, kabuステーション, Slack, データベースパス等のプロパティを提供。
    - 必須環境変数取得時の明示的エラー (_require)。
    - env / log_level のバリデーション（許容値チェック）。
    - duckdb/sqlite のパスは Path 型で返却。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大20銘柄/チャンク）、記事数/文字数のトリム、JSON Mode 応答パース、レスポンス検証を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ。失敗はログ記録してスキップ（フェイルセーフ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、トランザクション管理）。部分失敗時に既存スコアを保護する実装。
    - calc_news_window ユーティリティ（JST ベースのニュース収集ウィンドウ）。
  - regime_detector.score_regime
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - prices_daily / raw_news を参照し、OpenAI（gpt-4o-mini）呼び出しは独立実装。API失敗時は macro_sentiment=0.0 として継続（ロバスト設計）。
    - レジームスコアのクリップ、閾値判定、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK の扱い）。

- データ処理 / カレンダー（kabusys.data）
  - calendar_management
    - market_calendar を利用した営業日判定ロジックを実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar 未取得時は曜日ベース（週末除外）のフォールバックを行い、DB に登録済みの日付は優先する一貫性設計。
    - calendar_update_job: J-Quants API からの差分取得→保存（fetch/save 経路を jquants_client に委譲）、バックフィル（過去数日再取得）や健全性チェックを実装。
  - pipeline / ETL
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
      - 取得数・保存数・品質問題・エラー概要などを集約し has_errors / has_quality_errors / to_dict を提供。
    - ETL パイプライン用ユーティリティ（テーブル存在確認、最大日付取得、トレーディング日調整等）を実装。
    - 差分更新・バックフィル・品質チェックの方針を実装（API 側の後出し修正吸収等）。

- 研究（kabusys.research）
  - factor_research
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）、ボラティリティ（atr_20, atr_pct, avg_turnover, volume_ratio）、バリュー（per, roe）を DuckDB の prices_daily / raw_financials から算出する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 欠損やデータ不足時の扱い（None 戻り）やスキャン範囲のバッファ設計を実装。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク関数（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリで実装。ランクは同順位を平均ランクで処理。

- エクスポート
  - 各モジュールの主要関数・ユーティリティを __all__ で整備（例: kabusys.ai.score_news, kabusys.research.* など）。

### 変更（Changed）
- 初回リリースにより、設計方針やログ出力を各モジュールにドキュメントとして埋め込み。実装は運用/テストを想定したフェイルセーフ優先の設計。

### 修正（Fixed）
- N/A（初版のため特定のバグ修正履歴はありません）。

### セキュリティ（Security）
- OpenAI API キー未設定時に明確な ValueError を送出することで誤起動を防止。
- 環境変数保護（protected set）による OS 環境変数の不意な上書きを防止。

### 備考 / 実装上の注意
- すべての「日付」は date/datetime オブジェクトで扱い、timezone 混入を避ける設計（ニュースウィンドウは UTC naive datetime を使用）。
- LLM 呼び出し部分はテスト容易性のため _call_openai_api を patch して差し替え可能。
- DuckDB に対する executemany の空リスト扱い等の実装上の互換性考慮が入っています（DuckDB 0.10 互換性）。
- トランザクション管理（BEGIN/COMMIT/ROLLBACK）を用いて DB 一貫性を確保。ROLLBACK の失敗は警告ログで報告。
- 外部 API 呼び出し失敗は基本的に例外上げずにフェイルセーフで継続する（ログ記録）。上位での取り扱いを想定。

---

開発・運用中の改善点・既知の拡張候補は ISSUE に記録してください。