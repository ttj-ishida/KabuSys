# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の形式に従います。  

注: 本リポジトリの初回リリース相当の変更点は、ソースコードから推測してまとめています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを導入。バージョンは `0.1.0`。
  - パッケージの公開 API を `__all__ = ["data", "strategy", "execution", "monitoring"]` で定義。

- 環境設定 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を自動読み込みする仕組みを実装。
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）に基づいて行う。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能（テスト用）。
  - .env パーサーは次をサポート:
    - `export KEY=value` 形式、
    - シングル/ダブルクォート内のバックスラッシュエスケープ、
    - クォートなしでのインラインコメント認識（直前が空白/タブの場合）。
  - 環境変数の必須チェック `_require()` を提供（未設定時は ValueError）。
  - Settings クラスを導入し、以下の設定プロパティを提供:
    - J-Quants / kabu ステーション / Slack の必要トークン、DB パス（DuckDB/SQLite）、環境種別 (`KABUSYS_ENV`) とログレベル (`LOG_LEVEL`) の検証、is_live/is_paper/is_dev 判定等。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP (news_nlp)
    - raw_news / news_symbols を用いてニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON Mode で銘柄別センチメントを取得。
    - バッチ処理（最大 20 銘柄 / API コール）・トークン過膨張対策（記事数/文字数上限）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装。
    - 取得したスコアを ±1.0 にクリップし、ai_scores テーブルへ「部分置換方式（DELETE → INSERT）」で安全に書き込み。
    - テスト容易性のため API 呼び出し部分を外部でパッチ可能に設計（_call_openai_api を差し替え可）。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す。
  - レジーム判定 (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - prices_daily / raw_news からデータ取得、OpenAI を用いた macro_sentiment 評価、スコア合成、market_regime への冪等書き込みを実装。
    - API エラー時は macro_sentiment=0.0 でフェイルセーフ継続。OpenAI 呼び出しはモジュール独自実装で結合を低減。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。

- データサブシステム (src/kabusys/data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダー向けの夜間バッチ更新ジョブ(calendar_update_job)を実装。J-Quants API から差分取得して market_calendar に冪等保存。
    - 営業日判定・探索ユーティリティを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - カレンダー未取得時は曜日ベース（平日）でフォールバックする堅牢な設計。
    - バックフィル、先読み、健全性チェック（過度に未来の日付はスキップ）等を導入。
  - ETL パイプライン (pipeline)
    - ETLResult データクラスを追加し、ETL 実行結果の集約（取得件数・保存件数・品質問題・エラー等）を提供。
    - 差分フェッチ・保存・品質チェックの設計方針と内部ユーティリティ（テーブル存在確認、最大日付取得など）を実装。
  - etl モジュールは ETLResult を再エクスポート。

- リサーチ (src/kabusys/research)
  - factor_research
    - モメンタム/ボラティリティ/バリュー等の定量ファクター計算関数を実装:
      - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev（200日 MA 乖離）等。
      - calc_volatility(conn, target_date): atr_20 / atr_pct / avg_turnover / volume_ratio 等。
      - calc_value(conn, target_date): PER / ROE（raw_financials と prices_daily を結合）。
    - データ不足時は None を返す設計。
  - feature_exploration
    - calc_forward_returns(conn, target_date, horizons=None): 将来リターン（複数ホライズン）を計算。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）を計算。
    - rank(values) および factor_summary(records, columns) を提供（同順位は平均ランク、統計サマリー）。
  - research パッケージは主要関数を __all__ により公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の制約・設計上の注意 (Notes)
- 多くの処理は DuckDB 接続（DuckDBPyConnection）に依存する。テーブル schema（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols 等）が前提。
- 外部 API（OpenAI / J-Quants / kabu ステーション等）呼び出しが含まれるため、環境変数（API キー等）の設定が必須。Settings クラスの _require() により未設定時は例外が発生する。
- AI レスポンスのパースは堅牢化されているが、レスポンス形式が大きく変わった場合は想定外の結果（スコア欠落等）が発生する可能性がある。
- feature_calc の一部（PBR・配当利回り）は未実装。
- 一部の DuckDB バインド挙動（executemany と空リスト）に対応する保険的実装が行われているため、DuckDB のバージョン互換性に注意。

---

開発・運用上の詳細（ログ出力・リトライ方針・フェイルセーフ挙動・ルックアヘッドバイアス回避の設計意図等）は各モジュールのドキュメント文字列に記載しています。必要に応じて各モジュールの詳細な変更履歴や使用例を別途追記してください。