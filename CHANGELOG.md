# KEEP A CHANGELOG

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

全般的な方針:
- リリースはセマンティックバージョニングに従います。
- 各項目では追加された機能、変更点、修正点、破壊的変更（ある場合）を簡潔に説明します。

## [Unreleased]

(次回リリースに向けた変更をここに記載してください)

## [0.1.0] - 2026-04-01

初期公開リリース。以下の主要機能・モジュールを実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。公開 API: data, research, ai, 等を __all__ に設定。
  - バージョン: 0.1.0

- 環境設定 / ロード
  - 環境変数読み込みユーティリティを追加（kabusys.config）。
    - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env / .env.local 自動ロード（優先順位: OS 環境変数 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - .env パーサは以下をサポート/考慮:
      - コメント行、export KEY=val 形式、
      - シングル/ダブルクォート内のバックスラッシュエスケープ、
      - クォートなし行でのインラインコメント（直前が空白/タブの場合のみ）。
    - 上書き挙動: override と protected（OS 環境変数保護）を扱う。
  - Settings クラスを提供（kabusys.config.settings）。
    - J-Quants / kabu ステーション / Slack / DB パス / 監視阈値 / 環境・ログレベル等のプロパティを提供。
    - 必須環境変数未設定時に明瞭な ValueError を送出。
    - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値の検査）。
    - パスプロパティは Path 型で返却。

- AI モジュール (kabusys.ai)
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols から対象期間のニュースを銘柄単位に集約し、OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してスコアを算出。
    - バッチサイズ、記事数/文字数トリム、タイムウィンドウ（JST ベース → UTC 変換）などの制約を実装。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ。非リトライ対象のエラーはスキップ（フェイルセーフ）。
    - レスポンスの堅牢なバリデーションを実装（JSON 抽出、results キー、型検査、未知コード無視、数値変換、有限値チェック）。
    - スコアは ±1.0 にクリップ。取得したスコアを ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - API キー注入対応（api_key 引数または OPENAI_API_KEY 環境変数）。
    - テスト容易性: _call_openai_api の差し替え/モックを想定。
    - 関数: calc_news_window, score_news, 内部の _fetch_articles / _score_chunk / _validate_and_extract 等。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - prices_daily から MA200 乖離を算出（ルックアヘッド回避のため target_date 未満のみを参照、データ不足時は中立扱い）。
    - raw_news からマクロキーワードでタイトルを抽出して LLM に送信し macro_sentiment を取得。
    - OpenAI 呼出は専用実装（news_nlp と直接の内部関数共有を避ける）。
    - API 障害時は macro_sentiment を 0.0 にフォールバックして継続。結果は market_regime テーブルへ冪等書き込み。
    - 関数: score_regime と内部ユーティリティ。

- データプラットフォーム / ETL（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを保存する market_calendar テーブルを前提とした営業日判定ロジックを実装。
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
      - DB 登録値優先、未登録日は曜日ベース（土日非営業）でフォールバック。一貫性を保つ実装。
      - 最大探索日数制限、健全性チェック（将来日付の異常検出）などを実装。
    - calendar_update_job により J-Quants API からの差分取得 → 保存（バックフィル・健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを追加（取得/保存件数、品質問題、エラーの集約）。
    - 差分取得、idempotent 保存（jquants_client の save_* の利用）、品質チェック（quality モジュール）を想定した設計。
    - ETL の要件・設計方針（バックフィル、部分失敗時のデータ保護、テスト容易性）を実装に反映。
  - ETLResult を再エクスポートするエイリアス（kabusys.data.etl）。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（必要データ未満は None を返す）。
    - Volatility & Liquidity: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - Value: 最新の raw_financials と当日の株価から PER / ROE を算出（EPS が 0 の場合は PER を None に）。
    - DuckDB 上で SQL ウィンドウ関数を用いて効率的に集計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns（任意ホライズンに対応、境界検査あり）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンランク相関、必要サンプル数チェック）。
    - ランク変換ユーティリティ: rank（同順位は平均ランク、丸めで ties を安定化）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を返す）。
  - research パッケージの public API を __all__ で整備。

### 仕様上の設計判断・フェイルセーフ
- ルックアヘッドバイアス回避:
  - 各種処理（news, regime, factors 等）で datetime.today() / date.today() の直接参照を避け、target_date を引数で与える設計。
- OpenAI 呼び出しの堅牢化:
  - 429・ネットワーク・タイムアウト・5xx をリトライ、その他はスキップしてフェイルセーフ化。
  - レスポンスパース失敗はログを残して 0.0（中立）やスキップで継続。
- データベース書き込み:
  - DuckDB に対する書き込みは冪等性を考慮（DELETE → INSERT / ON CONFLICT を想定）し、トランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - DuckDB の executemany の制約（空リスト不可）に配慮した実装。
- テスト容易性:
  - OpenAI 呼び出し関数の差し替えを想定（ユニットテストでのモック化が容易）。

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 該当なし（初回リリース）

### 破壊的変更 (Removed / Deprecated)
- 該当なし（初回リリース）

---

今後の予定（例）
- モジュールのユニットテスト追加・CI 統合
- jquants_client / kabu API クライアント実装の追加・統合テスト
- モニタリング・実行系（execution, monitoring）モジュールの公開 API 実装とドキュメント整備

もし CHANGELOG に追加したい詳細（例: もっと細かい関数単位の説明や既知の問題）があれば教えてください。