# Changelog

すべての重要な変更履歴をここに記載します。本ファイルは Keep a Changelog のフォーマットに準拠しています。

最新の変更は常にトップに記載します。

## [Unreleased]

## [0.1.0] - 2026-03-31

初回リリース — 日本株自動売買プラットフォームのコア機能群を実装。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0）。公開モジュール: data, strategy, execution, monitoring。
- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local 自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの強化:
    - export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ対応。
    - 行末コメント（#）の適切な処理。
  - .env 読み込み時の保護機能: OS 環境変数を protected キーとして上書き防止。
  - Settings クラスでアプリ設定をプロパティとして提供（J-Quants、kabuステーション、Slack、DBパス、環境モード、ログレベル等）。
  - 必須環境変数不足時に明示的な ValueError を送出。
  - env/log_level 値のバリデーション（許容値チェック）。
- AI（自然言語処理）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ保存。
    - バッチ処理（最大 20 銘柄／API コール）、1 銘柄当たりの記事数・文字数トリム（上限設定）。
    - API 呼び出しでのリトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスの厳格バリデーション（JSON 抽出、results 配列、code/score 検証）とスコアクリップ（±1.0）。
    - テスト容易性のため _call_openai_api をモック可能。
    - 日次ウィンドウ計算ユーティリティ calc_news_window を実装（JST→UTC 変換を考慮）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定・保存。
    - 設計上ルックアヘッドバイアスを排除（target_date 未満のデータのみ参照）。
    - OpenAI 呼び出しは独立実装、API 失敗時は macro_sentiment=0.0 でフェイルセーフ処理。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の安全ハンドリング。
- Data / ETL / カレンダー（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない場合は曜日ベースでフォールバック（週末除外）。
    - 夜間バッチ更新 job（calendar_update_job）で J-Quants から差分取得・保存（バックフィル・健全性チェックを含む）。
    - 最大探索日数制限で無限ループ回避。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラーを保持）。
    - 差分更新、バックフィル、品質チェック運用方針に基づく設計（DataPlatform.md 準拠）。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。
  - data.etl は pipeline.ETLResult を再エクスポート。
- Research（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等の計算。
    - calc_value: raw_financials を用いた PER, ROE の算出（target_date 以前の最新財務データを使用）。
    - DuckDB SQL とウィンドウ関数を活用した実装。データ不足時は None を返す挙動。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 将来リターン（任意ホライズン）を一度のクエリで計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（結合、None 除外、3 件未満は None）。
    - rank / factor_summary: ランク付け（同順位平均ランク）・統計サマリー（count/mean/std/min/max/median）を実装。
  - 研究用ユーティリティの公開（zscore_normalize の re-export 等）。
- 互換性・実装ノート
  - DuckDB 0.10 の制約（executemany に空リスト不可）を考慮した実装（空チェックを行ってから executemany）。
  - 多くの箇所で datetime.today()/date.today() の直接参照を避け、target_date ベースで処理してルックアヘッドバイアスを防止。
  - 各所でロギング（info/debug/warning）を豊富に追加。

### Changed
- 初版リリースのため過去変更なし（新規実装）。

### Fixed
- 初版リリースのため過去修正なし。

### Notes / Limitations
- OpenAI に依存する機能は API キー（引数 or 環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError を発生させる設計。
- API 呼び出し失敗時は多くの処理でフェイルセーフ（ゼロスコア、スキップ）を採用して全体処理継続を優先。
- 一部の関数は DuckDB のスキーマ（prices_daily / raw_news / market_calendar / raw_financials / news_symbols / ai_scores / market_regime 等）を前提としている。データスキーマが異なる場合は動作しない可能性がある。
- README / ドキュメント（使用例・スキーマ定義・ジョブ実行手順）は別途整備が必要。

---

（CHANGELOG は今後のリリースで Unreleased → バージョン化して更新してください。）