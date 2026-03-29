CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠します。  
慣例: 「Added / Changed / Fixed / Deprecated / Removed / Security / Notes」。

Unreleased
----------
（なし）

0.1.0 - 2026-03-29
-----------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 主要サブパッケージを公開: data, research, ai, monitoring, strategy, execution（__all__ での想定外のエクスポートに注意）。
- 環境設定/ロード機能（src/kabusys/config.py）。
  - .env / .env.local の自動ロード（プロジェクトルートの検出: .git または pyproject.toml を起点）。
  - OS 環境変数を保護する読み込み順序（OS env > .env.local > .env）。
  - エクスポート形式やコメント、クォート・エスケープに対応した .env パーサを実装（export KEY=, '...' / "..." のエスケープ処理、インラインコメントルール）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスでアプリ設定をプロパティとして公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など）。
  - 値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live / is_paper / is_dev のユーティリティ。
  - 必須環境変数未設定時は ValueError を発生させる _require。

- AI 関連（src/kabusys/ai/）
  - ニュースセンチメント解析モジュール（news_nlp.score_news）。
    - ニュース収集ウィンドウの計算（JST ベース→UTC naive の返却、calc_news_window）。
    - raw_news / news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信（バッチサイズ上限・文字数トリム等）。
    - JSON Mode を期待したレスポンス処理と堅牢なパース/バリデーション（余分なテキストを含む場合の最外 {} 抽出含む）。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライ。
    - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - テストしやすいように _call_openai_api を patch で差し替え可能に実装。
  - 市場レジーム判定モジュール（regime_detector.score_regime）。
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して 'bull'/'neutral'/'bear' を判定。
    - prices_daily からの MA200 計算、raw_news からのマクロキーワード抽出、OpenAI 呼び出しとスコア合成。
    - API エラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ設計。
    - DB への書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理。エラー時は ROLLBACK を試み上位へ伝播。
    - OpenAI 呼び出し実装はニュースモジュールとは独立（モジュール結合を避ける）。

- データ関連（src/kabusys/data/）
  - カレンダー管理（calendar_management.py）。
    - market_calendar を基にした is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day の実装。
    - market_calendar 未取得時は曜日ベース（土日休業）でフォールバックする一貫した挙動。
    - 最大探索日数制限や健全性チェック、バックフィル処理、JPX（J-Quants 経由）差分取得の夜間ジョブ calendar_update_job を提供。
  - ETL / パイプライン（pipeline.py, etl.py）。
    - 差分更新、backfill、品質チェックのフレームワークを実装。
    - ETLResult データクラスを公開（etl.ETLResult をデータ platform 用に再エクスポート）。
    - DuckDB を前提とした最大日付取得やテーブル存在チェックなどのユーティリティ。
    - 品質チェック結果（quality_issues）とエラー情報を集約して返す設計。

- Research（src/kabusys/research/）
  - Factor 計算（factor_research.py）。
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR, 相対 ATR）、Liquidity（20日平均売買代金/出来高比）、Value（PER, ROE）の計算実装。
    - DuckDB SQL を活用した効率的な窓関数処理、データ不足時の None 扱い。
  - Feature exploration（feature_exploration.py）。
    - 将来リターン計算（複数ホライズンに対応、ホライズン検証）、IC（Spearman の ρ）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリー（count, mean, std, min, max, median）。
    - pandas 等外部依存を使わない純 Python 実装。欠損や非有限値の除外を考慮。

- 共通設計方針
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を内部処理で参照しない設計（target_date 引数を基準に処理）。
  - DuckDB を主要なローカル分析 DB として使用。実行前提のテーブル（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials 等）を想定。
  - API キーや外部接続情報は環境変数経由で注入。OpenAI 呼び出しは api_key 引数で上書き可能。
  - テストの容易性を考慮して外部 API 呼び出し部分を差し替え可能に実装（例えば _call_openai_api の patch）。

Security
- .env 読み込み時に OS 環境変数を保護（protected set）し、.env.local でも OS 環境変数が上書きされないように実装。

Notes
- OpenAI 関連:
  - gpt-4o-mini を想定した JSON Mode を使うため、レスポンスのパースとバリデーションを厳格に実装している（余分なテキスト混入への回復処理あり）。
  - API エラー・レート制限・ネットワーク断に対する再試行・バックオフ戦略が各モジュールで整備されているが、利用時のコスト・レイテンシに注意。
- DuckDB の executemany に関する互換性（空リスト不可）を考慮した実装が含まれている（ai_scores の置換処理等）。
- 環境変数未設定時は ValueError を送出する箇所があるため、本番運用前に必要な環境変数を正しく設定してください（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
- 現状の実装は「分析・研究・スコア生成」機能を主目的としており、発注や実行に関するコード（execution/strategy/monitoring など）はパッケージ構造上で想定されているが、本差分ではデータ取得・NLP・リサーチ周りの実装が中心。

Breaking Changes
- なし（初期リリース）。

今後の予定（提案）
- モジュール間のテストカバレッジ拡充（特に OpenAI 呼び出しのモックテスト）。
- ai モジュールのレスポンス検証ルール拡張（スキーマ検証、より詳細なエラーロギング）。
- pipeline の品質チェックルール強化と自動アラート連携（Slack 通知等）。

-----