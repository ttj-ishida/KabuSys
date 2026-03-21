# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) 準拠で記載しています。

## [0.1.0] - 2026-03-21

初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点・設計方針は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンと公開 API を設定（src/kabusys/__init__.py）。
  - バージョン: 0.1.0

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートを .git または pyproject.toml で検出して .env/.env.local を読み込む。
    - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 高度な .env パーサ実装（export 形式対応、クォート文字列内のエスケープ処理、インラインコメントの扱い、空行/コメント行スキップ）。
  - OS 環境変数の保護（.env.local 上書き時に既存 OS 環境変数を保護）。
  - Settings クラス（プロパティ経由で必須変数を取得）
    - J-Quants / kabuステーション / Slack / DB パス 等の設定を提供。
    - 値検証（KABUSYS_ENV の許容値検査、LOG_LEVEL の検査等）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ（_request）を実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大リトライ回数、408/429/5xx 対象）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ再取得）とモジュール内トークンキャッシュ。
    - ページネーション対応（pagination_key を利用）。
  - 認証トークン取得: get_id_token（refresh token から取得）。
  - データ取得関数:
    - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）。
  - DuckDB への保存関数（冪等）
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE を用いた upsert、fetched_at の UTC 記録、PK 欠損行スキップのログ。
  - 型変換ユーティリティ: _to_float / _to_int（安全な変換と欠損扱い）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS から記事収集・正規化・保存を行う機能を実装。
    - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント除去・スキーム/ホスト小文字化）。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を想定して冪等性を確保する設計。
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）によるメモリ DoS 対策。
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）で SQL 長やパラメータ数を制御。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。

- リサーチ（研究）モジュール（src/kabusys/research/）
  - factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB のウィンドウ関数を活用してモメンタム・ATR・MA200・出来高等を計算。
    - raw_financials / prices_daily のみ参照する純粋なデータ処理ロジック。
  - feature_exploration.py
    - calc_forward_returns（複数ホライズンの将来リターンを一括取得）
    - calc_ic（Spearman のランク相関（IC）計算）
    - factor_summary（基本統計量: count/mean/std/min/max/median）
    - rank（平均ランクを付与するランク変換）
    - pandas 等に依存しない純標準ライブラリ実装。
  - これらを research/__init__.py で公開。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features を実装。
    - research 側で計算した生ファクターを取得（calc_momentum/calc_volatility/calc_value の利用）。
    - ユニバースフィルタ（最低株価・20日平均売買代金）を適用。
    - zscore_normalize（kabusys.data.stats を利用）で正規化し ±3 でクリップ。
    - 日付単位で features テーブルをトランザクション内で置換（冪等性）。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals を実装。
    - features / ai_scores / positions を参照して最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算するユーティリティ関数を実装。
    - 重み付け（デフォルト重みを定義）、ユーザー指定重みの検証と再スケーリング。
    - Bear レジーム判定（ai_scores の regime_score 平均が負 → BUY 抑制）。
    - BUY シグナル閾値（デフォルト 0.60）超過銘柄に BUY シグナルを生成。
    - SELL（エグジット）判定:
      - ストップロス（終値/avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - （将来的な実装候補としてトレーリングストップ/時間決済を明記）
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入で原子性を保証）。

### 改善・設計上の配慮 (Changed / Design)
- ルックアヘッドバイアス対策
  - 全ての日付参照は target_date 時点で入手可能なデータのみを利用する方針で統一（research/strategy 層ともに明記）。
- 冪等性
  - DuckDB への保存は可能な限り UPSERT（ON CONFLICT）または日付単位の DELETE→INSERT を行い冪等性を確保。
- トランザクション保護
  - build_features/generate_signals 等の書き込み処理では BEGIN/COMMIT/ROLLBACK を用い、ROLLBACK 失敗時はログを残す。

### 修正・堅牢化 (Fixed)
- .env パーサの堅牢化（引用符内のエスケープ処理、export プレフィックス対応、インラインコメントの扱いなど）により現実的な .env フォーマットに対応。
- API 呼び出しのエラー処理強化（HTTPError に対する適切なリトライ、Retry-After ヘッダの考慮、ネットワーク例外の再試行）。
- データ保存時の PK 欠損行をスキップしてログ出力することで不正データによる例外発生を抑止。

### セキュリティ (Security)
- ニュース収集で defusedxml を利用して XML の脆弱性を軽減。
- ニュース URL の正規化・トラッキングパラメータ除去により ID 生成の冪等性を強化（悪意あるクエリ文字列差異による重複回避）。
- ドキュメントに SSRF 防止・HTTP スキームフィルタ・受信サイズ制限等の設計方針を記載（実装上の意図あり）。

### 既知の未実装 / 今後の作業 (Known issues / TODO)
- signal_generator の SELL 判定において、トレーリングストップや時間決済は positions テーブルに peak_price / entry_date 等の追加情報を要するため未実装。将来追加予定。
- news_collector の一部実装（IP/SSRF 検査や記事 ID 生成の詳細処理の実装箇所）は設計に沿った追加実装が必要。
- execution（発注）層や monitoring 層はパッケージ構造に含まれるが、このリリースでは実装依存を持たない設計（発注 API 直接呼び出しは行わない）。

---

このバージョンは「コアデータ処理・特徴量算出・シグナル生成・外部データ収集」の初期実装を提供します。発注（execution）や運用監視（monitoring）、UI/デプロイメント周りは今後のリリースで拡張予定です。