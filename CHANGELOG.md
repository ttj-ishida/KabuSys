# Changelog

すべての注記は Keep a Changelog 準拠です。  
現在のバージョンは src/kabusys/__init__.py に定義された v0.1.0 をベースにコードから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を定義。
    - 公開サブパッケージ: data, strategy, execution, monitoring（execution は空パッケージとして存在）。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサ実装（export 形式対応、シングル/ダブルクォート、インラインコメント処理、エスケープ対応）。
  - 読み込み時の上書き制御（override / protected）を実装。
  - Settings クラスで型付きアクセスプロパティを提供（J-Quants トークン、kabu API 設定、Slack トークン/チャンネル、DB パス、環境モード、ログレベルなど）。バリデーション（KABUSYS_ENV, LOG_LEVEL の検証）を実装。

- データ取得・保存: J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティを実装。特徴:
    - レート制限 (120 req/min) を守る固定間隔スロットリング _RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回。HTTP 408/429 と 5xx を対象）。
    - 401 Unauthorized を検知した場合の ID トークン自動リフレッシュ（1 回だけ再試行）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
    - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT を利用して重複更新）。
    - データパース用ユーティリティ _to_float / _to_int、UTC での fetched_at 記録。
    - ページネーション間でのトークン共有のためのモジュールレベルトークンキャッシュ。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集の基礎機能を実装。
    - デフォルト RSS ソース定義（例: Yahoo Finance）。
    - XML パースに defusedxml を利用して安全に処理。
    - 受信データサイズ上限（MAX_RESPONSE_BYTES = 10 MB）や受信元 URL 正規化を実装。
    - URL 正規化: 小文字化、トラッキングパラメータ（utm_* 等）の除去、フラグメント除去、クエリソート。
    - 記事 ID は URL 正規化後の SHA-256 ハッシュ先頭を使用する方針（冪等性の確保）。
    - DB へのバルク保存を前提にチャンクサイズ設定（_INSERT_CHUNK_SIZE）、SQL トランザクションで効率的に保存する設計。

- 研究用: ファクター計算・探索（src/kabusys/research/）
  - factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m、200 日移動平均乖離率（ma200_dev） を計算。
    - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 伝播制御あり）。
    - calc_value: raw_financials と prices_daily を結合して per / roe を計算（最新財務レコードの選択ロジック含む）。
    - SQL を活用した DuckDB ベースの実装（営業日欠損やデータ不足時の None 処理あり）。
  - feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。サンプル不足時は None を返す。
    - rank, factor_summary: ランク生成（同順位は平均ランク）およびカラム毎の基本統計量（count/mean/std/min/max/median）を提供。
  - research パッケージ __all__ に主要関数を公開。

- 戦略実装（src/kabusys/strategy/）
  - feature_engineering.py
    - 研究環境の生ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
    - フロー: research モジュールからファクター取得 → ユニバースフィルタ（最低価格 300 円、20 日平均売買代金 5 億円）適用 → Z スコア正規化（対象列: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev） → ±3 でクリップ → features テーブルへ日付単位の置換（トランザクションで原子性）。
    - ルックアヘッドバイアス対策として target_date 時点までのデータのみ参照。
  - signal_generator.py
    - generate_signals を実装し、features と ai_scores を統合して最終スコアを算出し BUY/SELL シグナルを生成。
    - コンポーネントスコア:
      - momentum (momentum_20/60, ma200_dev をシグモイドに変換して平均化)
      - value (PER に基づく変換)
      - volatility (atr_pct の逆符号をシグモイド)
      - liquidity (volume_ratio をシグモイド)
      - news (AI スコアをシグモイド)
    - デフォルト重みと閾値:
      - weights: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10（合計 1.0 に再スケール）
      - default threshold (BUY): 0.60
      - stop loss rate: -0.08（-8%）
    - 欠損コンポーネントは中立値 0.5 で補完し、不当な降格を防止。
    - Bear レジーム判定: ai_scores の regime_score 平均が負の場合に BUY を抑制（サンプル数閾値あり）。
    - 保有ポジションに対するエグジット判定（stop_loss / score_drop）と SELL シグナル生成。positions / prices_daily を参照。
    - signals テーブルへ日付単位の置換（トランザクションで原子性）。
    - 入力 weights のバリデーション（未知キー・NaN/Inf・負値を無視し警告）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を利用して XML 関連の攻撃を軽減。
- news_collector にレスポンスサイズ制限を導入してメモリ DoS を軽減。
- jquants_client の HTTP エラー/ネットワーク例外に対するリトライとトークンリフレッシュにより認証周り・通信の堅牢性を向上。

### Notes / Implementation details
- DuckDB を主要なストレージとして前提（多くの関数が DuckDB 接続を受け取り SQL を直接発行）。
- 多くの DB 書き込み処理は「日付単位の置換（DELETE + INSERT）」で冪等性と原子性を確保するためトランザクションを使用。
- ロギング（logger）と警告出力が各モジュールに組み込まれており、運用時の観察性を確保。
- execution モジュールはパッケージ構造に含まれているが、今回のコードスナップショットでは具体的な発注ロジックは実装されていない（分離された設計）。

### Breaking Changes
- 初回リリースのため該当なし。

---

もし CHANGELOG に追加したい日付、貢献者情報、あるいはバージョン表記の修正（例: リリース日を別にする）などの希望があれば教えてください。コード差分に基づく追加要約や、各モジュールごとの詳細な変更点（SQL スキーマ前提など）も作成できます。