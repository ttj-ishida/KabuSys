# Changelog

すべての重要な変更をこのファイルで管理します。フォーマットは Keep a Changelog に準拠しており、セマンティックバージョニングに従います。

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加内容を以下に示します。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - モジュール公開: data, strategy, execution, monitoring。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local を自動的にプロジェクトルートからロードする仕組みを導入（.git または pyproject.toml をプロジェクトルート判定に使用）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサーを実装（コメント処理・export プレフィックス対応・クォート内のエスケープ処理を考慮）。
  - OS 環境変数を保護する protected 機構（.env.local が OS 環境変数を上書きしないように制御可能）。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境種別・ログレベル検証などのプロパティを含む）。
  - 必須環境変数未設定時は明示的に ValueError を送出する設計。

- データ基盤（kabusys.data）
  - calendar_management: JPX マーケットカレンダー管理と営業日判定ユーティリティ
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar テーブルが未取得の場合は曜日ベースのフォールバック（週末を休場）を行う。
    - calendar_update_job により J-Quants から差分取得して冪等的に保存（バックフィル・健全性チェック含む）。
  - pipeline / etl:
    - ETLResult データクラスを実装して ETL 実行結果・品質問題・エラーを集約。
    - ETL の差分取得・保存・品質チェックの方針を明記（backfill, idempotent 保存等）。
    - ETLResult を外部に公開するための再エクスポート（kabusys.data.etl）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を元にニュース記事を銘柄単位で集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ（JST: 前日15:00～当日08:30 を UTC に変換）を正確に計算。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの最大記事数/文字数トリム、スコア ±1.0 クリップを実装。
    - JSON Mode を利用した厳密なレスポンス検証（復元ロジック含む）と堅牢なバリデーション実装。
    - RateLimit / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライを実装。失敗時は該当チャンクをスキップして継続するフェイルセーフ。
    - テスト容易性のため OpenAI 呼び出しポイントを差し替え可能（_call_openai_api を patch 可能）。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みを行う機能を実装。
    - マクロキーワードによる raw_news フィルタ、LLM 呼出し（gpt-4o-mini）、JSON パース、リトライ/フェイルセーフ処理を実装。
    - API キー注入（引数 or 環境変数 OPENAI_API_KEY）方式を採用。
    - API 失敗時は macro_sentiment = 0.0 にフォールバックする設計（例外を投げず処理継続）。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR，atr_pct，20日平均売買代金，出来高比率を計算。部分窓の扱い等を考慮。
    - calc_value: raw_financials から最終財務を取得して PER / ROE を計算（EPS 0 や欠損は None）。
    - DuckDB を使った SQL + Python の実装で外部ネットワーク呼び出しなし。
  - feature_exploration:
    - calc_forward_returns: 任意のホライズンに対する将来リターン計算（デフォルト [1,5,21]）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - rank: 同順位の平均ランク付け（丸め処理で ties の誤検出を防止）。
    - 外部ライブラリ依存を避け、標準ライブラリと DuckDB のみで実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- トランザクション処理の堅牢化
  - news_nlp / regime_detector / pipeline の DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の形で冪等に行い、例外発生時は ROLLBACK を試行。ROLLBACK に失敗した場合は警告ログを出力して上位へ例外を伝播する実装。

- API エラー時のフェイルセーフ挙動
  - OpenAI / ネットワーク系 API 呼び出しでの失敗に対し、致命的な例外を上位へ直接伝播させず、影響範囲を限定して処理を継続する設計（スコアを取得できなかった場合はスキップまたは 0.0 フォールバック）。

### Security
- 環境変数の扱いに注意
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を Settings が要求。未設定時は明示的なエラーを発生させるため、運用時には環境変数管理に注意が必要。

### Design notes / その他重要事項
- ルックアヘッドバイアス防止
  - AI モジュール・リサーチ関数は内部で datetime.today() / date.today() を直接参照せず、外部から target_date を注入する設計。DB クエリも target_date 未満/以前のデータのみを使用することで将来情報の漏洩を防止している。
- テスト容易性
  - OpenAI 呼び出し部分はモック差し替え可能にしており、ユニットテストで外部 API を置き換えられる。
- 依存
  - DuckDB をデータ処理の主要エンジンとして使用。
  - OpenAI Python SDK を Chat Completions(JSON mode) で利用する想定（gpt-4o-mini をデフォルトモデルとして設定）。

---

今後のリリース予定（例）
- strategy / execution / monitoring の具体的な売買ロジックおよび発注 API の実装（kabu ステーション連携含む）。
- 追加の品質チェックルールと監視アラート機能。
- テストカバレッジ強化と CI/CD 用のモック・フィクスチャ整備。