# Changelog

すべての重要な変更点をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

※ 本 CHANGELOG は与えられたコードベース（バージョン情報: 0.1.0）から実装内容を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース

### Added
- パッケージ初期化
  - パッケージ名: kabusys、バージョン: 0.1.0 を定義（src/kabusys/__init__.py）。
  - __all__ に主要サブパッケージを公開: data, strategy, execution, monitoring。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能を実装。優先順位は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .git または pyproject.toml を基準にプロジェクトルートを探索して自動ロードを実行（CWD に依存しない）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォートのエスケープ処理に対応。
    - インラインコメント処理（クォートあり/なしそれぞれの挙動を適切に扱う）。
  - 環境変数取得ユーティリティ _require と Settings クラスを提供。
  - Settings で J-Quants、kabuステーション、Slack、データベースパス（duckdb/sqlite）、実行環境（development/paper_trading/live）、ログレベルなどを取得・検証するプロパティを実装。
  - 不正な KABUSYS_ENV / LOG_LEVEL の値を検出して ValueError を送出。

- AI 関連（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを生成。
    - ニュース対象ウィンドウ（JST 基準: 前日 15:00 ～ 当日 08:30）を計算する calc_news_window を実装（UTC naive datetime を返す）。
    - バッチ処理（1回最大 20 銘柄）、各銘柄の記事トリム（記事数上限、文字数上限）などの肥大化対策を実装。
    - API エラー（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフ付きリトライを実装。その他エラーはスキップしてフェイルセーフに処理継続。
    - レスポンス検証: JSON パース、"results" 配列、コード一致、スコア数値のチェック、スコアの ±1.0 クリップ。
    - DuckDB への書き込みは冪等的に行う（対象コードのみ DELETE → INSERT）。DuckDB executemany の空リスト制約を考慮。
    - 外部呼び出しは _call_openai_api でラップし、テスト時の差し替えを想定。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出のためのキーワードリストを実装（日本語・英語混在）。
    - OpenAI 呼び出しについては独立した _call_openai_api を使用（news_nlp とは共有しない設計）。
    - API 失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフを実装。
    - レジームスコアのクリップ、閾値に基づくラベル決定を実装。
    - DuckDB への保存はトランザクションを用いて冪等（BEGIN / DELETE / INSERT / COMMIT）で実施。失敗時は ROLLBACK。

- Data モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し、market_calendar テーブルへ冪等保存。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーデータがない/不足する場合は曜日ベース（週末除外）でフォールバックする堅牢な設計。
    - 最大探索日数やバックフィル、健全性チェック（未来日付の異常検出）を実装。

  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（src/kabusys/data/etl.py で再エクスポート）。
    - 差分更新、バックフィル、品質チェック統合を行う ETL パイプラインの基盤を実装（保存は jquants_client 経由で冪等保存）。
    - テーブル最大日付取得などのユーティリティを実装。
    - 品質チェック（quality モジュールとの連携）で得られた結果を ETLResult に集約。致命的なエラーや品質エラーの判定プロパティを提供。

- Research モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算する calc_momentum を実装。データ不足時の None 管理。
    - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算する calc_volatility を実装。true_range 計算で NULL 伝播を厳密に管理。
    - Value: PER, ROE を raw_financials と prices_daily から取得する calc_value を実装。最新の財務レコードを target_date 以前から取得。
    - DuckDB SQL を主体とした実装で、本番口座や外部 API へ影響を与えない設計。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 任意ホライズンに対する将来終値リターンを一度のクエリで計算。horizons の入力バリデーションあり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関をランク関数を使って実装。データ不足時は None を返す。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランクで扱う。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算する実装（None 値を除外）。

- その他
  - 複数のモジュールで OpenAI クライアント呼び出しを _call_openai_api で抽象化し、テスト用に差し替え可能（unittest.mock.patch を想定）。
  - DuckDB を前提とした SQL 実装と、空の executemany 対策など DuckDB 互換性に配慮した実装が反映。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーは関数引数で注入可能。環境変数 OPENAI_API_KEY の未設定時は明示的にエラーを出す設計（誤使用を早期検出）。

---

設計上の注記（実装上の重要な振る舞い・制約）
- すべての日付関連処理は明示的に date / datetime オブジェクトで扱う（timezone 混入防止）。
- ルックアヘッドバイアス防止のために datetime.today()/date.today() の直接参照を避け、関数引数で target_date を受け取る設計を採用している箇所が多い（AI スコア算出・ファクター計算等）。
- OpenAI 呼び出しは冪等性の確保やテスト容易化の観点からラップされている。テストでは内部の _call_openai_api をパッチして挙動を制御できる。
- DuckDB 固有の制約（executemany の空リスト不可など）を考慮した実装が随所に見られる。

もし CHANGELOG に追記してほしい点（例えばリリース日を別の日付にする、Unreleased セクションに追加する、個別の修正履歴をより詳細に書く等）があれば指示してください。