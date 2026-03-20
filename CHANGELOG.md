# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

注意: このリポジトリの初期リリースとしてコードベースから推測される機能・設計をまとめています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-20

Added
- パッケージ基礎
  - kabusys パッケージ初期公開。モジュールを外部に公開するための __init__.py を追加し、version="0.1.0" として定義。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定・環境変数管理 (src/kabusys/config.py)
  - プロジェクトルート検出: .git または pyproject.toml を基準にパッケージの位置からプロジェクトルートを推定する _find_project_root() を実装。これにより CWD に依存せず .env 自動読み込みが可能。
  - .env パーサ実装: _parse_env_line() は空行・コメント・export プレフィックス・クォート付き値・インラインコメント処理をサポート。
  - .env 自動読み込み: OS 環境変数 > .env.local > .env の優先度で自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 読み込みの上書き制御: _load_env_file() で override/ protected（OS環境変数保護）を実装。
  - Settings クラスを提供してアプリケーション設定をプロパティ経由で取得可能に。主なプロパティ:
    - jquants_refresh_token, kabu_api_password, kabu_api_base_url
    - slack_bot_token, slack_channel_id
    - duckdb_path (デフォルト data/kabusys.duckdb), sqlite_path (デフォルト data/monitoring.db)
    - env (development/paper_trading/live の厳密検証)、log_level（有効値検証）、is_live/is_paper/is_dev
  - 必須環境変数未設定時は明確な ValueError を投げる _require() を実装。

- データ取得・永続化: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - API クライアント実装:
    - レート制限制御: 固定間隔スロットリング _RateLimiter（デフォルト 120 req/min）を実装。
    - リトライロジック: 指数バックオフで最大再試行回数を設定（最大 3 回）、HTTP 408/429/5xx に対するリトライ。429 の場合 Retry-After ヘッダを尊重。
    - 401 発生時のトークン自動リフレッシュを 1 回許可（無限再帰防止）。
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への冪等保存関数:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE により保存（fetched_at を UTC で記録）。
    - save_financial_statements: raw_financials テーブルへ同様に保存。
    - save_market_calendar: market_calendar テーブルへ保存（取引日/半日/SQ フラグを解釈）。
  - 型変換ユーティリティ: _to_float, _to_int を実装して不正値や空値を安全に扱う。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS ベースのニュース収集基盤を実装（DEFAULT_RSS_SOURCES にデフォルトソースを用意）。
  - セキュリティ・堅牢性:
    - defusedxml を使用して XML Bomb 等を防止。
    - 受信サイズ上限 MAX_RESPONSE_BYTES（10 MB）でメモリ DoS を軽減。
    - URL 正規化とトラッキングパラメータ除去 (_normalize_url) を実装（utm_, fbclid 等を排除）。
    - 安全に扱うための正規表現・チャンク挿入・ID 生成（コメントに SHA-256 を用いる設計記述）。
  - raw_news への冪等保存やニュースと銘柄の紐付け（news_symbols）を想定した設計。

- リサーチモジュール (src/kabusys/research/*)
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を DuckDB で高速に計算。スキャン範囲バッファを使い祝日・欠損に対応。
    - calc_volatility: 20日 ATR（true range の扱いに注意）、atr_pct、20日平均売買代金、volume_ratio を計算。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS 欠損・0 は None）。
  - feature_exploration.py:
    - calc_forward_returns: デフォルト horizon [1,5,21]（翌日/翌週/翌月）で将来リターンを計算。horizons の検証（正の整数かつ <=252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。サンプル数 3 未満は None。
    - rank: 同順位は平均ランクとするランク変換（round(v, 12) で ties の誤検出を抑制）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリーを実装。
  - research パッケージ __init__ で主要関数を再エクスポート。

- 戦略モジュール (src/kabusys/strategy/*)
  - feature_engineering.build_features:
    - research 側で計算した生ファクター（calc_momentum / calc_volatility / calc_value）を統合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 正規化: 指定カラムを zscore_normalize()（外部ユーティリティ）で正規化し ±3 でクリップ。
    - DB 操作: features テーブルに対して日付単位の置換（DELETE → bulk INSERT）をトランザクションで行い原子性を保証。処理は冪等。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコアを計算し final_score を算出。
    - デフォルト重みと閾値:
      - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
      - デフォルト閾値: 0.60（これ以上で BUY）
      - ストップロス閾値: -8%（pnl_rate <= -0.08 で SELL）
      - Bear 判定は ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合
    - 重みの入力検証と正規化: 外部から渡された weights は既知キーのみ受け付け、不正値は無視。合計が 1.0 でなければスケール調整、合計が不正ならデフォルトにフォールバック。
    - AI ニューススコア: ai_score をシグモイド変換して統合、未登録銘柄は中立(0.5)で補完。
    - SELL シグナル生成: 保有ポジション（positions テーブル）に対して stop_loss と スコア低下を判定。価格欠損時は判定をスキップして誤クローズを防止。
    - DB 操作: signals テーブルを日付単位で置換することで冪等に書き込み。
    - ログ出力: 各段階で warning/info/debug を出力して状況を把握可能。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Security
- news_collector で defusedxml を利用し XML パーサ攻撃に対処。
- news_collector は受信サイズ制限・URL 正規化等を実施し、SSRF/トラッキングパラメータなどのリスクを低減。
- J-Quants クライアントは認証トークンの自動リフレッシュとリトライポリシーを備え、レート制限を守る設計。

Notes / Known limitations
- signal_generator の一部エグジット条件（トレーリングストップや時間決済）はコメントで未実装と記載。positions テーブルに peak_price / entry_date 等の情報が必要。
- get_id_token() は settings.jquants_refresh_token に依存。環境変数未設定時は ValueError を送出。
- .env 自動読み込みはプロジェクトルート検出に依存するため、配布後や特殊なレイアウトでは自動ロードがスキップされることがある（KABUSYS_DISABLE_AUTO_ENV_LOAD を用いて明示的に制御可能）。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指しているため、API は生のリスト/辞書と DuckDB を扱う形になっている。
- DuckDB テーブルスキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, positions, market_calendar など）は本 CHANGELOG に含まれていないがコードの SQL 文から必要カラムを参照している。環境構築時はスキーマ整備が必要。

---

この CHANGELOG はコードベースのコメント・実装内容から推測して作成しています。実際のリリースノート作成時は差分・コミット履歴を基に適宜調整してください。