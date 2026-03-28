# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

- 未リリースの変更は "Unreleased" に記載します。
- 初回公開リリースは 0.1.0 です。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報と公開 API を追加（kabusys.__version__ = 0.1.0）。
  - パッケージのトップレベル __all__ に data, strategy, execution, monitoring を定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ 起点で .git または pyproject.toml を探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（コメント/export/クォート/エスケープ対応）。
  - Settings クラスを提供（settings オブジェクトを介してアクセス可能）。
    - J-Quants / kabu API / Slack / DB パス / 実行環境 (development/paper_trading/live) / ログレベルなどのプロパティ。
    - 必須環境変数未設定時は ValueError を送出する保護機能。
    - env, log_level の入力検証を実装。

- データプラットフォーム関連 (kabusys.data)
  - ETL パイプラインインターフェースを追加（ETLResult を公開）。
  - calendar_management モジュールを追加
    - JPX マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等）。
    - market_calendar が未取得の時は曜日ベースのフォールバックを行う堅牢な設計。
    - calendar_update_job で J-Quants から差分取得し冪等保存（バックフィル・健全性チェックを実装）。
  - pipeline / etl の基盤コード
    - ETLResult データクラス（実行結果、品質検査結果、エラー集計など）。
    - DB テーブル存在チェックや最大日付取得などのユーティリティ。

- AI / ニュース解析 (kabusys.ai)
  - news_nlp モジュールを追加（score_news）
    - raw_news / news_symbols から記事を集約し、OpenAI (gpt-4o-mini) を使って銘柄別センチメントを算出。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを実装（calc_news_window）。
    - 1銘柄あたり記事上限・文字数上限、バッチ処理 (_BATCH_SIZE) といったトークン肥大化対策を実装。
    - JSON Mode を利用したレスポンス検証と堅牢なパース処理（不正レスポンスの回復処理含む）。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - ai_scores テーブルへ取得済み銘柄のみを置換（DELETE → INSERT）し部分失敗時の保護を実現。
  - regime_detector モジュールを追加（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来マクロセンチメント（重み 30%）を合成して market_regime を日次判定。
    - マクロニュースは news_nlp の窓計算を利用し、OpenAI を呼び出して JSON を受け取る。
    - API エラー時は macro_sentiment=0.0 のフェイルセーフ挙動を採用。
    - DuckDB を用いた冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - ai パッケージは score_news, score_regime の公開 API を提供。

- リサーチ / ファクター計算 (kabusys.research)
  - factor_research モジュールを追加
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Value（PER/ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）等を DuckDB 上で計算する関数を実装（calc_momentum, calc_value, calc_volatility）。
    - データ不足時の None 処理やスキャン範囲バッファを考慮した設計。
  - feature_exploration モジュールを追加
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純 Python 実装。
  - research パッケージは主要関数を再エクスポート（zscore_normalize を含む）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数（OPENAI_API_KEY）から取得する設計。キー管理は呼び出し側で行うこと。

### 注記 / 実装上の重要点
- 全モジュール共通の設計方針:
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない（関数に target_date を渡す設計）。
  - API 呼び出しはフェイルセーフ（致命的エラーを避け、部分的にスキップして継続する方針）。
  - DuckDB を主要な計算・一時格納先として使用。書き込みは可能な限り冪等（置換）に設計。
  - ロギングと警告を多用し、異常時の情報を残す実装。

このリリースはプロジェクトの初期基盤を提供します。今後のリリースではテストカバレッジの拡充、パフォーマンス最適化、監視/運用周り（monitoring）や戦略実行部の実装強化を予定しています。