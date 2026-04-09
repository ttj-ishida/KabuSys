CHANGELOG
=========

すべての重要な変更点を記録します。  
このプロジェクトはセマンティックバージョニングに従います。  

フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

（現状、未リリースの変更はありません）

[0.1.0] - 2026-04-09
-------------------

初回公開リリース。以下の主要機能を実装しています。

Added
- 基本パッケージ設定
  - パッケージメタ情報（kabusys.__version__ = 0.1.0）と公開 API（__all__）を定義。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロードを実装。
  - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない実装）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ:
    - 空行・コメント行（#）を無視。
    - export KEY=val 形式に対応。
    - クォート（'"/"）内のバックスラッシュエスケープを解釈。
    - クォート無しでは "#" の直前が空白/タブの場合のみコメントと見なす。
  - .env 読み込み時に既存の OS 環境変数を保護する機能（protected set）。
  - 必須設定取得用の _require() を提供（未設定時は ValueError）。
  - 設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD の必須チェック。
    - KABU_API_BASE_URL / LINE 系 / DB パス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）などのデフォルト値。
    - Paper Trading の PAPER_FILL_MODE 検証（instant/partial/never/reject）。
    - 環境種別（KABUSYS_ENV）の検証（development, paper_trading, live）およびログレベル検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - 各種監視閾値（CPU/MEMORY/DISK）、PID/KILL フラグ関連設定。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - 銘柄選定: select_candidates — score 降順、同点時は signal_rank 昇順で上位 N を選択。
  - 重み計算:
    - calc_equal_weights — 等金額配分。
    - calc_score_weights — スコア加重配分。全銘柄スコア合計が 0.0 の場合は等金額にフォールバックし WARNING を出力。
  - リスク調整:
    - apply_sector_cap — 既存保有のセクター別エクスポージャーが閾値を超える場合、新規候補を除外（"unknown" セクターは除外対象としない）。
    - calc_regime_multiplier — 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルトマップ: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告後 1.0 でフォールバック。
  - ポジションサイズ計算:
    - calc_position_sizes — allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - risk_based: 許容リスク率 (risk_pct) と損切り幅 (stop_loss_pct) から基本株数を算出。
    - equal/score: 重みと max_utilization に基づく割当を計算。
    - lot_size（単元）で丸め、_max_per_stock による per-stock 上限を考慮。
    - aggregate cap（利用可能現金 available_cash）を超える場合はスケーリングし、端数は lot_size 単位で残差が大きい順に追加配分。
    - cost_buffer により手数料・スリッページを保守的に見積もる。
    - 価格欠損時はスキップし、ログ出力。

- リサーチ / ファクター計算 (kabusys.research)
  - calc_momentum: モメンタムファクター（1M/3M/6M リターン、MA200 乖離）を DuckDB SQL ウィンドウ関数で計算。データ不足時は None を返す。
  - calc_volatility: ATR(20)、相対ATR、20日平均売買代金、当日出来高比率を計算。true_range の NULL 伝播を適切に扱う。
  - calc_value: raw_financials から直近財務データを取得し PER/ROE を計算（EPS が 0/NULL の場合 PER は None）。
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons 引数のバリデーションあり（1〜252）。
  - calc_ic: スピアマンランク相関（IC）を計算。None 値除外、有効レコード < 3 の場合は None。
  - rank: 同順位は平均ランクで処理。丸め (round(..., 12)) による ties の安定化。
  - factor_summary: count/mean/std/min/max/median の統計サマリを提供（None 値は除外）。
  - DuckDB 依存だが外部 API にはアクセスしない設計。

- AI モジュール (kabusys.ai)
  - ニュース NLP (news_nlp.score_news):
    - raw_news / news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして OpenAI（gpt-4o-mini）へバッチ送信。
    - バッチサイズ 20、JSON Mode を利用して厳密な JSON 応答を期待。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。その他エラーはスキップ（フォールセーフ）。
    - レスポンスのバリデーション（results の存在、型、コードの既知性、スコアが有限数値等）。スコアは ±1.0 にクリップ。
    - 成功した銘柄のみ部分的に ai_scores テーブルに置換（DELETE→INSERT）して部分失敗時も既存スコアを保護。
    - 時間ウィンドウ計算（JST ベース → UTC 変換）を calc_news_window で提供（前日 15:00 JST ～ 当日 08:30 JST）。
  - レジーム判定 (regime_detector.score_regime):
    - ETF 1321 の ma200 乖離 (200 日) とマクロニュースの LLM センチメントを合成して market_regime を日次判定（重み: MA 70% / マクロ 30%）。
    - マクロキーワードフィルタ、最大記事 20 件、LLM は gpt-4o-mini を使用。
    - API 失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API 呼び出しは news_nlp とは別実装でモジュール結合を避ける。

- モニタリング永続化層 (kabusys.monitoring.monitoring_db)
  - SQLite ベースの監視ログ永続化ユーティリティを追加。
  - init_monitoring_db により冪等にテーブル/インデックスを作成（system_status, trade_logs, positions, risk_logs ... 計 5 テーブル想定）。

Changed
- （初版のため変更はなし）

Fixed
- （初版のため修正はなし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは直接引数で渡すか環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を発生させて安全に停止する箇所を実装（ニュース NLP / レジーム判定）。

Notes / 実装上の注意
- DuckDB / SQLite へのクエリはルックアヘッドバイアスを避ける設計（target_date の扱いに注意）。
- OpenAI クライアント呼び出しはテスト時に差し替え可能（内部関数を patch する設計）。
- 一部箇所に TODO コメントあり（例: 銘柄別 lot_size の将来的なサポート、価格欠損時のフォールバック戦略など）。

お問い合わせ・貢献
- バグ報告や改善提案は Issue を立ててください。仕様上の重要な設計判断（例: レジーム重み・閾値、PAPER_FILL_MODE のデフォルト等）は議論の対象です。