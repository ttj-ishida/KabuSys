# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

現在の日付: 2026-03-28

## [Unreleased]
（現在の開発中の変更はここに記載します）

## [0.1.0] - 2026-03-28
初期公開リリース

### Added
- パッケージ全体の初期実装を追加。
  - kabusys パッケージ内のモジュール群を公開（data, research, ai, config など）。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード機能（プロジェクトルートの検出は .git または pyproject.toml を参照）。
  - .env パーサー実装：コメント、export 形式、シングル/ダブルクォート、バックスラッシュエスケープに対応。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須環境変数取得ヘルパー `_require()`、各種設定プロパティ（OpenAI / kabu / Slack / DB パス / 環境判定 / ログレベル等）。
- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news + news_symbols から銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ保存する処理を実装。
    - バッチ処理、チャンク化（最大20銘柄/チャンク）、文字数・記事数トリム、JSON_Mode レスポンスの検証を実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、失敗時はフェイルセーフでスキップ。
    - テスト容易性のため OpenAI 呼び出し関数を patch 可能に設計。
  - regime_detector.score_regime
    - ETF(1321) の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定、market_regime テーブルに冪等的に書き込む。
    - DuckDB クエリでのルックアヘッドバイアス回避（target_date 未満のデータのみ使用）や API 失敗時のフォールバック（macro_sentiment=0.0）を実装。
- Data モジュール（kabusys.data）
  - calendar_management
    - market_calendar を利用した営業日判定・前後営業日取得・期間内営業日取得・SQ判定ロジックを実装。
    - J-Quants からの差分取得を行う夜間バッチ calendar_update_job を実装（バックフィル、健全性チェック、冪等保存を考慮）。
    - DB が未取得の場合の曜日ベースフォールバックを実装（堅牢性を重視）。
  - pipeline / ETL
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー等を集約）。
    - 差分取得、backfill、品質チェック（quality モジュール利用）を想定した設計。
  - etl モジュールは pipeline.ETLResult を再エクスポート。
- Research モジュール（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER・ROE）等のファクター計算関数を実装（DuckDB クエリベース）。
    - データ不足時の None 返却など堅牢な処理を提供。
  - feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン）、IC（calc_ic）計算、ランク変換 rank、統計サマリ factor_summary を実装。
    - pandas 等に依存しない純粋 Python / SQL 実装。
- 共通設計上の注意点を注記
  - ルックアヘッドバイアス回避のため各所で datetime.today()/date.today() を直接参照しない設計。
  - DuckDB を主要なローカル分析 DB として採用。
  - OpenAI 呼び出しは外部 API へ依存するためフェイルセーフ（失敗時はスコア0やスキップ）を重視。
  - テストしやすいように内部 API 呼び出しポイント（_call_openai_api 等）を patch 可能にしている。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- 環境変数の取り扱いに注意：
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY 等の機密情報を環境変数で利用。運用時は .env をソース管理に含めないこと。
  - .env の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能（テスト用途）。

### Notes / Migration
- 必須 DB スキーマ（以下のテーブルが必要）:
  - prices_daily, raw_news, market_regime, ai_scores, news_symbols, raw_financials, market_calendar など（各モジュールが参照）。
- OpenAI を利用する機能（news_nlp, regime_detector）は環境変数 OPENAI_API_KEY または関数引数で API キーを渡す必要がある。
- kabu API や Slack 連携機能のための環境変数は未設定時に ValueError を発生させる実装があるため、運用時に適切に設定してください。
- DuckDB の executemany に関する互換性注記（空リストは不可）を考慮した実装になっているため、DuckDB のバージョン依存で挙動が変わる可能性あり。

---

今後のリリース案内例:
- 0.2.0: 発注実行（execution）モジュールの実装、Slack 通知機能の統合、テストカバレッジの強化。
- 0.1.x: バグ修正、OpenAI モデルやリトライのチューニング、クエリ最適化等。

（必要に応じてこの CHANGELOG を更新してください）