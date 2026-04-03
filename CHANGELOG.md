# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従います。  

## [Unreleased]

- 現在のところ未リリースの作業はありません。

## [0.1.0] - 2026-04-03

初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring をエクスポート。
  - バージョン番号を "0.1.0" に設定。

- 設定管理（kabusys.config）
  - .env/.env.local ファイルと環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml で検出）。
  - .env パーサーは export 構文・クォート・エスケープ・行コメント等をハンドル。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / システム挙動（env, log_level, is_live 等）をプロパティ経由で取得。必須値は未設定時に ValueError を送出。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄別センチメント ai_score を計算。
    - 時間ウィンドウ（前日15:00 JST ～ 当日08:30 JST）に対応する calc_news_window 関数を実装。
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数トリム、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーション、スコアのクリップ、部分成功時に既存データを保護する idempotent な DB 操作（DELETE → INSERT）をサポート。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニューズの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出し market_regime テーブルへ冪等書込。
    - prices_daily, raw_news を参照し、OpenAI 呼び出しは専用の内部実装を使用（モジュール結合を抑制）。
    - API エラーやパース失敗時のフェイルセーフ（macro_sentiment=0.0）やリトライロジックを実装。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB データが不足する場合の曜日ベースのフォールバック、探索上限での例外制御、JPX カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装。
  - ETL / パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを提供（取得数／保存数／品質問題／エラー等の集約）。
    - 差分取得、バックフィル、品質チェック（kabusys.data.quality）を想定した ETL の基本設計を実装。
    - kabusys.data.etl モジュールで ETLResult を再エクスポート。

- リサーチ / ファクター（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン）、200 日移動平均乖離、ATR ベースのボラティリティ、20 日平均売買代金／出来高比率などを計算する関数（calc_momentum / calc_volatility / calc_value）を実装。
    - DuckDB の SQL を用いた効率的なウィンドウ集計、欠損時の None 処理、結果を (date, code) ベースの dict リストで返す設計。
  - 特徴量解析ユーティリティ（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman ランク相関）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換（rank）を実装。
    - pandas 等外部依存を持たない純粋 Python 実装。

- その他
  - DuckDB を主要なデータストアとして利用する前提で SQL / 接続型 API を整備。
  - ロギングと詳細な警告メッセージを各所に追加し、フェイルセーフ動作（API失敗時の継続/スキップ）を優先した設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

注記:
- OpenAI（gpt-4o-mini）や J-Quants などの外部 API キーは環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）で供給する設計です。サンプル .env ファイル（.env.example）を参照してください。