# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」仕様に従って作成されています。

フォーマット: [Unreleased] とリリース済みバージョンのセクションを含みます。

## [Unreleased]
- 今後のリリース向けの変更点はここに記載します。

## [0.1.0] - 2026-03-20
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

### Added
- パッケージ基本情報
  - パッケージ名/説明を追加（src/kabusys/__init__.py）。
  - バージョンを 0.1.0 に設定。

- 設定・環境変数管理
  - 環境変数・.env ファイル自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート判定 (.git または pyproject.toml) に基づく自動読み込み。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - `.env` 行パーサ: コメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート。
    - .env ファイル読み込み時の上書き/保護（protected keys) サポート。
  - Settings クラスを追加し、主要設定値をプロパティ経由で取得可能に。
    - J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パスなどを取得。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）を実装。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- Data レイヤ: J-Quants クライアント
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔スロットリング (_RateLimiter) によるレート制御（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を考慮）。
    - 401 受信時の ID トークン自動リフレッシュ（1 回だけ再試行）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（OHLCV）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存ユーティリティ（冪等化: ON CONFLICT DO UPDATE）:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - 入力サニタイズユーティリティ _to_float / _to_int を追加。
    - fetched_at を UTC ISO8601 形式で記録し、Look-ahead バイアス追跡を可能に。

- Data レイヤ: ニュース収集
  - RSS ベースのニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得、記事前処理、raw_news への冪等保存を想定。
    - 記事 ID を URL 正規化後の SHA-256 で生成（冪等性）。
    - トラッキングパラメータ除去、URL 正規化、受信サイズ上限（10MB）などの安全対策。
    - defusedxml による XML セキュリティ対策（XML Bomb 等）。
    - DB 挿入のバルク処理・チャンク化実装のための定数（チャンクサイズ）。

- Research（研究用）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - ボラティリティ/流動性: calc_volatility（ATR20, atr_pct, avg_turnover, volume_ratio）
    - バリュー: calc_value（PER, ROE を raw_financials と prices_daily から算出）
    - 各関数は DuckDB 接続を受け取り、(date, code) 単位の dict リストを返す。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: Spearman（ランク相関）による IC 計算（同順位は平均ランクで処理、3 サンプル未満は None）。
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）を算出。
    - rank: タイ（同順位）を平均ランクで扱うランク付けを実装。

- Strategy（戦略）モジュール
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュール（calc_momentum / calc_volatility / calc_value）を組み合わせて features を作成。
    - ユニバースフィルタ（最低株価 300 円、20 日 AVG 売買代金 5 億円）を実装。
    - 数値ファクターを Z スコア正規化し ±3 でクリップ（外れ値抑制）。
    - 日付単位での置換（DELETE -> INSERT within トランザクション）により冪等性を保証。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合し最終スコア final_score を計算。
      - momentum / value / volatility / liquidity / news の重み付け（デフォルト値を実装）。
      - シグモイド変換・コンポーネント平均化・欠損は中立 0.5 で補完。
      - ユーザ渡しの weights を検証して補完・再スケール（合計が 1 になるよう処理）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）。
    - BUY シグナル: threshold（デフォルト 0.60）以上の銘柄を選出、Bear 時は抑制。
    - SELL シグナル（エグジット判定）:
      - ストップロス（終値/avg_price -1 < -8%）
      - final_score が threshold 未満
      - 価格欠損時は SELL 判定をスキップして誤クローズを回避
    - signals テーブルへの日付単位置換（トランザクション）で冪等性を保証。

- パッケージ公開 API
  - strategy モジュールから build_features / generate_signals を __all__ にエクスポート。

### Changed
- ロギング/デバッグ情報を強化
  - 各処理での logger.debug/info/warning を充実させ、処理結果数や日付などを記録。

### Fixed
- トランザクション落ちた際の ROLLBACK の失敗を捕捉して警告を出す処理を追加（feature_engineering / signal_generator）。
- .env ファイル読み込み失敗時に警告を出すようにして、プロセスを停止させない設計に。

### Security
- 外部入力（XML/URL）に対する安全対策を実施
  - defusedxml を使用して XML の危険を軽減（news_collector）。
  - URL 正規化・トラッキングパラメータ除去・受信サイズ制限で SSRF / DoS 的な悪用を軽減する設計思想を適用。
- API クライアントでトークンの取り扱い・自動リフレッシュ時の無限再帰防止ロジックを実装。

### Performance
- DuckDB を想定した集約・ウィンドウ関数を利用する実装により大量データ処理での効率化を図る（factor_research / feature_engineering / feature_exploration）。
- J-Quants API 呼び出しで固定間隔スロットリングを用いレート制限守ることで安定性を確保。

### Notes / Limitations
- News collector の一部実装（例: 記事 ID の生成やシンボル紐付け処理の詳細、SSRF の IP 検証等）はモジュール内設計方針に記載されているが、コードの一部（例: _normalize_url の完全実装）やシンボル紐付けロジックは続きが想定されています。
- Execution / monitoring パッケージはインターフェースの存在を示すが、発注 API 連携（実行層）や監視関連の実装は本リリースでは最小限/未実装部分が想定されます（設計は層分離を重視）。
- 一部のルール（トレーリングストップ、時間決済など）は設計で言及されているが、positions テーブルの拡張（peak_price / entry_date）等が必要であり未実装。

---

今後の予定:
- news_collector の完全実装（記事 ID 生成／DB 保存返却値の厳密化／SSRF 対応）と unit test の追加。
- execution 層（kabu-station との連携）、モニタリング・アラート機能の実装。
- ドキュメント（StrategyModel.md, DataPlatform.md 等）に基づく追加テストと検証。