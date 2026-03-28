# Changelog

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。  
慣例として、バージョン番号と日付を記載しています。

※ 本 CHANGELOG はソースコードを解析して推測に基づいて作成したものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-28
初回公開リリース。

### 追加 (Added)
- パッケージ基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - top-level エクスポート: data, strategy, execution, monitoring

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml 基準で探索）
  - .env 読み込みの優先順位: OS環境変数 > .env.local > .env
  - 自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサーの強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - 行末コメント（#）の取り扱い（クォート外でかつ直前が空白/タブ時にコメントと認識）
  - 環境変数取得ユーティリティ Settings を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須とするプロパティ
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV のデフォルト値とバリデーション
    - is_live / is_paper / is_dev ヘルパー

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメント解析 (news_nlp.py)
    - score_news(conn, target_date, api_key=None)
      - raw_news / news_symbols テーブルから銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON mode で一括スコアリング
      - バッチ処理（1回最大 20 銘柄）、1銘柄あたり最大記事数・最大文字数でトリム
      - レスポンス検証（JSONパース、results 配列、code/score 検証）、スコアは ±1.0 にクリップ
      - DuckDB への書き込みは部分更新（DELETE → INSERT）で冪等性を確保
      - API リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を実装、失敗時は個別チャンクをスキップして継続
    - calc_news_window(target_date)：JST ベースのニュース収集ウィンドウ計算ユーティリティ
    - テスト容易性のため _call_openai_api は差し替え可能（unittest.mock.patch）

  - 市場レジーム判定 (regime_detector.py)
    - score_regime(conn, target_date, api_key=None)
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して日次で regime_label を判定（bull/neutral/bear）
      - MA 計算は target_date 未満データのみを使用（ルックアヘッドバイアス防止）
      - マクロ記事が無い場合は LLM 呼び出しをスキップ、API エラー時は macro_sentiment=0.0 のフェイルセーフ
      - OpenAI 呼び出しは内部で独立実装（モジュール結合を避ける）
      - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT で冪等処理、例外時は ROLLBACK を試行

- データ系モジュール (src/kabusys/data)
  - カレンダー管理 (calendar_management.py)
    - JPX カレンダー取得・夜間更新ジョブ（calendar_update_job）
      - J-Quants クライアント経由で差分取得 → 保存（save_market_calendar を使用）
      - バックフィル（直近 N 日を再フェッチ）と健全性チェック（将来日付の異常検知）
    - 営業日判定ユーティリティ:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
      - market_calendar データがない/未登録日の場合は曜日ベース（週末除外）でフォールバック
      - 探索は最大 _MAX_SEARCH_DAYS 日に制限し無限ループを防止
  - ETL パイプライン (pipeline.py, etl.py)
    - ETLResult データクラスを公開（etl.ETLResult 経由で再エクスポート）
      - ETL の集計結果、品質チェック結果、エラーリストを保持
      - has_errors / has_quality_errors ヘルパー、辞書変換 to_dict を提供
    - 差分更新・バックフィル・品質チェックを行う設計（実装は jquants_client / quality モジュールを利用する想定）
    - DuckDB のテーブル存在チェック、最大日付取得などのユーティリティを含む

- リサーチ系モジュール (src/kabusys/research)
  - factor_research.py
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、ma200 乖離計算
    - calc_volatility(conn, target_date): 20日 ATR、相対 ATR、平均売買代金、出来高比率
    - calc_value(conn, target_date): PER, ROE（raw_financials から最新レコードを参照）
    - 各関数は prices_daily / raw_financials のみを参照し、結果を (date, code) を含む dict のリストで返す
  - feature_exploration.py
    - calc_forward_returns(conn, target_date, horizons=None)：任意ホライズンの将来リターンを一括取得
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンのランク相関（IC）を計算
    - rank(values)：同順位は平均ランクで処理するランキングユーティリティ
    - factor_summary(records, columns)：count/mean/std/min/max/median を算出

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）
  - ただし各モジュールで不整合発生時にログを残して安全にフォールバック／スキップする実装を含む（例: API パース失敗 → スコア 0.0、DB 書込失敗時の ROLLBACK ログ等）。

### 非推奨 (Deprecated)
- （なし）

### 削除 (Removed)
- （なし）

### セキュリティ (Security)
- 環境変数による機密情報（OpenAI API キー等）を想定。Settings による必須チェックを実装し、.env の自動上書きを防ぐ保護（protected）機構を導入。
- 開発/本番区分は KABUSYS_ENV で制御。ログレベルは LOG_LEVEL で制御（許容値をバリデーション）。

---

開発者向け補足（実装上の主要な設計方針）
- ルックアヘッドバイアス回避: 各 AI / リサーチ関数は datetime.today() / date.today() を内部で参照せず、必ず外部から target_date を渡す設計。
- 冪等性: DB への書き込みは基本的に DELETE→INSERT または ON CONFLICT 相当で冪等化を図る。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）のエラーは個別にフェイルセーフで処理し、全体処理の継続を優先する。
- テスト容易性: OpenAI 呼び出し部分は _call_openai_api をパッチ可能にしてユニットテストで差し替え可能にしている。
- DuckDB 互換性: executemany に空リストを渡せないバージョンの互換性を考慮したチェックを実装。

以上。