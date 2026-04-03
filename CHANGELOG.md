# Changelog

すべての重要な変更はこのファイルに記録します。本ドキュメントは「Keep a Changelog」形式に準拠します。

- 変更ログの読み方: 重大な追加は "Added"、仕様変更は "Changed"、バグ修正は "Fixed" に分類しています。
- バージョン 0.1.0 はパッケージ初回公開（初期実装）を示します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-03
初回リリース。以下の主要機能・設計方針を実装しました。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン定義 __version__ = "0.1.0" を追加。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env パーサ実装:
    - コメント行、空行、export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォート無しのインラインコメント処理（'#' の直前が空白またはタブの場合のみコメント扱い）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 環境変数上書きロジック（.env と .env.local の優先度、OS 環境変数を protected として保護）。
  - Settings クラスを公開（settings）。主要プロパティ:
    - J-Quants / kabuステーション / LINE / DB パス / 監視関連（PID ファイル、kill flag、閾値）などの取得。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - is_live / is_paper / is_dev の便宜プロパティ。
  - 必須環境変数未設定時に ValueError を送出する _require 実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価。
    - タイムウィンドウ：前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB 参照）。
    - バッチ処理: 最大 20 銘柄/リクエスト、1 銘柄あたり最大 10 記事・3000 文字にトリム。
    - JSON Mode を利用した厳密な JSON 応答を期待しつつ、前後テキスト混入時の復元ロジックを実装。
    - 再試行戦略（429 / ネットワーク断 / タイムアウト / 5xx）: 指数バックオフ。
    - レスポンス検証: results 配下の {code, score} を検証し、±1.0 でクリップ。
    - ai_scores テーブルへ冪等的に書き込み（対象コードのみ DELETE → INSERT）。DuckDB 0.10 の executemany 空リスト制約に対応。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み銘柄数を返す。API キー未設定時は ValueError。
    - テスト容易性: _call_openai_api を patch で差し替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次レジームを判定（'bull'/'neutral'/'bear'）。
    - ma200_ratio 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。
    - マクロ記事はニュースからマクロキーワードでフィルタ（最大 20 件）。記事なしの場合 LLM 呼び出しをスキップして macro_sentiment=0.0。
    - OpenAI 呼び出しでのリトライ（429/ネットワーク/タイムアウト/5xx）とフォールバック（失敗時 macro_sentiment=0.0）。
    - スコア合成: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。閾値でラベル判定（BULL_THRESHOLD/BEAR_THRESHOLD）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。書き込み失敗時は ROLLBACK。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。API キー未設定は ValueError。
    - テスト容易性: news_nlp と異なる独自の _call_openai_api 実装でモジュール間結合を避ける設計。

- データプラットフォーム (kabusys.data)
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定 API:
      - is_trading_day(conn, d)、is_sq_day(conn, d)、next_trading_day(conn, d)、prev_trading_day(conn, d)、get_trading_days(conn, s, e) を提供。
    - DB 登録値優先、未登録日は曜日ベース（週末を非営業日）でフォールバックする一貫性設計。
    - 最大探索日数制限（_MAX_SEARCH_DAYS）や健全性チェック（_SANITY_MAX_FUTURE_DAYS）。
    - 夜間バッチ: calendar_update_job(conn, lookahead_days=90) で J-Quants から差分取得、バックフィル（直近 _BACKFILL_DAYS）・健全性チェック・J-Quants クライアント経由で保存。
    - jquants_client 呼び出しに対する例外ハンドリングとログ出力。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（取得数/保存数/品質問題/エラー一覧 等）。
    - 差分更新・バックフィル方針（デフォルト backfill 3 日）、品質チェック統合（quality モジュールからの検出を収集）を想定した設計。
    - テーブル存在確認や最大日付取得などのユーティリティ実装（DuckDB を前提）。
    - kabusys.data.etl は ETLResult を再エクスポート。
    - jquants_client を使った idempotent 保存（ON CONFLICT DO UPDATE）を前提とする設計。
  - 実装上の互換性配慮:
    - DuckDB のバージョン差異（executemany の空リスト制約、日付型の取り扱い等）に配慮した実装。

- 研究用分析モジュール (kabusys.research)
  - factor_research モジュール:
    - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev を計算（不足時は None）。
    - calc_volatility(conn, target_date): atr_20、atr_pct、avg_turnover、volume_ratio を計算。true_range の NULL 伝播を慎重に扱う。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得し PER/ROE を計算。
    - DuckDB 上の SQL ウィンドウ関数を利用した実装（速度と可説明性重視）。
    - 全関数は prices_daily / raw_financials のみ参照し、本番発注 API にアクセスしないことを明示。
  - feature_exploration モジュール:
    - calc_forward_returns(conn, target_date, horizons): 将来リターン（複数ホライズン）を計算。horizons 検証あり（1..252）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を実装（有効レコード < 3 の場合 None）。
    - rank(values): 同順位は平均ランクにする実装（浮動小数点丸めで ties 検出漏れ防止）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算する軽量統計関数。
  - 研究パッケージの __init__ で主要関数を再エクスポート（使いやすさ向上）。

### Changed
（初回リリースのため該当なし）

### Fixed
（初回リリースのため該当なし）

### Deprecated
（初回リリースのため該当なし）

### Removed
（初回リリースのため該当なし）

### Security
- 環境変数のロードで OS 環境変数を保護する設計（.env が既存の OS 環境変数を意図せず上書きしない）。.env.local は override=True でローカル優先だが、OS 環境変数は protected。
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY を利用し、未設定時は ValueError により誤った公開呼び出しを防止。

---

注記（設計上の重要点）
- ルックアヘッドバイアス回避: 全てのデータ取得/判定関数は内部で datetime.today() / date.today() を参照せず、呼び出し元から target_date を受け取る設計。
- フェイルセーフ: AI API の失敗は基本的に例外を伝播させずフォールバック（例えば macro_sentiment=0.0 やスキップ）してパイプライン全体の停止を避ける方針。
- テストしやすさ: OpenAI 呼び出し部分はモック差し替え可能（ユニットテストを想定）。

もしリリースノートの表現や日付、各機能の粒度を変更したければ指示してください。