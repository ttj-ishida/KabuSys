# Changelog

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトの初期リリースを示します。

全般な注意:
- 日付は 2026-03-20（現行リビジョン日）です。
- リリースノートはソースコードから明示的に分かる実装・設計方針・既知の制限をまとめたものです。

## [0.1.0] - 2026-03-20

### Added
- 初期パッケージ「kabusys」を追加
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__="0.1.0"、公開モジュールとして data, strategy, execution, monitoring を列挙。
- 環境設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロードを実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理、キー・値検証。
  - 環境設定用 Settings クラスを実装（settings インスタンスをエクスポート）。
    - 必須環境変数の取得（_require）と ValueError による明確なエラー。
    - J-Quants / kabu station / Slack / DB パス等のプロパティを提供。
    - KABUSYS_ENV / LOG_LEVEL の値チェックと補助メソッド（is_live / is_paper / is_dev）。
- データ取得・保存モジュールを追加（src/kabusys/data）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 固定間隔スロットリング方式の RateLimiter（120 req/min 想定）を実装。
    - 再試行（指数バックオフ、最大 3 回）とステータスコードベースのリトライ判定（408, 429, 5xx）。
    - 401 受信時にリフレッシュトークンから id token を自動更新して1回リトライする仕組み。
    - ページネーション処理を備えた fetch_* API（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT で冪等性を担保し、fetched_at を UTC ISO 形式で記録。
    - 型変換ユーティリティ (_to_float, _to_int) による安全なパース。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード収集の基礎実装（デフォルトソース: Yahoo Finance ビジネス RSS）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）とテキスト前処理。
    - defusedxml を利用した XML パースによる安全対策、受信サイズ制限（MAX_RESPONSE_BYTES: 10MB）、バルク挿入のチャンク化などを考慮。
    - 設計文書に基づく冪等保存・識別子生成方針（コメント化された仕様説明）。
- 研究用モジュール（src/kabusys/research）
  - ファクター計算モジュール（factor_research.py）
    - calc_momentum（1M/3M/6M リターン、200日移動平均乖離）、calc_volatility（20日 ATR、20日平均売買代金、出来高比率）、calc_value（PER, ROE）の実装。
    - DuckDB のウィンドウ関数を活用した効率的な SQL ベース計算、データ不足時の None ハンドリング。
  - 特徴量探索モジュール（feature_exploration.py）
    - calc_forward_returns（複数ホライズンの将来リターンを一度のクエリで取得）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量）、rank（平均ランクでの同順位処理）を実装。
    - calc_forward_returns は horizons の入力検証（正の整数かつ <=252 営業日）を行う。
  - research パッケージの __all__ を整備して主要 API をエクスポート。
- 戦略モジュール（src/kabusys/strategy）
  - 特徴量エンジニアリング（feature_engineering.py）
    - research 側で計算した生ファクターを統合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 正規化は外部ユーティリティ zscore_normalize（kabusys.data.stats）を利用、±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション + バルク挿入）で冪等性を保証する build_features を提供。
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）、重み（デフォルトは設定値）を用いた final_score 計算を実装。
    - weights の入力検証（既知キーのみ、非負・有限数のみ採用）、合計が 1 でない場合の再スケーリングを行う。
    - Bear レジーム判定（regime_score の平均が負かつサンプル数閾値を満たす場合）で BUY シグナルを抑制。
    - BUY シグナル閾値デフォルト 0.60、SELL 条件（ストップロス -8%、スコア低下）を実装。
    - SELL 優先ポリシー（SELL 対象を BUY から除外）と signals テーブルへの日付単位置換により冪等性を保持する generate_signals を提供。
- API のトランザクション管理とログ出力を各所で強化（begin/commit/rollback の扱い、失敗時の警告ログ）。

### Changed
- （初期リリースのため主に追加のみ。実装時点での設計方針・安全対策をコードコメントと実装に反映）
  - DuckDB への保存関数は ON CONFLICT を使い重複上書きを行う方針を採用。
  - データ取得処理はページネーションおよびレート制御・リトライを組み合わせる設計に統一。

### Fixed
- N/A（初期公開版）

### Security
- news_collector で defusedxml を採用、受信バイト数上限の導入など外部データ取り込み時の脆弱性対策をコメント・実装で明記。
- J-Quants クライアントはトークンリフレッシュの自動化とレート制御、再試行ポリシーを備え、API 認証エラーや過負荷に対して堅牢化。

### Removed
- N/A（初期公開版）

### Deprecated
- N/A（初期公開版）

### Known issues / Notes
- execution パッケージは __init__ が存在するのみで、発注実装は含まれていません（発注レイヤは今後の実装予定）。
- monitoring は __all__ に含まれているが、明示的な実装コードは含まれていません（将来の監視機能のプレースホルダ）。
- 戦略に関する未実装事項（feature_engineering / signal_generator のコメントに記載）:
  - トレーリングストップ（peak_price に基づく）や時間決済（保有日数に基づく強制決済）は positions テーブルの拡張と合わせて未実装。
  - calc_value において PBR や配当利回りは現バージョンでは未実装。
- news_collector の一部仕様（例: 記事ID の SHA-256 生成や SSRF/IP チェックなど）は設計コメントで記載されているが、メインの正規化関数やパーシング周りはコードベースの続き（truncate 部分）との結合が必要。

---

今後のリリースでは、execution 層の発注ロジック、監視（monitoring）機能、news <-> symbol の紐付け処理、さらに追加的なファクター・運用上の安全機能（ウォレット管理、注文リトライ戦略等）を予定しています。