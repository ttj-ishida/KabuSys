# Changelog

すべての変更は Keep a Changelog の仕様に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

※このファイルはコードベースから推測して作成しています。実際のリリースノートとして使用する際は必要に応じて修正してください。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース。以下の主要コンポーネントと機能を実装。

### Added
- パッケージ基礎
  - パッケージ名: kabusys、バージョン 0.1.0 を src/kabusys/__init__.py に定義。
  - パッケージ API のエクスポート候補: data, strategy, execution, monitoring（__all__ に明示）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パースは export 付き、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントに対応。
    - protected 引数による OS 環境変数保護ロジック（上書き制御）。
  - Settings クラスを提供し、アプリケーションで必要な設定をプロパティ経由で取得可能。
    - 必須環境変数検証: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）。
    - その他: KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH / SQLITE_PATH の既定値、KABUSYS_ENV 検証（development/paper_trading/live）、LOG_LEVEL 検証。
    - is_live / is_paper / is_dev の便宜プロパティ実装。

- AI モジュール (src/kabusys/ai/*)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini、JSON mode）へバッチで投げてセンチメント（-1.0〜1.0）を取得。
    - バッチ処理上限: 1 API コールあたり最大 20 銘柄、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - リトライ戦略: レート制限(429)、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。
    - レスポンスの厳密バリデーション実装（JSON 抽出、results 配列・code/score 検証、未知コード無視、スコア数値化・有限値チェック、±1.0 にクリップ）。
    - DuckDB への書き込みは部分的に冪等（該当 code の DELETE → INSERT）で行い、部分失敗時に他コードの既存スコアを保護。DuckDB executemany の空リスト制約に対処。
    - テスト容易性のため _call_openai_api を patch で差し替え可能。
    - 公開関数: score_news(conn, target_date, api_key=None)
    - calc_news_window(target_date) でニュース収集ウィンドウ（JST 基準）を計算。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を統合して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベース（複数キーワードリスト）で raw_news からタイトルを取得。
    - OpenAI 呼び出しは gpt-4o-mini、JSON mode を使用。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開関数: score_regime(conn, target_date, api_key=None)
    - テスト容易性のため _call_openai_api をモジュール内で独自実装（news_nlp と共有しない設計）。

- データプラットフォーム / ETL (src/kabusys/data/*)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー夜間バッチ更新 job（calendar_update_job）を実装。J-Quants から差分取得し market_calendar テーブルへ冪等保存。
    - 営業日判定ユーティリティ群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - カレンダーデータが未取得または一部しかない場合は曜日ベースのフォールバック（週末休場）を一貫して利用。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) と健全性チェック（過度に将来日付の検出抑止）を実装。
    - J-Quants クライアントのラッパーを想定（kabusys.data.jquants_client を利用）。
  - ETL パイプライン基盤 (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を導入し、ETL 実行結果（取得数・保存数・品質チェック結果・エラー等）を構造化して返却・ログ化可能に。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの扱い、id_token 注入によるテスト容易性）を注記。
    - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（因子・特徴量探索） (src/kabusys/research/*)
  - ファクター計算群 (src/kabusys/research/factor_research.py)
    - Momentum: mom_1m / mom_3m / mom_6m、ma200_dev（200 日移動平均乖離率）。データ不足時は None を返す。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等。
    - Value: PER（EPS が 0 または欠損なら None）、ROE（raw_financials から最新レコードを結合）。
    - いずれも DuckDB SQL を活用して効率的に計算し、(date, code) ベースのレコードリストを返却。
  - 特徴量探索・統計ユーティリティ (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons)（デフォルト [1,5,21]）。
    - IC 計算: calc_ic(factor_records, forward_records, factor_col, return_col) — Spearman（ランク相関）実装。レコード不足時は None。
    - ランキング補助: rank(values)（同順位は平均ランク）。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median）を返す。
    - 実装は標準ライブラリのみで依存最小化を意識。

### Design / Quality notes
- ルックアヘッドバイアス対策: 各モジュールは date.today() / datetime.today() を利用しない設計。target_date を明示的に渡す方式を採用。
- 冪等性: DB 書き込みは可能な限り冪等化（DELETE → INSERT や ON CONFLICT を想定）。
- フェイルセーフ性: 外部 API（OpenAI、J-Quants 等）失敗時は致命例外にせずフォールバックやスキップで処理継続する設計が多数（ただし、API キー未設定は ValueError を送出して明示する）。
- テスト容易性: OpenAI 呼び出しのラッパー関数を patch で差し替え可能にしてユニットテストを容易化。
- DuckDB をデフォルトの分析 DB として使用。executemany の空リスト問題など DuckDB 固有の挙動に配慮。

### Removed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Security
- 必須 API キー・機密情報は環境変数から取得する設計。自動 .env ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

参考（必須環境変数の例）
- OPENAI_API_KEY（OpenAI 呼び出し時に利用）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（実際のデプロイ/運用時は .env.example を参照して適切に設定してください）