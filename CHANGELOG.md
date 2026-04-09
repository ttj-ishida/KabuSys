Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
このプロジェクトでは "Keep a Changelog" の慣例に従います。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-09
--------------------

Added
- 初回リリースを追加（バージョン 0.1.0）。
- 基本パッケージ構成
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"、主要サブパッケージを __all__ に公開。
- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式やクォート／エスケープ、行内コメント処理に対応したパーサ実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須変数チェック用 _require() を提供（未設定時は ValueError）。
  - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DB パス / monitoring / システム設定 等）。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値検証とエラーメッセージを実装。
- ポートフォリオ構築 (src/kabusys/portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア降順ソート（score, signal_rank によるタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、セクター集中上限超過時に候補を除外（sell_codes を考慮、"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime (bull/neutral/bear) に応じた資金乗数を返す（未知レジームはフォールバック）。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の割当方式をサポート。許容リスク、損切り率、単元枚数(lot_size)、1銘柄上限、総投下上限、手数料スリッページバッファ(cost_buffer) を考慮した株数算出ロジックを実装。
    - aggregate cap の超過時はスケールダウンと lot_size 単位での再配分（端数処理・残差順配分）を行う。
    - ログ出力や価格欠損時のスキップ処理を実装。
- リサーチ／ファクター計算 (src/kabusys/research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離を DuckDB SQL で計算。データ不足時は None。
    - calc_volatility: 20日 ATR、ATR / close、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を制御。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS 欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンへの将来リターンを一括クエリで取得。horizons バリデーションあり。
    - calc_ic: スピアマンランク相関（IC）を純粋 Python 実装で計算（ランクは同順位平均ランク処理）。
    - rank / factor_summary: ランク算出および count/mean/std/min/max/median の統計サマリーを提供。
  - research パッケージ __init__ で主要関数と zscore_normalize を公開。
  - 実装は DuckDB 接続を受け取り、外部 API へは依存しない方針。
- AI 関連 (src/kabusys/ai)
  - news_nlp:
    - score_news: raw_news を集約して OpenAI (gpt-4o-mini) へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込むフローを実装。
    - バッチサイズ、文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）、レスポンス検証、スコアの ±1.0 クリップ、トランザクション（DELETE→INSERT）をサポート。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。API 失敗時は部分スキップ（フェイルセーフ）。
    - calc_news_window を実装（JST ベースの時間窓を UTC naive datetime に変換）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - regime_detector:
    - score_regime: ETF 1321 の MA200 乖離 (70%) とマクロニュース LLM センチメント (30%) を合成して market_regime に書き込む機能を実装。
    - マクロニュースはキーワードフィルタで抽出、LLM 呼び出しは失敗時に macro_sentiment=0.0 でフォールバック。
    - ルックアヘッド防止（prices_daily の date < target_date）やトランザクションを確保した冪等書き込みを実装。
- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db: system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを SQLite で冪等作成する処理を実装。

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- N/A

Deprecated
- N/A

Removed
- N/A

Breaking Changes
- なし（初回リリース）

Notes / Known limitations / TODO
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少に評価される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨を TODO として残している。
- position_sizing:
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map へ拡張する TODO コメントあり。
- DuckDB executemany に関する互換性:
  - DuckDB 0.10 の制約を回避するため、executemany に空リストを渡さないガード処理が実装されている。
- OpenAI レスポンスの JSON パース:
  - JSON mode を使っているが、稀に余計な前後テキストが混ざる場合を想定して復元ロジックを実装している。確実性のためプロダクションではレスポンス監視を推奨。
- 自動 .env ロード:
  - __file__ を起点に親ディレクトリを探索する実装のため、パッケージ化・配置方法によってはプロジェクトルートが特定できず自動ロードがスキップされる可能性がある（その場合 KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか手動で環境変数を設定してください）。

作者からの補足
- 設計方針として DuckDB / SQLite を用いたローカルデータ処理、外部 API 呼び出しは明確に切り分け（テスト用に差し替え可能）、ルックアヘッドバイアス防止を重視しています。