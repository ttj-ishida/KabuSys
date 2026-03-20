Keep a Changelog 準拠 — CHANGELOG.md

すべての変更はセマンティックバージョニングに従います。  
このファイルは、コードベースから推測できる実装内容・意図に基づき作成した初期の変更履歴です。

Unreleased
---------
- 今後の追加予定・改善案（参考）
  - ポジション管理情報（peak_price / entry_date）を positions テーブルに保持し、
    トレーリングストップや保有日数に基づく時間決済を実装する。
  - ニュース記事の銘柄紐付け（news_symbols）の自動化ロジック強化（NLP 利用など）。
  - execution 層（kabuステーション連携）の実装とテストカバレッジ拡充。
  - モジュール間の依存注入改善と単体テストの追加。

[0.1.0] - 2026-03-20
-------------------

Added
- 基本パッケージ構成を追加（kabusys パッケージ、__version__ = 0.1.0）。
- 環境設定管理モジュールを追加（kabusys.config）。
  - .env ファイルおよび環境変数から設定を読み込み。
  - プロジェクトルートの検出（.git または pyproject.toml を起点）により
    CWD に依存しない自動 .env 読み込みを実装。
  - .env の書式解析を堅牢化（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - .env / .env.local の読み込み優先度（OS 環境 > .env.local > .env）と上書き保護（protected keys）を実装。
  - Settings クラスを提供し、必須環境変数の検査、enum 的な env/log level の検証、データベースパスの Path 表現などのプロパティを実装。

- データ取得/保存モジュール（kabusys.data）を追加
  - J-Quants クライアント（kabusys.data.jquants_client）
    - API レート制御（120 req/min を固定間隔スロットリングで制御する RateLimiter）。
    - ページネーション対応の fetch_* 系関数（daily_quotes / financial_statements / market_calendar）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）、429 の Retry-After 尊重。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、
      ON CONFLICT による冪等保存を実現。
    - データ型変換ユーティリティ（_to_float / _to_int）を提供し、入力の堅牢性を確保。
  - ニュース収集（kabusys.data.news_collector）
    - RSS フィードからの記事取得と正規化機能を追加（既定ソースに Yahoo Finance）。
    - URL 正規化（トラッキングパラメータ削除・ソート・フラグメント削除・小文字化）。
    - security 対策: defusedxml を利用した XML パース、受信バイト数上限、SSRF 対策（HTTP/HTTPS 判定想定）。
    - 記事ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を担保。
    - DB へのバルク挿入時にチャンク処理を行いパフォーマンス/SQL 制限を考慮。

- リサーチ・戦略モジュール（kabusys.research, kabusys.strategy）
  - ファクター計算（kabusys.research.factor_research）
    - momentum / volatility / value を DuckDB の prices_daily / raw_financials を用いて計算。
    - mom_1m/mom_3m/mom_6m、ma200_dev、atr_20 / atr_pct、avg_turnover、volume_ratio、per / roe などを提供。
    - ウィンドウや不足データ時の None ハンドリングを実装。
  - 特徴量探索・解析（kabusys.research.feature_exploration）
    - calc_forward_returns（複数ホライズンの将来リターン取得、1/5/21 日がデフォルト）を実装。
    - calc_ic（Spearman ランク相関: IC）を実装（同順位は平均ランクで処理）。
    - factor_summary（count/mean/std/min/max/median）と rank 関数を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装する方針。
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価・流動性）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位の置換（冪等）で保存（トランザクション + バルク挿入）。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースの各コンポーネントを計算。
    - コンポーネントに対する重み付け（デフォルト weight を実装）と、ユーザー渡しの weights の検証／正規化（負値・NaN・非数値を無視、合計が 1 に再スケール）。
    - final_score による BUY シグナル生成（閾値デフォルト 0.60）、Bear レジーム時の BUY 抑制。
    - エグジット（SELL）判定: ストップロス（終値 / avg_price - 1 < -8%）および final_score の閾値割れを実装。
    - signals テーブルへ日付単位の置換（冪等）で保存（トランザクション・ROLLBACK 対応）。

Changed
- -（初期リリースのため過去変更なし。実装方針・設計注記をソース内 docstring で明確化）

Fixed
- .env パーサの改善（コメントやクォート、エスケープ、export 付き行の処理不備を考慮）。
- DuckDB への複数テーブル保存処理で PK 欠損行をスキップして警告を出すように変更（データ品質問題の早期検出）。
- HTTP リトライの挙動を改善（429 の Retry-After 優先、最大試行回数での適切な例外送出）。

Security
- RSS パースに defusedxml を採用して XML Bomb 等から保護。
- ニュース収集で受信サイズ上限（10 MB）を設け、メモリ DoS を緩和。
- URL 正規化時に HTTP/HTTPS スキームしか受け付けない前提で SSRF リスクを低減（実装により想定）。
- J-Quants クライアントはトークン管理・自動更新を実装し、認証エラーを適切に扱う。

Performance
- DuckDB へのバルク挿入（executemany）と日付単位の置換による原子性確保で大量データ挿入時のパフォーマンスを配慮。
- ニュース挿入でチャンク処理を採用し SQL パラメータ数制限に対応。
- J-Quants API 呼び出しは固定間隔スロットリングによりレート制限に準拠。

Known limitations / Notes
- positions テーブルに peak_price / entry_date 等が無い場合、トレーリングストップや時間決済等は未実装。コード中でも未実装コメントを残している。
- 一部の挙動（例: features に存在しない保有銘柄は final_score=0 として扱う）は明示的なポリシーとして実装されているが、運用方針により調整が必要。
- ニュース→銘柄紐付け（news_symbols）部分の実装は説明にあるが、詳細アルゴリズムは今後の実装対象。
- 外部依存を減らす方針のため、データ解析処理は pandas 等に依存しない実装になっている。大規模データや高度な分析が必要な場面では追加検討が必要。

Deprecated
- なし

Removed
- なし

参考（実装上の主要ファイル / 主要関数）
- kabusys.config: Settings, 自動 .env 読み込み、_parse_env_line, _find_project_root
- kabusys.data.jquants_client: _RateLimiter, _request, get_id_token, fetch_* / save_* / _to_float/_to_int
- kabusys.data.news_collector: _normalize_url, NewsArticle 型、RSS 周りの保護処理
- kabusys.research.factor_research: calc_momentum, calc_volatility, calc_value
- kabusys.research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy.feature_engineering: build_features
- kabusys.strategy.signal_generator: generate_signals, _generate_sell_signals, スコア計算ユーティリティ群

もし CHANGELOG を実際のコミット履歴に合わせて厳密に整備したい場合は、Git のログ（コミットメッセージ）やリリースノートの草案を提供してください。そこからセマンティックに沿った履歴（Added/Changed/Fixed/Removed/Security など）を細かく分割して作成します。