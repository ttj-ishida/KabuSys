# CHANGELOG

すべての注目すべき変更点を記述します。  
このファイルは Keep a Changelog 準拠の形式で記載しています。

## [Unreleased]

## [0.1.0] - 2026-04-09

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
- パッケージ公開情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - __all__ に data, strategy, execution, monitoring を公開。
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - コメント処理（クォートあり/なしの扱い差分）
  - _load_env_file による保護（override と protected keys）実装。
  - Settings クラスを提供し、主要設定（J-Quants トークン、kabu API 設定、LINE トークン、DB パス、Paper Trading 設定、監視しきい値、環境/ログレベル判定等）をプロパティで取得可能。
  - 必須設定取得時に未設定なら ValueError を投げる _require を実装。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）、KABUSYS_ENV / LOG_LEVEL の検証を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を使い銘柄毎にニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを評価、ai_scores テーブルへ書き込み。
  - タイムウィンドウ計算（JST: 前日15:00 ～ 当日08:30 → UTC に変換）を calc_news_window として公開。
  - バッチ処理: 最大 20 銘柄/コール、1銘柄あたりの記事数・文字数制限（記事数上限/文字トリム）。
  - OpenAI への JSON Mode 呼び出しを行い、レスポンスのバリデーションを厳格化。レスポンスパース失敗や API エラーはフェイルセーフでスキップ。
  - リトライ戦略: 429・ネットワーク断・タイムアウト・5xx に対して指数バックオフでリトライ。
  - DuckDB 互換性考慮（executemany に空リスト渡さない等）。
  - public API: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。APIキー未設定時は ValueError。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュース（LLM によるセンチメント、重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
  - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
  - OpenAI 呼び出しは内部的に独立実装され、テスト用に差し替え可能。
  - API 障害時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
  - public API: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。APIキー未設定時は ValueError。

- データプラットフォーム（kabusys.data）
  - ETL パイプラインの結果を表す ETLResult データクラスを追加（kabusys.data.pipeline、kabusys.data.etl で再エクスポート）。
    - ETLResult は取得数・保存数・品質問題・エラー一覧等を保持し、has_errors / has_quality_errors / to_dict を提供。
  - calendar_management モジュール:
    - market_calendar テーブルに基づいた営業日判定ロジックを提供（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 未取得時は曜日ベースのフォールバック（土日非営業日）。
    - 最大探索日数制限で無限ループ防止。
    - 夜間バッチ更新 job: calendar_update_job(conn, lookahead_days=90) を実装。J-Quants から差分取得して冪等保存（バックフィル・健全性チェック含む）。
  - pipeline モジュール（ETLの骨組み）:
    - 差分取得、idempotent 保存、品質チェックのための基盤説明と ETLResult を提供。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB ベースの SQL 実装で lookback バッファを考慮（データ不足時は None を返す）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（入力検証あり）。
    - calc_ic: ファクタ値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 未満で None）。
    - rank: 同順位は平均ランクを返すランク関数（丸めによる ties 対応）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージは主要関数を __all__ で公開（zscore_normalize は kabusys.data.stats から再利用）。

Security / Safety / Reliability
- OpenAI 連携部分は APIキー未設定時に明示的なエラーを出す（呼び出し元で制御可能）。
- LLM 呼び出しの失敗は基本的にフェイルセーフ（デフォルトスコア 0.0、部分スキップ）でシステム全体の停止を防止。
- DuckDB の実装はバージョン依存の挙動（executemany の空リスト等）へ注意して実装。

Notes
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - OPENAI_API_KEY（AI モジュール利用時）
- Paper Trading 用 DB や PID/KILL フラグなど監視関連のパスはデフォルト設定ありが可能（Settings から上書き可）。
- strategy / execution / monitoring の実装はインターフェースを公開しているが、本リリースでは主にデータ/研究/AI 側の基盤実装を含む。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

---

参照:
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0" に基づく初回リリース記録。