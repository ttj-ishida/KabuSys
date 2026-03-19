# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-03-19
初回公開リリース。日本株自動売買システムのコア機能（データ取得・前処理・ファクター計算・シグナル生成・設定管理など）を実装。

### Added
- パッケージ基盤
  - パッケージのメタ情報と公開 API を定義 (src/kabusys/__init__.py, __version__ = "0.1.0")。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env/.env.local および OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を検出して行うため、CWD に依存しない自動読み込みを実現。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、エスケープ、コメント（インライン含む）に対応。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスでアプリ固有設定をプロパティ化 (J-Quants トークン、kabu API 設定、Slack、DB パス、環境/ログレベル判定等)。
  - env/log_level のバリデーション、is_live/is_paper/is_dev ユーティリティを提供。

- データ取得クライアント: J-Quants (src/kabusys/data/jquants_client.py)
  - API クライアントを実装（ページネーション対応）。
  - 固定間隔の RateLimiter による 120 req/min 制御。
  - リトライ（指数バックオフ、最大 3 回）と 408/429/5xx の再試行処理。
  - 401 受信時はリフレッシュトークンから自動で ID トークンを再取得して 1 回リトライ。
  - 取得日時（fetched_at）を UTC で記録し、Look-ahead バイアスの追跡に対応。
  - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - DuckDB へ冪等保存する save_* 関数（raw_prices, raw_financials, market_calendar）。INSERT ... ON CONFLICT DO UPDATE を利用。
  - robust な型変換ユーティリティ _to_float / _to_int を実装。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集の初期実装（デフォルトで Yahoo Finance のビジネスカテゴリ RSS を登録）。
  - URL 正規化（トラッキングパラメータ除去、フラグメント削除、キーソート、小文字化）を実装。
  - defusedxml を使った安全な XML パース、最大受信バイト数制限（10MB）などの安全対策を実施。
  - 記事 ID を URL 正規化後の SHA-256（短縮）で生成して冪等性を確保。
  - バルク INSERT のチャンク処理や INSERT RETURNING を想定した実装設計。

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - ファクター計算モジュールを実装（prices_daily / raw_financials を参照する純粋集計ロジック）。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日 MA）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金(avg_turnover)、volume_ratio を計算。
    - calc_value: 直近の財務データを用いて PER/ROE を計算（EPS=0 の場合は None）。
  - 研究支援ユーティリティ (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを計算（1 クエリでまとめて取得）。
    - calc_ic: ファクターと将来リターンのスピアマン IC（ランク相関）を計算。サンプル不足時は None を返す。
    - rank / factor_summary: 同順位の平均ランク処理、各ファクターの集計統計（count/mean/std/min/max/median）を計算。
  - すべて標準ライブラリ + DuckDB SQL で実装し、本番 API にアクセスしない設計。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価=300円、20日平均売買代金>=5億円）を適用。
  - 指定日付の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性保証）。
  - 休場日や当日欠損に対する価格取得ロジック（target_date 以前の最新価格参照）を実装。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を算出するシステムを実装。
  - コンポーネントスコア算出:
    - momentum（momentum_20/60、ma200_dev をシグモイド→平均）
    - value（PER を 20 を基準にスケール）
    - volatility（atr_pct の Z を反転してシグモイド）
    - liquidity（volume_ratio をシグモイド）
    - news（ai_score をシグモイド、未登録は中立）
  - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
  - 重みはデフォルトで合計 1.0。ユーザー渡しの weights を検証・補完・再スケールするロジックを実装（無効値はスキップ）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値達成時）により BUY シグナルを抑制。
  - BUY は閾値（デフォルト 0.60）以上の銘柄。SELL は stop_loss（-8%）と final_score 低下を実装。
  - positions / prices の欠損時の挙動（価格欠損で SELL 判定をスキップ、features 非存在保有は score=0.0 扱いで SELL）を明確化。
  - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）で冪等性を保証。

- パッケージ公開 API (src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py)
  - 主要関数を __all__ にまとめて上位からインポートしやすくした。

### Security / Safety
- ニュース XML パースに defusedxml を使用して XML Bomb 等の攻撃を緩和。
- news_collector は受信サイズを制限して DoS のリスクを低減。
- .env 読み込みは既存の OS 環境変数を保護する機構（protected set）を導入。
- J-Quants クライアントはタイムアウト・リトライ・レート制御を備え、トークン自動リフレッシュで認証失敗に対処。

### Notes / Known limitations
- execution 層はパッケージ内にディレクトリは存在するが（src/kabusys/execution/__init__.py）、発注実装は含まれていない（現時点ではシグナル生成まで）。
- signal_generator の一部戦略条件は未実装（コメントに記載）:
  - トレーリングストップ（peak_price の管理が positions テーブルに必要）
  - 時間決済（保有日数ベースの自動エグジット）
- news_collector の完全な RSS パース / URL 検証・ネットワークリトライの詳細実装（HTTP エラー時の再試行等）は拡張の余地あり。
- research モジュールは DuckDB の prices_daily/raw_financials に依存するため、事前に適切な ETL でデータをロードする必要がある。
- Save 系関数は DuckDB のスキーマ（raw_prices/raw_financials/market_calendar/features/signals 等）前提で実装されている。スキーマの不整合があると例外が発生する。

### Internal / Implementation decisions (概要)
- Look-ahead バイアス防止を重視し、各処理は target_date 時点のデータ・fetched_at の記録を基本設計とした。
- 冪等性を重視し、DB 書き込みは日付単位の置換（DELETE→INSERT）や ON CONFLICT を多用。
- 外部依存（pandas 等）を避け、標準ライブラリと DuckDB SQL でパフォーマンスと移植性を確保。

---

今後のリリースでは以下を想定しています:
- execution 層の発注実装（kabu API 経由）と発注結果の監視
- news_collector のソース追加・自然言語前処理・ニュース→銘柄マッチング強化
- モニタリング / アラート機能の充実（Slack 通知など）
- テスト・CI の充実とスキーマ移行ツール

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートはリポジトリのコミット履歴・リリース方針に従って更新してください。）