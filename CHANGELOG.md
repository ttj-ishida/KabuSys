# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠します。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]


## [0.1.0] - 2026-03-27
初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。
  - バージョン: 0.1.0。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを提供。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの取り扱いなどを考慮して安全にパース。
  - Settings クラスを公開（settings オブジェクト）。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供。
    - KABUSYS_ENV, LOG_LEVEL の検証（許容値チェック）。
    - duckdb/sqlite のデフォルトパスを Path オブジェクトで返すユーティリティ。

- AI モジュール（src/kabusys/ai/）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを算出。
    - バッチ処理（最大 20 銘柄/コール）、トークン肥大化対策（記事数・文字数上限）を実装。
    - JSON Mode を用いた厳密なレスポンス検証と数値クリップ（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ。
    - ai_scores テーブルへ冪等的に書き込み（取得済みコードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily/raw_news を参照、計算はルックアヘッドバイアスを防ぐ実装（target_date 未満のデータのみ使用）。
    - OpenAI 呼び出しでのリトライ/フォールバック（失敗時 macro_sentiment=0.0）。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。

- データプラットフォーム関連（src/kabusys/data/）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーに基づく営業日判定ユーティリティを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - market_calendar が未取得の場合は曜日ベースのフォールバック（週末除外）。
    - 夜間バッチ calendar_update_job による J-Quants からの差分取得→保存処理と健全性チェック、バックフィル機能。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETLResult データクラスを定義（取得数・保存数・品質問題・エラー一覧を保持）。
    - 差分取得・バックフィル・品質チェック（quality モジュール）を想定した設計。
    - DuckDB を前提にした最大日付取得・テーブル存在チェック等のユーティリティを実装。
    - data/etl から ETLResult を再エクスポート。

- リサーチ / ファクター関連（src/kabusys/research/）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン, 200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を計算する関数を提供:
      - calc_momentum, calc_volatility, calc_value
    - DuckDB SQL を駆使して営業日ベースの窓計算を行う実装。
    - 不足データ時は None を返す挙動。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）、IC 計算 calc_ic（Spearman ρ）、ランク変換 rank、統計サマリー factor_summary を提供。
    - pandas 等外部依存を避け、標準ライブラリのみでの実装。

- その他
  - DuckDB を中心としたデータ操作を想定した設計（戻り値は Python ネイティブ型や dict のリスト）。
  - 各所でログ出力を適切に配置し、失敗時は例外伝播またはフェイルセーフ（ログ警告＋フォールバック）を行うポリシーを採用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / 実装上の重要ポイント
- ルックアヘッドバイアス防止:
  - AI モジュールやリサーチ関数は datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を渡す設計。
- OpenAI 連携:
  - gpt-4o-mini を利用する想定。JSON Mode による厳密なパース、リトライとバックオフ、5xx/ネットワークエラーに対するフォールバック動作を実装。
  - テストのために _call_openai_api をパッチ可能にしてある（unittest.mock 等で差し替え可能）。
- DuckDB の互換性考慮:
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）の挙動を考慮して、空チェックを入れている箇所がある。
- .env パーサー:
  - export プレフィックス、クォート、エスケープシーケンス、コメント処理を考慮した独自実装。キーが未設定の場合は書き込みをスキップ（override フラグの挙動あり）。
- DB 書き込みは可能な限り冪等性を保つ（DELETE → INSERT、ON CONFLICT 期待設計等）。
- 設計原則として「本番口座・発注 API にはアクセスしない」コードパス（研究/分析モジュール）を明確に分離。

--- 

今後のリリースでは、API 呼び出しの抽象化、テストカバレッジの強化、監視・メトリクスの追加、さらに細かな品質チェックルール追加を予定しています。