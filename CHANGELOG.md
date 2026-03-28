# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このファイルは「Keep a Changelog」の慣習に従って構成されています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0。
  - パッケージの公開 API を __all__ で定義（"data", "strategy", "execution", "monitoring"）。
  - DuckDB を中心としたローカルデータプラットフォームを想定した設計（多くのモジュールが DuckDB 接続を引数に取る）。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索（CWD に依存しない）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途想定）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントなどに対応。
    - ファイル読み込み失敗時に警告を出す実装。
  - Settings クラスを公開（settings インスタンスを利用）。
    - 必須環境変数取得用の _require を提供（未設定時に ValueError を送出）。
    - サポートする主要設定:
      - JQUANTS_REFRESH_TOKEN（必須）
      - KABU_API_PASSWORD（必須）
      - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
      - SLACK_BOT_TOKEN（必須）
      - SLACK_CHANNEL_ID（必須）
      - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
      - SQLITE_PATH（デフォルト: data/monitoring.db）
      - KABUSYS_ENV（有効値: development / paper_trading / live、デフォルト: development）
      - LOG_LEVEL（有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
    - ヘルパー: is_live / is_paper / is_dev プロパティ。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いて銘柄単位のセンチメントスコアを算出・ai_scores テーブルへ書き込み。
    - 処理の特徴:
      - スコア算出ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）
      - 1 銘柄あたり最大記事数・最大文字数でトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）
      - バッチ処理（最大 20 銘柄単位）
      - レスポンスは JSON mode を期待し、冗長な前後テキストが混在するケースも復元してパース
      - 429 / 接続断 / タイムアウト / 5xx に対する指数バックオフのリトライ実装（リトライ回数上限あり）
      - レスポンス検証: results 配列、code と score の存在、未知コードは無視、スコアを ±1.0 にクリップ
      - 書き込みは部分成功に配慮し、取得できたコードのみ DELETE → INSERT の冪等置換
    - 公開関数:
      - calc_news_window(target_date) → (window_start, window_end)
      - score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数
    - テスト容易性:
      - OpenAI 呼び出しを行う内部関数 _call_openai_api は patch 可能（unittest.mock.patch 推奨）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を組み合わせて日次で市場レジームを判定（bull/neutral/bear）し market_regime テーブルへ保存。
    - 処理の特徴:
      - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）。
      - マクロ記事は raw_news からキーワードでフィルタ（_MACRO_KEYWORDS）し、最大件数を制限して LLM へ送信。
      - OpenAI 呼び出しは専用関数 _call_openai_api（news_nlp の実装とは切り離し）。
      - API 失敗時はフェイルセーフとして macro_sentiment=0.0 を用いる（例外は上げない）。
      - 冪等に market_regime を更新（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - 公開関数:
      - score_regime(conn, target_date, api_key=None) → 1（成功）

- データ / ETL / カレンダー (kabusys.data)
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ロジック（calendar_update_job）を実装。
      - J-Quants API から差分取得して market_calendar テーブルへ保存（バックフィル・健全性チェックあり）。
      - last_date が極端に将来の場合はスキップして警告出力。
    - 営業日判定ユーティリティを提供:
      - is_trading_day(conn, d)
      - next_trading_day(conn, d)
      - prev_trading_day(conn, d)
      - get_trading_days(conn, start, end)
      - is_sq_day(conn, d)
    - 設計方針:
      - market_calendar データがない場合は曜日（週末）ベースでフォールバック。
      - DB に登録があれば DB 値を優先、未登録日は曜日ベースの補完で一貫性を担保。
      - 最大探索範囲を設定して無限ループを回避。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラス（結果集約、品質問題・エラーメッセージの格納、has_errors / has_quality_errors 判定、to_dict）
    - 差分取得 → 保存 → 品質チェックという ETL の設計方針に基づく実装骨子を用意（実装は jquants_client / quality モジュールと連携）。
    - デフォルトバックフィル日数や最小データ日付などの定数を定義し、挙動を制御。
    - jquants_client を通じた idempotent な保存（save_* 呼び出し）を想定。
    - 品質チェックは重大度を収集するが、ETL 自体は継続して実行（呼び出し側で判断）。
  - その他ユーティリティ:
    - data.etl は ETLResult を公開再エクスポート。

- 研究用モジュール (kabusys.research)
  - factor_research
    - モメンタム、ボラティリティ（ATR）およびバリュー（PER, ROE）等のファクター計算関数を実装:
      - calc_momentum(conn, target_date) → mom_1m, mom_3m, mom_6m, ma200_dev
      - calc_volatility(conn, target_date) → atr_20, atr_pct, avg_turnover, volume_ratio
      - calc_value(conn, target_date) → per, roe
    - DuckDB の SQL ウィンドウ関数を用いて集計（LAG/AVG/COUNT 等）。
    - データ不足時は None を返すなど堅牢な扱い。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons)
      - 複数ホライズンをまとめて1クエリで取得、horizons の妥当性チェックあり。
    - IC（スピアマンランク相関）計算 calc_ic(...)
      - rank（同順位は平均ランク）、ランク変換関数を含む。
      - 有効レコードが少ない場合は None を返す。
    - factor_summary(records, columns)
      - count / mean / std / min / max / median を計算する軽量ユーティリティ。
  - これら研究用 API は prices_daily / raw_financials 等の読み取り専用であり、本番発注ロジックへはアクセスしない設計。

### Notes / 実装上の重要事項
- 全体設計に共通する方針
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を内部で直接参照せず、target_date ベースで明示的に処理を行う。
  - OpenAI 等の外部 API 呼び出しはフェイルセーフ（API 失敗時にスキップまたは中立値で継続）を基本方針とする。
  - テスト容易性を考慮し、OpenAI 呼び出し箇所などは内部関数を patch 可能にしている。
  - DuckDB の executemany に関する注意点（空リスト不可等）に対応した実装。
- 環境変数/ファイルに関する注意
  - .env のパースルールは比較的寛容だが、必須項目が未設定の場合は ValueError を投げる設計のため、デプロイ前に .env 等を正しく用意すること。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するとパッケージインポート時の自動 .env 読み込みを抑止できる（テストや CI で有用）。

### Deprecated
- なし（初回リリース）。

### Removed
- なし（初回リリース）。

### Fixed
- なし（初回リリース）。

### Security
- 外部 API キー（OpenAI など）は環境変数で管理することを想定。コード内に埋め込まないでください。

---

開発者向け補足:
- public API の簡単な利用イメージ:
  - 設定取得: from kabusys.config import settings
  - ニューススコア実行: from kabusys.ai.news_nlp import score_news
  - レジーム判定: from kabusys.ai.regime_detector import score_regime
  - ファクター計算: from kabusys.research.factor_research import calc_momentum
  - カレンダー更新: from kabusys.data.calendar_management import calendar_update_job

フィードバックやバグ報告は Issue にてお願いします。