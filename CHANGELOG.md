# CHANGELOG

すべての重要な変更点を Keep a Changelog 準拠の形式で記載します。

フォーマット:
- 変更はセマンティックバージョニングに従います。
- 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しています。主な追加点は以下のとおりです。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py によりパッケージ名・バージョン（0.1.0）と主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定・自動ロード機能
  - src/kabusys/config.py を追加。
  - .env および .env.local の自動読み込み機能（プロジェクトルートの検出: .git / pyproject.toml ベース）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
  - export プレフィックス対応、クォート・エスケープ処理、行内コメント処理などを考慮した堅牢な .env パーサを実装。
  - OS 環境変数を保護する protected 機構と override 挙動を実装。
  - Settings クラスを導入し、J-Quants / kabuAPI / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベル 等をプロパティ経由で取得。必須環境変数未設定時は ValueError を送出。

- AI モジュール（ニュースNLP・市場レジーム）
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news / news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出し ai_scores テーブルへ書き込み。
    - チャンク処理（最大20銘柄）、1銘柄あたりの記事数・文字数制限、JSON Mode のレスポンス検証、スコアの ±1.0 クリップ、部分失敗時の部分書換保護（DELETE → INSERT）などを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - テスト容易性のため OpenAI 呼び出し関数を patch 可能に（_kabusys.ai.news_nlp._call_openai_api）。
    - calc_news_window(target_date) により JST 時間ウィンドウを UTC naive datetime で計算。

  - src/kabusys/ai/regime_detector.py を追加。
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースセンチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - マクロ記事フィルタリング、OpenAI（gpt-4o-mini）呼出し、リトライ・フォールバック（API失敗時は macro_sentiment=0.0）、結果の冪等的な market_regime テーブル書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - ルックアヘッドバイアス対策（datetime.today()/date.today() を直接参照せず、target_date 基準でクエリを行う設計）。

- データプラットフォーム機能
  - src/kabusys/data/calendar_management.py を追加。
    - market_calendar を用いた営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数制限、JPX カレンダー差分取得用の calendar_update_job（J-Quants クライアント呼出し）を実装。
    - 健全性チェック（将来日付異常やバックフィル）や冪等保存方針を実装。

  - src/kabusys/data/pipeline.py を追加。
    - ETL パイプラインの骨格を実装。差分取得、保存（idempotent）、品質チェック（品質問題は収集して呼び出し元へ報告する方針）を想定。
    - ETL 実行結果を表す dataclass ETLResult を実装（to_dict で品質問題をシリアライズ）。
    - DuckDB のテーブル存在確認や最大日付取得などのユーティリティを提供。
    - backfill や calendar lookahead 等のデフォルトポリシーを定義。

  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

  - jquants_client（外部モジュール想定）との連携を前提にした設計（fetch/save 関数を利用）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py を追加。
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等の定量ファクター計算関数（calc_momentum, calc_volatility, calc_value）を実装。
    - DuckDB SQL を多用し、prices_daily / raw_financials のみ参照する自己完結設計。結果は dict のリストで返却。
    - データ不足時の挙動（None を返す）やスキャンバッファ（カレンダー日換算）を明記。

  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等外部依存を避けた実装。欠損や非有限値のフィルタリング、horizons の入力検証を実装。

  - src/kabusys/research/__init__.py で主要関数を再エクスポート。

- その他ユーティリティ
  - OpenAI SDK 呼出しラッパー関数を各モジュールで分離（テスト時差し替え容易）。
  - 多くの関数で「ルックアヘッドバイアスを防ぐ」設計方針を明記・適用。
  - DuckDB 互換性に配慮した executemany 空リスト回避ロジックや型変換ユーティリティ（_to_date）を実装。
  - ロギングでの詳細な情報出力（info/debug/warning/exception）を整備。

### Changed
- 初回リリースにつき変更履歴はありません（開発版からの差分を初回として公開）。

### Fixed
- 初回リリースにつき修正履歴はありません。

### Deprecated
- なし。

### Removed
- なし。

### Security
- なし（ただし OpenAI/外部APIキーの取り扱いは Settings を通じて必須化）。

## 重要な設計メモ / 注意事項
- OpenAI API キーは各関数の api_key 引数から注入可能。空文字列や未設定時は ValueError を送出して処理を中断します（明示的設定を要求）。
- OpenAI 呼び出しは gpt-4o-mini と JSON mode を使用する想定。レスポンスパース失敗や API エラーはフェイルセーフ（多くの場合 0.0 やスキップ）で継続する設計。
- DuckDB をデータレイヤに使用。SQL は DuckDB の機能を前提とする（ウィンドウ関数、ROW_NUMBER、LEAD/LAG 等）。
- ETL / カレンダー更新等は外部 J-Quants クライアント（jquants_client）に依存。外部 API 呼出しに伴う例外は呼び出し元でハンドル可能に設計。
- .env 自動ロードはプロジェクトルートの検出に基づくため、パッケージ配布後の動作やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って制御可能。

## 互換性に関する注記
- 本リリースは初版のため後方互換性の観点は当面は考慮済み（今後の API 変更はメジャーバージョン上げで通知予定）。

---

ご希望であれば、リリースノートの英語版・要約版の作成、または各モジュールごとの詳細な使用例（コードサンプル）も作成します。どの形式をご希望ですか？