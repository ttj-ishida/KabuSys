# Keep a Changelog
すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」の形式に従っています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回リリース

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - パブリック API として data, strategy, execution, monitoring をエクスポート（将来的機能の入口を確保）。

- 設定・環境変数管理
  - env ファイルおよび環境変数から設定を読み込む設定モジュールを追加（src/kabusys/config.py）。
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml から探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロード無効化。
    - export KEY=val 形式やクォート・エスケープ、行末コメント等のパース処理に対応。
    - Settings クラスを通じた型安全なプロパティ提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）。
    - ログレベル・環境（development/paper_trading/live）の検証。

- AI（OpenAI）連携モジュール
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとに gpt-4o-mini でセンチメント（-1.0〜1.0）を算出して ai_scores テーブルに書き込む。
    - チャンク処理（最大 20 銘柄/コール）、1銘柄あたりの記事・文字数制限、JSON Mode レスポンスの検証ロジックを実装。
    - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - レスポンスパース時の頑健性向上（前後余計なテキストの切り出し・スコア検証・数値クリップ）。
    - テスト容易性: _call_openai_api をユニットテストで差し替え可能。
    - タイムウィンドウ算出（JST 基準、UTC 変換）を提供（calc_news_window）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定。
    - DuckDB の prices_daily, raw_news, market_regime を利用し、冪等的に market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - LLM 呼び出しのリトライ・フォールバック（API 失敗時は macro_sentiment=0.0）。
    - look-ahead バイアス防止設計（target_date 未満のデータのみ使用、date.today() を参照しない）。
    - OpenAI クライアントの利用部分を独立実装しモジュール結合を避ける設計。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン基盤（src/kabusys/data/pipeline.py / src/kabusys/data/etl.py）
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラーの集約）。
    - 差分取得・バックフィル・品質チェックの設計方針を実装するための下地（J-Quants クライアント呼び出しを想定）。
    - DuckDB テーブル存在チェック等ユーティリティを実装。

  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX マーケットカレンダー（market_calendar テーブル）の夜間バッチ更新ジョブ(calendar_update_job)を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - DB 登録値優先・未登録日は曜日ベースのフォールバック、最大探索日数制限、バックフィル・健全性チェックを実装。

  - その他
    - data パッケージの ETLResult を再エクスポートするインターフェースを追加（src/kabusys/data/etl.py）。

- 研究（リサーチ）モジュール
  - factor 計算群（src/kabusys/research/factor_research.py）
    - momentum（1M/3M/6M リターン、200日 MA 乖離）、volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、value（PER/ROE）を DuckDB の prices_daily / raw_financials を参照して算出。
    - データ不足時の None 処理・日単位（営業日ベース）での計算を想定。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算(calc_forward_returns)、IC（Information Coefficient）計算(calc_ic)、ランク変換(rank)、ファクター統計サマリー(factor_summary) を実装。
    - pandas 等の外部依存を持たずに標準ライブラリで実装。

  - research パッケージ __init__ で主要関数群をエクスポート（zscore_normalize は別モジュールから再エクスポート）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

### Notes / Limitations
- DuckDB を前提とした実装であり、必要なテーブルスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が存在することが前提。
- OpenAI API を利用する機能は OPENAI_API_KEY（または関数引数での注入）が必須。API レスポンスのフォーマットに依存するため、実運用ではキー管理とレート制限運用に注意が必要。
- strategy / execution / monitoring パッケージは __all__ に宣言されているが、本リリースに含まれるソースのスナップショットでは詳細実装が確認できない箇所がある（将来的な拡張ポイント）。
- テスト容易性のため一部の外部呼び出し（_call_openai_api 等）は差し替え可能に実装しています。ユニットテストでのモックを想定。

---

作成時点では v0.1.0 が最初のリリースです。次のリリースでは実運用でのフィードバックに基づくバグ修正、performance tuning、strategy / execution / monitoring の実装追加などを記録してください。