# Changelog

すべての重要な変更点を記録します。このファイルは Keep a Changelog の書式に準拠しています。  
安定版リリースはセマンティックバージョニングに従います。

- リリース日付は該当リリースのコードベースから推測した日付を使用しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージメタ情報: src/kabusys/__init__.py にて __version__ = "0.1.0"、公開モジュールとして ["data", "strategy", "execution", "monitoring"] を定義。
- 環境設定/ロード機能
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装（src/kabusys/config.py）。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（CWD に依存しない実装）。
    - .env/.env.local の読み込み優先度（OS環境 > .env.local > .env）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - .env パーサは export プレフィックス、シングル／ダブルクォートやエスケープ、インラインコメント（スペース直前の#）を考慮して安全にパース。
    - Settings クラスを公開し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）、パスの Path 型変換（DUCKDB_PATH / SQLITE_PATH）、環境（KABUSYS_ENV）やログレベル検証を提供。
- データ取得/保存（J-Quants API クライアント）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 固定間隔スロットリングによるレート制限管理（120 req/min）。
    - 再試行（指数バックオフ、最大3回）、HTTP 408/429/5xx を再試行対象に、429 の場合は Retry-After ヘッダ優先。
    - 401 受信時にリフレッシュトークンから自動で id_token を取得し 1 回リトライする仕組み（無限再帰防止のフラグ）。
    - ページネーション対応の fetch_ 系関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB への保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT/DO UPDATE による冪等保存）。
    - 型変換ユーティリティ: _to_float / _to_int（妥当性を考慮した安全変換）。
    - 取得時刻（fetched_at）を UTC ISO フォーマットで保存し、look-ahead バイアスのトレーサビリティを確保。
- ニュース収集
  - RSS から記事を収集して raw_news に保存するニュース収集モジュールを実装（src/kabusys/data/news_collector.py）。
    - デフォルト RSS ソース（例: Yahoo Finance）を定義。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、トラッキングパラメータ除去、URL 正規化、記事 ID の SHA-256 による冪等化を実装。
    - XML パーシングに defusedxml を使用して XML ボム等の攻撃を軽減。
    - SSRF 対策や受信サイズ制限、バルク INSERT のチャンク処理など安全性・効率性を考慮した実装。
- 研究（Research）モジュール
  - ファクター計算モジュールを実装（src/kabusys/research/factor_research.py）。
    - Momentum（mom_1m/mom_3m/mom_6m、MA200乖離）、Volatility（ATR20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の prices_daily/raw_financials を参照して計算。
    - 売買代金・ボラティリティ計算において窓幅やデータ不足を考慮（十分な観測がない場合は None を返す）。
  - 特徴量探索ユーティリティを実装（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns: 将来リターン（1/5/21 営業日デフォルト）の一括取得（ウィンドウのスキャン範囲最適化を実装）。
    - calc_ic: スピアマンランク相関による IC 計算（同順位は平均ランクで処理、サンプル不足時は None）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクを採るランク化ユーティリティ（丸めで ties の漏れを防止）。
  - research パッケージの __all__ に主要関数を公開。
- 特徴量エンジニアリング（Strategy）
  - build_features を実装（src/kabusys/strategy/feature_engineering.py）。
    - research モジュールの calc_momentum/calc_volatility/calc_value を統合して features を構築。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - 日付単位での置換（BEGIN/DELETE/INSERT/COMMIT）による冪等性と原子性を保証。
- シグナル生成（Strategy）
  - generate_signals を実装（src/kabusys/strategy/signal_generator.py）。
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを計算。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完し不当な降格を防止。
    - デフォルト重みは StrategyModel.md に基づく（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。ユーザー指定重みは検証・正規化して合計 1.0 に調整。
    - Bear レジーム判定（ai_scores の regime_score の平均が負、ただしサンプル数閾値あり）により BUY を抑制。
    - SELL（エグジット）判定実装: ストップロス（-8%）とスコア低下（threshold 未満）。保有銘柄で価格欠損がある場合は SELL 判定をスキップして安全性を確保。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）で冪等性を保証。
- パッケージ公開 API
  - strategy パッケージの __init__ で build_features/generate_signals を公開。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- news_collector で defusedxml を利用し XML パース時の安全対策を導入。
- ニュース収集で受信サイズ制限・URL 正規化・トラッキングパラメータ除去・HTTP スキーム検証等の対策を実装。
- J-Quants クライアントのネットワークエラー・重試行処理・トークンリフレッシュにより堅牢性を向上。

Known issues / Limitations
- signal_generator のエグジット条件について、コメントにある未実装の条件が残っています:
  - トレーリングストップ（直近最高値から -10%）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに peak_price / entry_date 等の追加が必要で未実装。
- calc_value では PBR・配当利回りは未実装（コメント参照）。
- feature_engineering では per（PER）は正規化対象外（逆数変換等の扱いは別途要検討）。
- execution パッケージは空のプレースホルダ（API との実際の発注・実行層は未実装）。
- monitoring パッケージは __all__ に含まれているが、この差分内で実装の詳細は確認できません。
- データベーススキーマ（テーブル定義）や外部モジュール（kabusys.data.stats の zscore_normalize 等）の実装は本差分では提示されていないため、実行には追加のテーブル定義とユーティリティ実装が必要。

Authors
- コードベースのコメント・設計文書に基づき本リリース内容を記載。

License
- コード内に明示的なライセンス情報は含まれていません（パッケージ配布時に LICENSE を追加してください）。