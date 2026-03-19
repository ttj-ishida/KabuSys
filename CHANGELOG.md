Keep a Changelog
=================

すべての重要な変更点を記録します。  
このファイルは Keep a Changelog の形式に従います。  
詳細: https://keepachangelog.com/ (日本語訳に準拠)

バージョン履歴
--------------

Unreleased
----------

なし

0.1.0 - 2026-03-19
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージルート: src/kabusys/__init__.py（__version__ = "0.1.0"）
  - エクスポート: data, strategy, execution, monitoring を __all__ で公開

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能
    - プロジェクトルートを .git または pyproject.toml から探索して決定（CWD 非依存）
    - 読み込み順: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化
  - .env パーサ実装: export 句・クォート・エスケープ・インラインコメントを考慮したパース
  - 環境変数必須チェック _require と Settings クラス
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などのプロパティ
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等
    - env 値の検証: KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーション

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント実装（ページネーション対応）
  - レート制限制御: 固定間隔スロットリングで 120 req/min を厳守する RateLimiter を実装
  - リトライ: 指数バックオフ、最大 3 回、ステータス 408/429/5xx に対応
  - 401 時の自動トークンリフレッシュ（get_id_token を用いて 1 回リトライ）
  - ID トークンのモジュールレベルキャッシュ（ページネーション間で共有）
  - fetch_* 系（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
    - 冪等保存: ON CONFLICT DO UPDATE / DO NOTHING を使用
    - fetched_at を UTC ISO8601（Z）で保存
    - 不完全な PK 行はスキップしてログ警告

- ニュース収集 (kabusys.data.news_collector)
  - RSS 取得・正規化・保存パイプライン
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ(utm_*, fbclid, gclid 等)除去、フラグメント削除、クエリソート
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を利用して冪等性を確保
    - defusedxml を利用して XML 攻撃（XML Bomb 等）を防御
    - HTTP スキーム以外の URL 拒否や受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）による安全対策
    - バルク INSERT チャンク化（_INSERT_CHUNK_SIZE = 1000）で DB 負荷を抑制
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを設定

- 研究モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research)
    - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）
    - Volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio（20日平均を利用）
    - Value: per、roe（raw_financials から最新の報告を利用）
    - DuckDB SQL を活用した効率的なウィンドウ集計
    - データ不足時は None を返却する設計（ルックアヘッドバイアス回避）
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21] 営業日）の将来リターンを計算
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（有効サンプル 3 未満は None）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ
    - rank ユーティリティ: 同順位は平均ランクにする実装（round(..., 12) による ties 対策）
  - 研究用関数は外部 API や発注層へアクセスしない（安全に研究可能）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date): research モジュールの生ファクターを合成して features テーブルへ UPSERT
    - ユニバースフィルタ: 最低株価 300 円、20日平均売買代金 >= 5 億円
    - 正規化: zscore_normalize を適用（対象カラムを指定）、±3 でクリップ
    - 日付単位での置換（DELETE + INSERT をトランザクションで行い原子性を担保）
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみ使用

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を結合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - コンポーネントごとの計算ロジックを内包（_sigmoid, _avg_scores, _compute_*）
    - AI スコアは未登録時に中立（0.5）で補完
    - ウェイトの検証・補完・再スケール機能（不正値は警告してスキップ）
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に BUY を抑制（サンプル数閾値あり）
    - BUY: final_score >= threshold
    - SELL（エグジット判定）: ストップロス（-8%）およびスコア低下（threshold 未満）を実装
      - いくつかのエグジットロジック（トレーリングストップ、時間決済）は未実装（備考あり）
    - 日付単位の置換で signals テーブルへ保存（トランザクション＋バルク挿入）
    - BUY と SELL の優先付け（SELL 優先で BUY から除外しランクを再付与）

Changed
- デフォルト設定
  - DUCKDB_PATH のデフォルトを data/kabusys.duckdb、SQLITE_PATH を data/monitoring.db に設定
  - KABU_API_BASE_URL のデフォルトを http://localhost:18080/kabusapi に設定（テスト用ローカルステーション想定）
  - LOG_LEVEL のデフォルトを INFO

Security
- XML パースで defusedxml を使用して XML 関連攻撃から保護（news_collector）
- RSS 処理で受信サイズ上限、トラッキングパラメータ除去、HTTP スキーム制約、IP/SSRF 関連対策を設計方針に明示

Fixed
- 初版のため該当なし

Deprecated
- 初版のため該当なし

Removed
- 初版のため該当なし

Notes / Design decisions
- 研究モジュールは外部依存（pandas 等）を避け、標準ライブラリ + DuckDB SQL で実装
- データ取得では「いつデータを知り得たか」を記録するため fetched_at を UTC で保存（Look-ahead Bias 対策）
- DB への書き込みは可能な限り冪等（ON CONFLICT）かつトランザクションで原子性を確保
- ロギングと警告を多用してデータ欠損や不正パラメータを明示的に検知できるようにしている

今後の予定（例）
- execution 層の発注ロジックと kabuステーション連携の実装
- signals のポジション管理でトレーリングストップや時間決済ルールの導入
- AI スコア供給パイプラインとニュースの銘柄マッピング強化
- 単体テストおよび統合テストの拡充

---

（CHANGELOG は今後の変更ごとに日時付きで追記してください）